"""
X-Request-ID duplicate detection for safe retries across **multiple workers**.

Uses Redis ``SET key NX EX ttl`` when ``REDIS_URL`` is set so only one worker
claims a logical operation; others treat the request as a duplicate and replay
from DB / error paths as today.

Key shape: ``idem:{scope}:{logical_key}:{X-Request-ID}``

TTL is clamped between ``idempotency_ttl_min_seconds`` and ``idempotency_ttl_max_seconds``
(env: ``IDEMPOTENCY_TTL_MIN_SECONDS``, ``IDEMPOTENCY_TTL_MAX_SECONDS``; defaults 60–120).
Without Redis, falls back to the prior in-process dict (single-worker only).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from app.core.config import get_settings
from app.core.redis_store import get_redis_client

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_SEEN: dict[str, float] = {}


def _cleanup(now: float) -> None:
    stale_keys = [k for k, exp in _SEEN.items() if exp <= now]
    for k in stale_keys:
        _SEEN.pop(k, None)


def _idem_key(scope: str, logical_key: str, request_id: str) -> str:
    return f"idem:{scope}:{logical_key}:{request_id}"


def _clamp_ttl_redis(ttl_seconds: int) -> int:
    """
    Operational window for idempotency markers (Redis + in-memory).
    Bounds come from ``IDEMPOTENCY_TTL_MIN_SECONDS`` / ``IDEMPOTENCY_TTL_MAX_SECONDS``.
    """
    s = get_settings()
    lo = max(5, int(getattr(s, "idempotency_ttl_min_seconds", 60) or 60))
    hi = max(lo, int(getattr(s, "idempotency_ttl_max_seconds", 120) or 120))
    return max(lo, min(int(ttl_seconds), hi))


def is_duplicate_request(
    *,
    request_id: Optional[str],
    scope: str,
    key: str,
    ttl_seconds: int = 60,
) -> bool:
    """
    Optional idempotency guard.
    - If request_id is missing/blank, returns False (backward compatible).
    - If present, the first caller within TTL claims the key; later callers
      receive True (duplicate) and should replay from persistence or 409.
    """
    rid = (request_id or "").strip()
    if not rid:
        return False

    redis_key = _idem_key(scope, key, rid)
    ttl_redis = _clamp_ttl_redis(ttl_seconds)

    r = get_redis_client()
    if r is not None:
        try:
            # First SET NX wins; duplicate retries see key already present.
            ok = bool(r.set(redis_key, "1", nx=True, ex=ttl_redis))
            return not ok
        except Exception as e:
            logger.warning(
                "redis idempotency error; using process-local fallback: %s",
                e,
                exc_info=False,
            )

    now = time.time()
    with _LOCK:
        _cleanup(now)
        expires_at = _SEEN.get(redis_key)
        if expires_at and expires_at > now:
            return True
        _SEEN[redis_key] = now + float(ttl_redis)
    return False
