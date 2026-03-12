import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from typing import Optional
from app.core.config import get_settings
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def send_email_sync(to_email: str, subject: str, html_body: str) -> bool:
    """Synchronous implementation of sending an email with retries"""
    if not all([settings.smtp_host, settings.smtp_port, settings.smtp_user, settings.smtp_password, settings.smtp_from]):
        print("\n" + "="*50)
        print(f"[EMAIL MOCK] To: {to_email}")
        print(f"[EMAIL MOCK] Subject: {subject}")
        print(f"[EMAIL MOCK] Body: {html_body}")
        print("="*50 + "\n")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    part = MIMEText(html_body, "html")
    msg.attach(part)

    # Connect and send
    server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
    server.starttls()
    server.login(settings.smtp_user, settings.smtp_password)
    server.sendmail(settings.smtp_from, to_email, msg.as_string())
    server.quit()
    return True

async def send_email_async(to_email: str, subject: str, html_body: str) -> bool:
    """Asynchronously send an email using asyncio loop to avoid blocking"""
    try:
        loop = asyncio.get_running_loop()
        # Run the synchronous smtplib code in an executor thread
        success = await loop.run_in_executor(None, send_email_sync, to_email, subject, html_body)
        return success
    except Exception as e:
        logger.error(f"Persistent failure sending email to {to_email} after retries: {e}")
        # We return False here but it's now logged and was retried
        return False

# --- Standard Email Templates ---

async def send_otp_email(to_email: str, otp: str):
    subject = "Verify your account for the Recruitment System"
    body = f"""
    <html>
      <body>
        <h2>Account Verification</h2>
        <p>Thank you for registering! Please use the following One-Time Password to verify your account.</p>
        <h3 style="background:#f4f4f4; padding:10px; display:inline-block; letter-spacing: 5px;">{otp}</h3>
        <p>This code will expire in 30 minutes.</p>
      </body>
    </html>
    """
    await send_email_async(to_email, subject, body)

async def send_application_received_email(to_email: str, job_title: str):
    subject = f"Application Received: {job_title}"
    body = f"""
    <html>
      <body>
        <h2>Thank You for Applying!</h2>
        <p>We have successfully received your application for the <strong>{job_title}</strong> position.</p>
        <p>Our team (and AI systems) will review your profile shortly. We will reach out if there is a match!</p>
      </body>
    </html>
    """
    await send_email_async(to_email, subject, body)

async def send_approved_for_interview_email(to_email: str, job_title: str, raw_access_key: str = ""):
    subject = f"Congratulations! You're invited to interview for {job_title}"
    
    body = f"""
    <html>
      <body>
        <h2>Interview Invitation</h2>
        <p>Congratulations! Your application for <strong>{job_title}</strong> has been approved.</p>
        <p>You have been granted a one-time secure access key to complete your AI Interview. This key will expire in exactly 24 hours.</p>
        <br>
        <p><strong>Your Access Key:</strong> <span style="background:#f4f4f4; padding:8px 12px; letter-spacing: 2px; font-family: monospace;">{raw_access_key}</span></p>
        <br>
        <p>Please go to our <a href="{settings.frontend_base_url}/interview/access">Interview Portal</a> and enter your email and access key to begin.</p>
        <br>
        <hr style="border:none; border-top:1px solid #eee;">
        <p style="font-size: 0.9em; color: #666;">
          Have issues or grievances? You can report them via our 
          <a href="{settings.frontend_base_url}/support">Support Portal</a>.
        </p>
      </body>
    </html>
    """
    await send_email_async(to_email, subject, body)

