"""Security middleware for Sentinel Vault.

Adds recommended security headers to all HTTP responses:
- Strict-Transport-Security (HSTS)
- X-Frame-Options (prevent clickjacking)
- X-Content-Type-Options (prevent MIME sniffing)
- Content-Security-Policy (CSP)
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Prevent browsers from MIME-sniffing a response away from the declared content-type
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking by forbidding rendering inside a frame/iframe
        response.headers["X-Frame-Options"] = "DENY"
        
        # Enforce HTTPS on clients (max-age = 1 year)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Restrict resources the browser can load (default to none, allow local scripts/styles for docs if needed)
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        
        # Provide some protection against XSS (mostly replaced by CSP but still good practice)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response
