import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def get_request_id(request: Any = None) -> str:
    """
    Extract request id from headers; fall back to a random id.
    Kept dependency-free and safe to call in non-HTTP contexts.
    """
    try:
        if request and hasattr(request, "headers"):
            rid = request.headers.get("x-request-id") or request.headers.get("X-Request-Id")
            if rid:
                return str(rid)
    except Exception:
        pass
    return secrets.token_hex(8)


def safe_hash(value: Optional[str]) -> Optional[str]:
    """Avoid logging raw sensitive strings; return a short SHA256 hex."""
    if not value:
        return None
    try:
        import hashlib

        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return digest[:12]
    except Exception:
        return None


def log_json(
    logger: logging.Logger,
    event: str,
    *,
    request_id: Optional[str] = None,
    user_id: Optional[Any] = None,
    endpoint: Optional[str] = None,
    status: Optional[Any] = None,
    level: str = "info",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Best-effort structured logging.
    Note: we emit JSON as a string to stay compatible with existing logging config.
    """
    payload: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
    }
    if request_id:
        payload["request_id"] = request_id
    if user_id is not None:
        payload["user_id"] = user_id
    if endpoint:
        payload["endpoint"] = endpoint
    if status is not None:
        payload["status"] = status
    if extra:
        # PII Protection: Recursively scrub strings in the extra dict
        def scrub_dict(d):
            if isinstance(d, dict):
                return {k: scrub_dict(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [scrub_dict(x) for x in d]
            elif isinstance(d, str):
                return filter_pii(d)
            return d
        payload["extra"] = scrub_dict(extra)

    msg = json.dumps(payload, ensure_ascii=False)
    if level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
    else:
        logger.info(msg)


import re

def filter_pii(text: str) -> str:
    """Mask common PII patterns: emails, phone numbers from strings."""
    if not text:
        return ""
    # Mask common patterns: emails
    text = re.sub(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", "[EMAIL_REDACTED]", text)
    # Mask common patterns: phone numbers (8+ digits with common separators)
    text = re.sub(r"(\+?\d[\d\s\-\(\)]{8,}\d)", "[PHONE_REDACTED]", text)
    return text


def log_ai_score_deviation(logger: logging.Logger, score: float, context: str, application_id: int):
    """Log warning if AI score is under 2.0 or over 9.0 (outlier detection)."""
    if score < 2.0 or score > 9.0:
        log_json(
            logger,
            "ai_score_deviation",
            level="warning",
            extra={
                "score": score,
                "context": context,
                "application_id": application_id,
                "threshold_breach": "low" if score < 2.0 else "high"
            }
        )
