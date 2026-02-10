"""
Audit logging middleware.

Provides request/response audit trail for compliance and monitoring.
Handles logging of API requests and responses.
Does not handle authentication or authorization.
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for audit logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Processes request and logs audit information.
        
        Args:
            request: HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        start_time = time.time()
        
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        
        logger.info(f"Request: {method} {path} from {client_ip}")
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        status_code = response.status_code
        tenant = getattr(request.state, "tenant", None)
        tenant_id = str(tenant.tenant_id) if tenant else "anonymous"
        logger.info(
            f"Response: {method} {path} - {status_code} - {process_time:.3f}s tenant_id={tenant_id}"
        )
        
        return response

