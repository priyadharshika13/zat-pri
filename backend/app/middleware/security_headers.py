"""
Security headers middleware for production deployment.

Adds mandatory security headers to all responses:
- Content-Security-Policy (CSP)
- X-Frame-Options
- X-Content-Type-Options
- Referrer-Policy
- Strict-Transport-Security (HSTS)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.
    
    Security headers help protect against:
    - XSS attacks (CSP)
    - Clickjacking (X-Frame-Options)
    - MIME type sniffing (X-Content-Type-Options)
    - Information leakage (Referrer-Policy)
    - Protocol downgrade attacks (HSTS)
    """
    
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Swagger/OpenAPI only: skip CSP and strict headers so /docs works; security intact for rest
        path = request.url.path or ""
        if path.startswith("/docs") or path == "/openapi.json":
            return response

        settings = get_settings()

        # Content-Security-Policy (CSP)
        # Restricts resources that can be loaded to prevent XSS
        # Note: Adjust based on your frontend requirements
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # unsafe-eval needed for Vite dev, consider removing in production
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.openrouter.ai https://openrouter.ai; "  # For AI services
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # X-Frame-Options: Prevent clickjacking
        # DENY prevents the page from being displayed in a frame
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options: Prevent MIME type sniffing
        # nosniff prevents browsers from guessing content types
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Referrer-Policy: Control referrer information
        # strict-origin-when-cross-origin sends full URL for same-origin, origin only for cross-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Strict-Transport-Security (HSTS)
        # Force HTTPS for 1 year (31536000 seconds)
        # Only add in production with HTTPS enabled
        if settings.environment_name.lower() in ("production", "prod"):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # X-XSS-Protection (legacy, but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Permissions-Policy (formerly Feature-Policy)
        # Restrict access to browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=()"
        )
        
        return response

