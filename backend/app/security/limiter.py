"""Rate limiter configuration for Sentinel Vault.

Uses slowapi with an in-memory storage (can be backed by Redis in the future).
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

def _get_client_ip(request: Request) -> str:
    """Extract client IP securely, respecting X-Forwarded-For if available."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)

# Default limits can be defined here
limiter = Limiter(key_func=_get_client_ip, default_limits=["100/minute"])
