import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import asyncio
import base64
from app.core.config import get_settings
import logging
from urllib.parse import urlparse, urlencode
import httpx
import traceback
from typing import Any, Optional

settings = get_settings()
logger = logging.getLogger(__name__)

def _safe_email_target(to_email: str) -> str:
    """PII-safe target string for logs/audits."""
    try:
        from app.core.observability import safe_hash
        return safe_hash((to_email or "").lower().strip())
    except Exception:
        return "<hash_error>"

def _audit_email_event(action: str, *, to_email: str, details: dict[str, Any]) -> None:
    """
    Best-effort DB audit log for email events.
    Never raises (email failures must not crash request flow).
    """
    try:
        from app.infrastructure.database import SessionLocal
        from app.domain.models import AuditLog
        import json

        payload = {
            "to_hash": _safe_email_target(to_email),
            **(details or {}),
        }
        with SessionLocal() as db:
            db.add(
                AuditLog(
                    user_id=None,
                    action=action,
                    resource_type="Email",
                    resource_id=None,
                    details=json.dumps(payload),
                    ip_address=None,
                )
            )
            db.commit()
    except Exception:
        # Intentionally silent: DB may be down and should not affect email flow.
        pass

def _is_gmail_quota_error(error: BaseException | str) -> bool:
    msg = str(error or "")
    return ("Daily user sending limit exceeded" in msg) or ("5.4.5" in msg and "sending limit" in msg)

def _send_via_smtp(to_email: str, subject: str, html_body: str, attachments: list = None) -> dict:
    """Core SMTP sending logic using Gmail with a single attempt."""
    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from or settings.smtp_user
        msg["To"] = to_email

        msg.attach(MIMEText(html_body, "html"))

        if attachments:
            for attr in attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(base64.b64decode(attr["content"]))
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {attr['filename']}",
                )
                msg.attach(part)

        # Use a timeout for the SMTP connection
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        
        # LOG SUCCESS ONLY ONCE THE MESSAGE IS SENT
        logger.info(f"[EMAIL SUCCESS] Mail definitely accepted by relay for {to_email}")
        _audit_email_event(
            "EMAIL_SEND_SUCCESS",
            to_email=to_email,
            details={
                "provider": "smtp",
                "smtp_host": settings.smtp_host,
                "smtp_port": settings.smtp_port,
            },
        )
        return {"success": True, "error": None}
    except Exception as e:
        error_msg = str(e)
        deferred = _is_gmail_quota_error(e)
        logger.error(
            f"[EMAIL ATTEMPT FAILED] provider=smtp to={to_email} deferred={deferred} "
            f"exc_class={e.__class__.__name__} error={error_msg}",
            exc_info=True,
        )
        _audit_email_event(
            "EMAIL_SEND_FAILED",
            to_email=to_email,
            details={
                "provider": "smtp",
                "deferred": deferred,
                "exc_class": e.__class__.__name__,
                "error": error_msg[:800],
            },
        )
        return {"success": False, "error": error_msg, "deferred": deferred}