async def send_hired_email(to_email: str, job_title: str, interview=None):
    subject = "Congratulations — Next Stage Interview"
    
    stage_text = "the First Level Interview"
    if interview and getattr(interview, 'aptitude_score', None) is not None:
        stage_text = "Aptitude and First Level Interview"
        
    body = f"""
    <html>
      <body>
        <h2>Congratulations!</h2>
        <p>We are thrilled to let you know that you have successfully cleared {stage_text} for the <strong>{job_title}</strong> position.</p>
        <p>You have now been invited to the <strong>Face-to-Face</strong> stage of our interview process.</p>
        <p>Our HR team will be in touch with you shortly regarding the scheduling and next steps.</p>
      </body>
    </html>
    """
    await send_email_async(to_email, subject, body)

async def send_rejected_email(to_email: str, job_title: str, is_ai_auto_reject: bool = False):
    subject = f"Update on your application for {job_title}"
    body = f"""
    <html>
      <body>
        <h2>Application Update</h2>
        <p>Thank you for applying to the <strong>{job_title}</strong> position at our company.</p>
        <p>While we appreciate your interest, we {"have decided to move forward with other candidates at this time." if not is_ai_auto_reject else "found that your resume did not align closely enough with the job requirements."}</p>
        <p>This concludes the application and interview process for this role, but we encourage you to apply for other roles in the future that align with your skills and experience!</p>
        <p>We wish you the best in your career journey.</p>
      </body>
    </html>
    """
    await send_email_async(to_email, subject, body)

async def send_call_for_interview_email(to_email: str, job_title: str):
    subject = f"Interview Invitation — {job_title}"
    body = f"""
    <html>
      <body>
        <h2>You're Invited for an Interview!</h2>
        <p>Congratulations! Based on your performance in the AI assessment, we would like to invite you for an in-person/virtual interview for the <strong>{job_title}</strong> position.</p>
        <p>Our HR team will be in touch with you shortly to schedule the interview.</p>
        <p>Please ensure you are available and prepared.</p>
        <br>
        <p>Best of luck!</p>
      </body>
    </html>
    """
    await send_email_async(to_email, subject, body)

async def send_ticket_resolved_email(to_email: str, issue_type: str, hr_response: str, job_title: str = "your applied position"):
    # Using the same subject as invitation with Re: prefix to encourage threading
    subject = f"Re: Congratulations! You're invited to interview for {job_title}"
    body = f"""
    <html>
      <body>
        <h2>Support Ticket Update</h2>
        <p>Your reported issue (<strong>{issue_type}</strong>) has been reviewed by our HR team.</p>
        <p><strong>HR Response:</strong></p>
        <div style="background:#f9f9f9; padding:15px; border-left:4px solid #3b82f6; margin:10px 0;">
          {hr_response}
        </div>
        <p>Thank you for your patience.</p>
      </body>
    </html>
    """
    await send_email_async(to_email, subject, body)

async def send_key_reissued_email(to_email: str, job_title: str, new_key: str, hr_response: str):
    # Using the same subject as invitation with Re: prefix to encourage threading
    subject = f"Re: Congratulations! You're invited to interview for {job_title}"
    body = f"""
    <html>
      <body>
        <h2>Support Ticket Resolved - Access Key Re-issued</h2>
        <p>Your request for a second chance/re-issue for the <strong>{job_title}</strong> interview has been approved.</p>
        
        <p><strong>HR Response:</strong></p>
        <div style="background:#f9f9f9; padding:15px; border-left:4px solid #10b981; margin:10px 0;">
          {hr_response}
        </div>

        <p>Your new secure access key is provided below. This key is for one-time use.</p>
        <br>
        <p><strong>Your New Access Key:</strong> <span style="background:#f4f4f4; padding:8px 12px; letter-spacing: 2px; font-family: monospace; font-weight: bold;">{new_key}</span></p>
        <br>
        <p>Please go to our <a href="{settings.frontend_base_url}/interview/access">Interview Portal</a> to continue your process.</p>
        <p>If you encounter any other issues, you can always reach out via our <a href="{settings.frontend_base_url}/support">Support Portal</a>.</p>
      </body>
    </html>
    """
    await send_email_async(to_email, subject, body)
