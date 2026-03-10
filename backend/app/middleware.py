"""
Performance middleware: slow-query and slow-route logging.
Logs any request taking >500ms with structured output.

Uses pure Starlette middleware (not BaseHTTPMiddleware) to avoid
the known issue where BaseHTTPMiddleware strips CORS headers set
by CORSMiddleware, causing browser "Failed to fetch" errors.
"""
import time
import logging
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

class PerformanceLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                elapsed_ms = (time.perf_counter() - start) * 1000
                if elapsed_ms > 500:
                    path = scope.get("path", "")
                    method = scope.get("method", "")
                    status = message.get("status", 0)
                    logger.warning(
                        f"[SLOW ROUTE] method={method} "
                        f"route={path} "
                        f"time={elapsed_ms:.0f}ms "
                        f"status={status}"
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)
