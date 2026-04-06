"""
Short-lived JSON response cache for idempotent HTTP retries (same X-Request-ID).

Used by transcribe and upload-video to return the **exact** JSON body on replay
without re-processing. With ``REDIS_URL``, replays work across workers.

Key shape: ``idem:{scope}:{logical_key}:{X-Request-ID}`` (same family as
``idempotency.is_duplicate_request``, but values are JSON payloads, not markers).

TTL uses the same bounds as ``idempotency`` (settings / env). Falls back to in-process dict when Redis is absent.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Optional

from app.core.config import get_settings
from app.core.redis_store import get_redis_client

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_store: dict[str, tuple[float, Any]] = {}


def _purge_unlocked(now: float) -> None:
    stale = [k for k, (exp, _) in _store.items() if exp <= now]
    for k in stale:
        _store.pop(k, None)


def _clamp_ttl(ttl_seconds: float) -> int:
    s = get_settings()
    lo = max(5, int(getattr(s, "idempotency_ttl_min_seconds", 60) or 60))
    hi = max(lo, int(getattr(s, "idempotency_ttl_max_seconds", 120) or 120))
    return max(lo, min(int(ttl_seconds), hi))


def cache_get(key: str) -> Optional[Any]:
    r = get_redis_client()
    if r is not None:
        try:
            raw = r.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.warning("redis ephemeral cache get failed: %s", e, exc_info=False)

    now = time.time()
    with _lock:
        _purge_unlocked(now)
        hit = _store.get(key)
        if not hit:
            return None
        exp, val = hit
        if exp <= now:
            _store.pop(key, None)
            return None
        return val


def cache_set(key: str, value: Any, ttl_seconds: float = 90) -> None:
    ttl = _clamp_ttl(ttl_seconds)
    r = get_redis_client()
    if r is not None:
        try:
            r.set(key, json.dumps(value), ex=ttl)
            return
        except Exception as e:
            logger.warning("redis ephemeral cache set failed: %s", e, exc_info=False)

    with _lock:
        _store[key] = (time.time() + float(ttl), value)
        _purge_unlocked(time.time())
