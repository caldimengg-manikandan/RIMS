import logging
import re
import time
from collections import deque
from typing import Optional

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, EmailStr

from app.core.observability import log_json, safe_hash

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "yopmail.com", "tempmail.com",
    "10minutemail.com", "discard.email", "throwawaymail.com", "temp-mail.org",
    "sharklasers.com", "nada.ltd"
}

_INVALID_EMAIL_ATTEMPTS = {}  # ip -> deque[timestamps]
_INVALID_EMAIL_WINDOW_SECONDS = 10 * 60
_INVALID_EMAIL_THRESHOLD = 20
_INVALID_EMAIL_DELAY_SECONDS = 0.05


def _record_invalid_email_attempt(ip: Optional[str], reason: str) -> float:
    """Return delay seconds to apply after exceeding threshold."""
    if not ip:
        return 0.0
    now = time.time()
    dq = _INVALID_EMAIL_ATTEMPTS.setdefault(ip, deque())
    # Purge old attempts
    while dq and dq[0] < now - _INVALID_EMAIL_WINDOW_SECONDS:
        dq.popleft()
    dq.append(now)

    if len(dq) > _INVALID_EMAIL_THRESHOLD:
        return _INVALID_EMAIL_DELAY_SECONDS
    return 0.0


def validate_email_strict_enterprise(
    email: str,
    *,
    ip: Optional[str] = None,
    request_id: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> str:
    """
    Enterprise-safe email validation.

    Backward-compatible requirements:
    - Throws ValueError with the same messages as the original implementation.
    - Returns normalized email (lower/trim) on success.
    - Adds structured logging + basic IP throttling only for invalid attempts.
    """
    logger = logger or logging.getLogger(__name__)

    if not email:
        raise ValueError("Email is required.")
        
    email = email.lower().strip()
    
    # Custom rule: Local part cannot be purely numeric
    local_part = email.split('@')[0] if '@' in email else ''
    if local_part.isdigit():
        log_json(
            logger,
            "email_validation_rejected",
            request_id=request_id,
            endpoint="apply_for_job",
            status=400,
            level="warning",
            extra={
                "reason": "numeric_local_part",
                "email_hash": safe_hash(email),
            },
        )
        delay = _record_invalid_email_attempt(ip, "numeric_local_part")
        if delay:
            time.sleep(delay)
        raise ValueError("Email local part cannot be only numbers.")
        
    # Use Pydantic EmailStr for strict syntax validation (no MX/DNS checks).
    class _EmailModel(BaseModel):
        email: EmailStr

    try:
        # EmailStr already normalizes casing; we additionally keep lower/trim consistent.
        normalized_email = _EmailModel(email=email).email
    except Exception as e:
        log_json(
            logger,
            "email_validation_rejected",
            request_id=request_id,
            endpoint="apply_for_job",
            status=400,
            level="warning",
            extra={
                "reason": "invalid_format",
                "email_hash": safe_hash(email),
            },
        )
        delay = _record_invalid_email_attempt(ip, "invalid_format")
        if delay:
            time.sleep(delay)
        raise ValueError("Enter a valid email (e.g., user@example.com)") from e

    # Keep the disposable-domain protection, but avoid MX/DNS checks.
    try:
        valid = validate_email(normalized_email, check_deliverability=False)
        domain = valid.domain
        if domain in DISPOSABLE_DOMAINS:
            log_json(
                logger,
                "email_validation_rejected",
                request_id=request_id,
                endpoint="apply_for_job",
                status=400,
                level="warning",
                extra={
                    "reason": "disposable",
                    "domain": domain,
                    "email_hash": safe_hash(normalized_email),
                },
            )
            delay = _record_invalid_email_attempt(ip, "disposable")
            if delay:
                time.sleep(delay)
            raise ValueError(f"Disposable email domains ({domain}) are not allowed.")
    except EmailNotValidError as e:
        log_json(
            logger,
            "email_validation_rejected",
            request_id=request_id,
            endpoint="apply_for_job",
            status=400,
            level="warning",
            extra={
                "reason": "invalid_format",
                "email_hash": safe_hash(normalized_email),
            },
        )
        delay = _record_invalid_email_attempt(ip, "invalid_format")
        if delay:
            time.sleep(delay)
        raise ValueError(str(e))

    return normalized_email


def validate_email_strict(email: str) -> str:
    """Backward-compatible wrapper (no request-scoped logging/throttling)."""
    return validate_email_strict_enterprise(email)
