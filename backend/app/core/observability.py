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
        payload["extra"] = extra

    msg = json.dumps(payload, ensure_ascii=False)
    if level == "warning":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
    else:
        logger.info(msg)

