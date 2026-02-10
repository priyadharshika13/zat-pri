"""
Rate limiting middleware for subscription enforcement.

Enforces per-tenant API rate limits based on subscription plan.
Uses token bucket algorithm for rate limiting.
"""

import logging
import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.schemas.subscription import LimitExceededError

logger = logging.getLogger(__name__)


class TokenBucket:
    """
    Token bucket for rate limiting.
    
    Implements token bucket algorithm where tokens are added at a constant rate
    and requests consume tokens.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initializes token bucket.
        
        Args:
            capacity: Maximum number of tokens (rate limit per minute)
            refill_rate: Tokens added per second (capacity / 60)
        """
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempts to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens available, False otherwise
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self) -> None:
        """Refills tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
    
    def tokens_remaining(self) -> int:
        """Returns number of tokens remaining."""
        self._refill()
        return int(self.tokens)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for subscription-based rate limits.
    
    Enforces per-tenant rate limits based on subscription plan.
    Rate limits are retrieved from subscription service.
    """
    
    def __init__(self, app):
        """
        Initializes rate limiting middleware.
        
        Args:
            app: FastAPI application
        """
        super().__init__(app)
        # Token buckets per tenant (in-memory, resets on restart)
        self.buckets: Dict[int, TokenBucket] = {}
    
    async def dispatch(self, request: Request, call_next):
        """
        Processes request and enforces rate limits.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response or rate limit error
        """
        # Skip rate limiting for health checks and non-API routes
        if request.url.path.startswith("/health") or not request.url.path.startswith("/api"):
            return await call_next(request)
        
        # Get tenant context if available
        tenant_context = getattr(request.state, "tenant", None)
        
        if not tenant_context:
            # No tenant context - skip rate limiting (will fail auth anyway)
            return await call_next(request)
        
        # Get rate limit from subscription service
        try:
            from app.db.session import SessionLocal
            from app.services.subscription_service import SubscriptionService
            db = SessionLocal()
            try:
                subscription_service = SubscriptionService(db, tenant_context)
                rate_limit = subscription_service.get_rate_limit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Failed to get rate limit, using default: {e}")
            rate_limit = 60  # Default rate limit
        
        # Get or create token bucket for tenant
        tenant_id = tenant_context.tenant_id
        if tenant_id not in self.buckets:
            # Refill rate: tokens per second (rate_limit / 60)
            refill_rate = rate_limit / 60.0
            self.buckets[tenant_id] = TokenBucket(rate_limit, refill_rate)
        
        bucket = self.buckets[tenant_id]
        
        # Check if request can proceed
        if not bucket.consume():
            # Rate limit exceeded
            error = LimitExceededError(
                limit_type="RATE_LIMIT",
                message=f"Rate limit exceeded. Maximum {rate_limit} requests per minute.",
                upgrade_required=True,
                limit=rate_limit
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=error.model_dump()
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(bucket.tokens_remaining())
        
        return response

