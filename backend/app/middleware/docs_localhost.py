"""
Docs localhost restriction middleware.

When DOCS_LOCALHOST_ONLY is True, serves /docs and /openapi.json only to
requests from localhost (127.0.0.1, ::1). Returns 404 for all other clients.
Production-safe: use with ENABLE_DOCS or ENVIRONMENT_NAME=local|dev only.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings

DOCS_PATHS = ("/docs", "/openapi.json", "/docs/")
LOCALHOST_IPS = ("127.0.0.1", "::1")


class DocsLocalhostMiddleware(BaseHTTPMiddleware):
    """
    Restricts Swagger UI and OpenAPI JSON to localhost when docs_localhost_only is True.

    Use with enable_docs=True (e.g. ENVIRONMENT_NAME=local|dev or ENABLE_DOCS=true).
    In production, set ENVIRONMENT_NAME=production so enable_docs is False and
    /docs is not registered at all.
    """

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.enable_docs or not settings.docs_localhost_only:
            return await call_next(request)

        path = request.scope.get("path", "").rstrip("/") or "/"
        if path not in ("/docs", "/openapi.json"):
            return await call_next(request)

        client_host = request.client.host if request.client else ""
        if client_host not in LOCALHOST_IPS:
            return JSONResponse(
                status_code=404,
                content={"detail": "Not Found"},
            )
        return await call_next(request)