async def _send_via_resend(to_email: str, subject: str, html_body: str) -> dict:
    """
    Send an HTML email via Resend's HTTP API.
    Note: for now we don't implement attachments here.
    """
    try:
        api_key = getattr(settings, "resend_api_key", "") or ""
        if not api_key:
            return {"success": False, "error": "RESEND_API_KEY not configured"}

        # Resend is explicit opt-in: require RESEND_FROM to avoid unverified sender domains.
        from_email = getattr(settings, "resend_from", "") or ""
        if not from_email:
            return {"success": False, "error": "RESEND_FROM not configured (Resend disabled)"}

        payload = {
            "from": from_email,
            "to": to_email,
            "subject": subject,
            "html": html_body,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post("https://api.resend.com/emails", json=payload, headers=headers)

        if resp.status_code in (200, 201):
            logger.info(f"[EMAIL SUCCESS] Resend accepted message for {to_email}")
            _audit_email_event(
                "EMAIL_SEND_SUCCESS",
                to_email=to_email,
                details={
                    "provider": "resend",
                    "status_code": resp.status_code,
                },
            )
            return {"success": True, "error": None}

        # Avoid returning huge bodies to logs.
        err_preview = (resp.text or "").strip()[:500]
        logger.error(
            f"[EMAIL ATTEMPT FAILED] provider=resend to={to_email} http_status={resp.status_code} "
            f"error_preview={err_preview}"
        )
        _audit_email_event(
            "EMAIL_SEND_FAILED",
            to_email=to_email,
            details={
                "provider": "resend",
                "status_code": resp.status_code,
                "error_preview": err_preview,
            },
        )
        return {"success": False, "error": f"Resend failed with HTTP {resp.status_code}", "status_code": resp.status_code}
    except Exception as e:
        logger.error(f"[EMAIL ATTEMPT FAILED] Resend {to_email}: {e}", exc_info=True)
        _audit_email_event(
            "EMAIL_SEND_FAILED",
            to_email=to_email,
            details={
                "provider": "resend",
                "exc_class": e.__class__.__name__,
                "error": str(e)[:800],
            },
        )
        return {"success": False, "error": str(e)}

async def send_email_async(to_email: str, subject: str, html_body: str, attachments: list = None) -> dict:
    """Async wrapper for the SMTP sender with up to 2 retries (3 total attempts)."""
    # Attachments: keep SMTP path for now (Resend implementation is HTML-only).
    if attachments:
        loop = asyncio.get_running_loop()
        max_retries = 2
        last_error = "Unknown error"

        for attempt in range(max_retries + 1):
            result = await loop.run_in_executor(
                None,
                _send_via_smtp,
                to_email,
                subject,
                html_body,
                attachments,
            )
            if result["success"]:
                return {**result, "provider": "smtp"}

            if result.get("deferred"):
                return {
                    "success": False,
                    "provider": "smtp",
                    "deferred": True,
                    "error": result.get("error") or "Deferred due to SMTP quota",
                }

            last_error = result["error"]
            if attempt < max_retries:
                wait_time = (attempt + 1) * 2  # Exponential-ish backoff: 2s, 4s
                logger.warning(f"Retrying SMTP email to {to_email} in {wait_time}s (Attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(wait_time)

        return {"success": False, "provider": "smtp", "error": f"Failed after {max_retries + 1} attempts: {last_error}", "deferred": False}

    # No attachments:
    # Resend is explicit opt-in and only used when BOTH RESEND_API_KEY and RESEND_FROM are set.
    resend_api_key = (getattr(settings, "resend_api_key", "") or "").strip()
    resend_from = (getattr(settings, "resend_from", "") or "").strip()
    if resend_api_key and resend_from:
        smtp_configured = bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)

        # Single Resend attempt; if it fails and SMTP is configured, fall back to SMTP.
        # Real-world Resend failures include:
        # - 401/403 (bad key)
        # - 422 (unverified/invalid "from" domain)
        # - 429 (rate limit)
        # Falling back preserves user-visible behavior when SMTP is available.
        result = await _send_via_resend(to_email, subject, html_body)
        if result["success"]:
            return {**result, "provider": "resend"}

        last_error = result["error"]

        if smtp_configured:
            logger.warning(
                f"[EMAIL FALLBACK TO SMTP] Resend failed for {to_email} ({last_error}); falling back to SMTP."
            )
            loop = asyncio.get_running_loop()
            max_smtp_retries = 1
            smtp_last_error = "Unknown error"
            try:
                for smtp_attempt in range(max_smtp_retries + 1):
                    smtp_result = await loop.run_in_executor(
                        None,
                        _send_via_smtp,
                        to_email,
                        subject,
                        html_body,
                        None,
                    )
                    if smtp_result["success"]:
                        return {**smtp_result, "provider": "smtp"}
                    if smtp_result.get("deferred"):
                        return {
                            "success": False,
                            "provider": "smtp",
                            "deferred": True,
                            "error": smtp_result.get("error") or "Deferred due to SMTP quota",
                        }
                    smtp_last_error = smtp_result["error"]
                    if smtp_attempt < max_smtp_retries:
                        wait_time = (smtp_attempt + 1) * 2
                        await asyncio.sleep(wait_time)
            except Exception as e:
                # Never crash request flow due to email issues.
                logger.error(f"[EMAIL FALLBACK TO SMTP] SMTP fallback crashed: {e}", exc_info=True)
            return {"success": False, "provider": "smtp", "error": f"Failed after SMTP fallback: {smtp_last_error}", "deferred": False}

        return {"success": False, "provider": "resend", "error": f"Failed after Resend attempt: {last_error}", "deferred": False}

    # Fallback: SMTP (original behavior).
    loop = asyncio.get_running_loop()
    max_retries = 2
    last_error = "Unknown error"

    for attempt in range(max_retries + 1):
        result = await loop.run_in_executor(
            None,
            _send_via_smtp,
            to_email,
            subject,
            html_body,
            attachments,
        )
        if result["success"]:
            return {**result, "provider": "smtp"}

        if result.get("deferred"):
            return {
                "success": False,
                "provider": "smtp",
                "deferred": True,
                "error": result.get("error") or "Deferred due to SMTP quota",
            }

        last_error = result["error"]
        if attempt < max_retries:
            wait_time = (attempt + 1) * 2  # Exponential-ish backoff: 2s, 4s
            logger.warning(f"Retrying SMTP email to {to_email} in {wait_time}s (Attempt {attempt + 1}/{max_retries})...")
            await asyncio.sleep(wait_time)

    return {"success": False, "provider": "smtp", "error": f"Failed after {max_retries + 1} attempts: {last_error}", "deferred": False}

# --- Email Templates ---

async def send_otp_email(to_email: str, otp: str):
    subject = "Verify your account for the Recruitment System"
    body = f"""
    <html><body>
      <h2>Account Verification</h2>
      <p>Use the OTP below to verify your account. Expires in 30 minutes.</p>
      <h3 style="background:#f4f4f4; padding:10px; display:inline-block; letter-spacing:5px;">{otp}</h3>
    </body></html>
    """
    result = await send_email_async(to_email, subject, body)
    if not result["success"]:
        logger.warning(f"Email failed for {to_email}: {result['error']}")
    return result["success"]

async def send_application_received_email(to_email: str, job_title: str):
    subject = f"Application Received: {job_title}"
    body = f"""
    <html><body>
      <h2>Thank You for Applying!</h2>
      <p>We received your application for <strong>{job_title}</strong>.</p>
      <p>Our team will review your profile shortly!</p>
    </body></html>
    """
    result = await send_email_async(to_email, subject, body)
    if not result["success"]:
        logger.warning(f"Application Received Email failed for {to_email}: {result['error']}")
    return result["success"]

async def send_approved_for_interview_email(to_email: str, job_title: str, raw_access_key: str = ""):
    subject = f"Congratulations! You're invited to interview for {job_title}"
    frontend_url = settings.frontend_base_url
    try:
        parsed = urlparse(frontend_url)
        base = parsed.netloc or frontend_url
        logger.debug(f"Generated interview link base: {base}")
    except Exception:
        pass
    access_url = f"{frontend_url}/interview/access?email={to_email}&key={raw_access_key}"
    support_url = f"{frontend_url}/support?{urlencode({'email': to_email, 'access_key': raw_access_key})}"
    body = f"""
    <html><body style="font-family:sans-serif; color:#333;">
      <h2>Interview Invitation</h2>
      <p>Your application for <strong>{job_title}</strong> has been approved!</p>
      <p>Please use the secure link below to access the interview portal. This link is unique to you and expires in 24 hours.</p>
      <div style="margin: 20px 0; text-align: center;">
        <a href="{access_url}" style="background-color: #2563eb; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Begin Interview</a>
      </div>
      <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
      <p><a href="{access_url}" style="color:#2563eb;">{access_url}</a></p>
      <hr style="border:none; border-top:1px solid #eee; margin: 20px 0;"/>
      <p style="margin: 0 0 6px 0; font-weight:600;">Need help with your interview experience?</p>
      <p style="margin: 0 0 8px 0;">If you faced a technical issue, unexpected termination, or need to raise a grievance, use the Support Portal:</p>
      <p style="margin: 0 0 12px 0;">
        👉 <a href="{support_url}" style="color:#2563eb; font-weight:700;">Support Portal Link</a>
      </p>
      <p style="margin: 0; font-size:0.95em; color:#555;">Our HR team will review your request promptly and reach out if more details are needed.</p>
      <hr style="border:none; border-top:1px solid #eee; margin: 20px 0;"/>
      <p style="font-size:0.9em; color:#666;">If you did not apply for this role, please disregard this email.</p>
    </body></html>
    """
    result = await send_email_async(to_email, subject, body)
    if not result["success"]:
        logger.warning(f"Interview Invitation Email failed for {to_email}: {result['error']}")
    return result["success"]

async def send_hired_email(to_email: str, job_title: str, interview=None, offer_letter_path: str = None):
    subject = "Congratulations! You have been selected"
    body = f"""
    <html><body style="font-family:sans-serif; color:#333;">
      <h2 style="color:#10b981;">Congratulations!</h2>
      <p>You have been selected for the <strong>{job_title}</strong> position!</p>
      <p>Please find your Offer Letter attached.</p>
      <p>Our HR team will contact you within 24-48 hours for onboarding.</p>
      <br><p>Best Regards,<br>The Recruitment Team</p>
    </body></html>
    """
    attachments = []
    if offer_letter_path and os.path.exists(offer_letter_path):
        with open(offer_letter_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")
            attachments.append({
                "filename": os.path.basename(offer_letter_path),
                "content": content,
            })
    result = await send_email_async(to_email, subject, body, attachments if attachments else None)
    if not result["success"]:
        logger.warning(f"Hired Email failed for {to_email}: {result['error']}")
    return result["success"]

async def send_simple_email(to_email: str, subject: str, message: str):
    """Utility for sending internal/simple notification emails."""
    body = f"<html><body><p>{message}</p></body></html>"
    result = await send_email_async(to_email, subject, body)
    return result["success"]

async def send_offer_letter_email(to_email: str, candidate_name: str, company_name: str, offer_letter_path: str, accept_link: str = "", reject_link: str = ""):
    subject = f"Offer Letter - {company_name}"
    
    # Template with buttons (Point 2)
    body = f"""
    <html><body style="font-family:sans-serif; color:#333; line-height: 1.6;">
      <h2 style="color: #2563eb;">Hello {candidate_name},</h2>
      <p>Congratulations! We are pleased to offer you a position at <strong>{company_name}</strong>.</p>
      <p>Please find the attached offer letter for your review. We are excited about the possibility of you joining our team!</p>
      
      <div style="margin: 30px 0; padding: 20px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; text-align: center;">
        <h4 style="margin-top: 0;">Please respond to this offer:</h4>
        <a href="{accept_link}" style="background-color: #10b981; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-right: 15px; display: inline-block;">Accept Offer</a>
        <a href="{reject_link}" style="background-color: #ef4444; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Reject Offer</a>
      </div>

      <p>If the buttons above do not work, use these links:</p>
      <p>Accept: <a href="{accept_link}">{accept_link}</a></p>
      <p>Reject: <a href="{reject_link}">{reject_link}</a></p>
      
      <br><p>Best Regards,<br>HR Team, {company_name}</p>
    </body></html>
    """
    attachments = []
    if offer_letter_path and os.path.exists(offer_letter_path):
        with open(offer_letter_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")
            attachments.append({
                "filename": os.path.basename(offer_letter_path),
                "content": content,
            })
    result = await send_email_async(to_email, subject, body, attachments if attachments else None)
    if not result["success"]:
        logger.warning(f"Offer Letter Email failed for {to_email}: {result['error']}")
    return result["success"]

async def send_rejected_email(to_email: str, job_title: str, is_ai_auto_reject: bool = False):
    subject = f"Update on your application for {job_title}"
    reason = "we found that your resume did not align closely enough with the job requirements." if is_ai_auto_reject else "we have decided to move forward with other candidates at this time."
    body = f"""
    <html><body>
      <h2>Application Update</h2>
      <p>Thank you for applying to <strong>{job_title}</strong>.</p>
      <p>Unfortunately, {reason}</p>
      <p>We encourage you to apply for future roles that match your skills!</p>
    </body></html>
    """
    result = await send_email_async(to_email, subject, body)
    if not result["success"]:
        logger.warning(f"Rejected Email failed for {to_email}: {result['error']}")
    return result["success"]

async def send_call_for_interview_email(to_email: str, job_title: str):
    subject = f"Interview Invitation — {job_title}"
    body = f"""
    <html><body>
      <h2>You're Invited for an Interview!</h2>
      <p>Based on your AI assessment, you're invited for an interview for <strong>{job_title}</strong>.</p>
      <p>Our HR team will contact you shortly to schedule it.</p>
    </body></html>
    """
    result = await send_email_async(to_email, subject, body)
    if not result["success"]:
        logger.warning(f"Call for Interview Email failed for {to_email}: {result['error']}")
    return result["success"]

async def send_ticket_resolved_email(to_email: str, issue_type: str, hr_response: str, job_title: str = "your applied position"):
    subject = f"Re: Congratulations! You're invited to interview for {job_title}"
    body = f"""
    <html><body>
      <h2>Support Ticket Update</h2>
      <p>Your issue (<strong>{issue_type}</strong>) has been reviewed.</p>
      <div style="background:#f9f9f9; padding:15px; border-left:4px solid #3b82f6; margin:10px 0;">{hr_response}</div>
    </body></html>
    """
    result = await send_email_async(to_email, subject, body)
    if not result["success"]:
        logger.warning(f"Ticket Resolved Email failed for {to_email}: {result['error']}")
    return result["success"]

async def send_key_reissued_email(to_email: str, job_title: str, new_key: str, hr_response: str):
    subject = f"Re: Congratulations! You're invited to interview for {job_title}"
    body = f"""
    <html><body>
      <h2>Access Key Re-issued</h2>
      <p>Your request for <strong>{job_title}</strong> has been approved.</p>
      <div style="background:#f9f9f9; padding:15px; border-left:4px solid #10b981; margin:10px 0;">{hr_response}</div>
      <p><strong>New Access Key:</strong> <span style="background:#f4f4f4; padding:8px 12px; font-family:monospace; font-weight:bold;">{new_key}</span></p>
      <p><a href="{settings.frontend_base_url}/interview/access">Go to Interview Portal</a></p>
    </body></html>
    """
    result = await send_email_async(to_email, subject, body)
    if not result["success"]:
        logger.warning(f"Key Reissued Email failed for {to_email}: {result['error']}")
    return result["success"]
