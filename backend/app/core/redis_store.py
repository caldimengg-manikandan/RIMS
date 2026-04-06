"""
Shared Redis connection for idempotency and short-lived response replay caches.

When ``REDIS_URL`` is unset, callers fall back to in-process stores (single-worker only).
Use ``redis://...`` in production so all workers share the same key space.

On each access we ``PING`` the existing client; if the connection dropped, we discard
the client and reconnect so a transient Redis blip does not permanently disable Redis.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_client: Optional[object] = None  # redis.Redis when available


def get_redis_client():
    """
    Lazy singleton Redis client. Returns None if REDIS_URL is empty.
    Validates the connection with PING and transparently reconnects after failures.
    """
    global _client
    url = (get_settings().redis_url or "").strip()
    if not url:
        return None

    with _client_lock:
        if _client is not None:
            try:
                _client.ping()
                return _client
            except Exception as e:
                logger.warning(
                    "Redis ping failed; discarding client and reconnecting: %s",
                    e,
                    exc_info=False,
                )
                try:
                    _client.close()
                except Exception:
                    pass
                _client = None

        try:
            import redis as redis_lib

            r = redis_lib.Redis.from_url(url, decode_responses=True)
            r.ping()
            _client = r
            logger.info("Redis connected for idempotency / ephemeral replay cache")
        except Exception as e:
            logger.warning(
                "Redis unavailable; idempotency falls back to process-local: %s",
                e,
                exc_info=False,
            )
            _client = None

    return _client


def reset_redis_client_for_tests() -> None:
    """Close and clear singleton (tests only)."""
    global _client
    with _client_lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
        _client = None
