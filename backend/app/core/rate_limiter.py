"""
IP-based rate limiting for sensitive endpoints.
Uses slowapi (built on top of limits library).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

def get_real_remote_address(request):
    """Fallback if simple remote address is blocked or missing."""
    return get_remote_address(request) or "127.0.0.1"

# Global rate limiter instance — keyed by client IP
# Note: We use a custom wrapper to avoid rate-limiting OPTIONS (CORS preflight)
limiter = Limiter(key_func=get_real_remote_address)

