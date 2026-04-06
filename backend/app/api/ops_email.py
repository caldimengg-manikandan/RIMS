from __future__ import annotations

import logging
from typing import Any, Optional, Literal

import httpx
import smtplib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.core.auth import get_current_admin
from app.core.config import get_settings
from app.domain.models import User
from app.services.email_service import send_email_async

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/ops/email", tags=["ops-email"])


class EmailTestRequest(BaseModel):
    to_email: EmailStr
    subject: str = Field(default="RIMS email test")
    html_body: str = Field(default="<html><body><p>RIMS email test.</p></body></html>")
    provider: Optional[str] = Field(
        default=None,
        description="Optional override: 'resend' or 'smtp'. If omitted, normal selection logic applies.",
    )


class ResendHealthOut(BaseModel):
    status: Literal["ok", "error"]
    verified_from: str
    error: str = ""


class SmtpHealthOut(BaseModel):
    status: Literal["ok", "error"]
    host: str
    error: str = ""


class EmailHealthOut(BaseModel):
    resend: ResendHealthOut
    smtp: SmtpHealthOut


class ProviderHealth(BaseModel):
    configured: bool
    ok: bool
    detail: str = ""
    extra: dict[str, Any] = {}


class EmailHealthResponse(BaseModel):
    resend: ProviderHealth
    smtp: ProviderHealth
    effective_from: str


def _effective_from() -> str:
    return (settings.resend_from or settings.smtp_from or settings.smtp_user or "").strip()


async def _check_resend_domain_verified() -> ProviderHealth:
    api_key = (settings.resend_api_key or "").strip()
    from_email = _effective_from()
    if not api_key:
        return ProviderHealth(configured=False, ok=False, detail="RESEND_API_KEY not configured")
    if not from_email or "@" not in from_email:
        return ProviderHealth(configured=True, ok=False, detail="No effective from address configured for Resend")

    domain = from_email.split("@", 1)[1].lower().strip()
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get("https://api.resend.com/domains", headers=headers)
        if resp.status_code != 200:
            return ProviderHealth(
                configured=True,
                ok=False,
                detail=f"Resend domains API failed: HTTP {resp.status_code}",
                extra={"domain": domain, "body_preview": (resp.text or "")[:300]},
            )

        data = resp.json()
        domains = data.get("data") or []
        match = None
        for d in domains:
            if (d.get("name") or "").lower().strip() == domain:
                match = d
                break

        if not match:
            return ProviderHealth(
                configured=True,
                ok=False,
                detail="From domain not found in Resend account (not added/verified)",
                extra={"domain": domain},
            )

        status = (match.get("status") or "").lower().strip()
        verified = status in {"verified", "active"}
        return ProviderHealth(
            configured=True,
            ok=verified,
            detail=f"Resend domain status: {status or '<unknown>'}",
            extra={"domain": domain, "raw_status": match.get("status")},
        )
    except Exception as e:
        logger.error("Resend health check failed", exc_info=True)
        return ProviderHealth(configured=True, ok=False, detail=f"Resend health check exception: {e}")


def _check_smtp_connect_and_auth() -> ProviderHealth:
    host = (settings.smtp_host or "").strip()
    user = (settings.smtp_user or "").strip()
    pwd = (settings.smtp_password or "").strip()
    port = int(settings.smtp_port or 0)

    if not (host and user and pwd and port):
        return ProviderHealth(configured=False, ok=False, detail="SMTP_* not fully configured")

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, pwd)
        return ProviderHealth(configured=True, ok=True, detail="SMTP connect+STARTTLS+AUTH ok", extra={"host": host, "port": port})
    except Exception as e:
        logger.error("SMTP health check failed", exc_info=True)
        return ProviderHealth(configured=True, ok=False, detail=f"SMTP health check exception: {e}", extra={"host": host, "port": port, "exc_class": e.__class__.__name__})


@router.get("/health", response_model=EmailHealthResponse)
async def email_health_check(current_admin: User = Depends(get_current_admin)):
    resend_health = await _check_resend_domain_verified()
    smtp_health = _check_smtp_connect_and_auth()
    return EmailHealthResponse(
        resend=resend_health,
        smtp=smtp_health,
        effective_from=_effective_from(),
    )


@router.get("/health-v2", response_model=EmailHealthOut)
async def email_health_check_v2(current_admin: User = Depends(get_current_admin)):
    resend_health = await _check_resend_domain_verified()
    smtp_health = _check_smtp_connect_and_auth()

    verified_from = _effective_from()
    smtp_host = (settings.smtp_host or "").strip()

    return EmailHealthOut(
        resend=ResendHealthOut(
            status="ok" if resend_health.ok else "error",
            verified_from=verified_from,
            error="" if resend_health.ok else (resend_health.detail or "Resend misconfigured"),
        ),
        smtp=SmtpHealthOut(
            status="ok" if smtp_health.ok else "error",
            host=smtp_host,
            error="" if smtp_health.ok else (smtp_health.detail or "SMTP misconfigured"),
        ),
    )


@router.post("/test")
async def send_test_email(payload: EmailTestRequest, current_admin: User = Depends(get_current_admin)):
    # Provider override is intentionally minimal: it forces the config path by temporarily masking settings.
    provider = (payload.provider or "").strip().lower() or None

    if provider not in (None, "resend", "smtp"):
        raise HTTPException(status_code=400, detail="provider must be 'resend', 'smtp', or omitted")

    # If forcing SMTP, ensure Resend isn't selected by selection logic.
    if provider == "smtp":
        original = settings.resend_api_key
        try:
            settings.resend_api_key = ""
            result = await send_email_async(str(payload.to_email), payload.subject, payload.html_body)
        finally:
            settings.resend_api_key = original
        return {"success": bool(result.get("success")), **result}

    # If forcing Resend, just call the normal function (it prefers Resend when configured).
    result = await send_email_async(str(payload.to_email), payload.subject, payload.html_body)
    return {"success": bool(result.get("success")), **result}

