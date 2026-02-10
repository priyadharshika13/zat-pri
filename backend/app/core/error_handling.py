"""
Enhanced error handling and resilience for production.

Provides structured error handling with context logging for:
- ZATCA downtime/timeouts
- AI provider failures
- Rate limit exhaustion
- Subscription limit exceeded
"""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
import httpx

from app.schemas.auth import TenantContext
from app.core.i18n import get_bilingual_error

logger = logging.getLogger(__name__)


def handle_zatca_error(
    error: Exception,
    tenant_context: Optional[TenantContext],
    invoice_number: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """
    Handles ZATCA API errors with structured logging.
    
    Args:
        error: Exception from ZATCA API call
        tenant_context: Tenant context (for logging)
        invoice_number: Invoice number (for logging)
        context: Additional context for logging
        
    Returns:
        HTTPException with appropriate status and message
    """
    tenant_id = tenant_context.tenant_id if tenant_context else None
    
    if isinstance(error, httpx.TimeoutException):
        logger.error(
            f"ZATCA timeout: invoice_number={invoice_number}, tenant_id={tenant_id}",
            extra={
                "error_type": "zatca_timeout",
                "invoice_number": invoice_number,
                "tenant_id": tenant_id,
                **(context or {})
            }
        )
        error_detail = get_bilingual_error("ZATCA_TIMEOUT")
        error_detail["reason"] = "timeout"
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=error_detail
        )
    
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        logger.error(
            f"ZATCA HTTP error: status={status_code}, invoice_number={invoice_number}, tenant_id={tenant_id}",
            extra={
                "error_type": "zatca_http_error",
                "status_code": status_code,
                "invoice_number": invoice_number,
                "tenant_id": tenant_id,
                **(context or {})
            }
        )
        
        if status_code >= 500:
            # ZATCA server error
            error_detail = get_bilingual_error("ZATCA_SERVER_ERROR")
            error_detail["reason"] = "server_error"
            error_detail["status_code"] = status_code
            return HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=error_detail
            )
        else:
            # ZATCA client error (4xx)
            error_detail = get_bilingual_error("ZATCA_CLIENT_ERROR")
            error_detail["reason"] = "client_error"
            error_detail["status_code"] = status_code
            error_detail["message_en"] = f"ZATCA API returned error: {status_code}"
            error_detail["message_ar"] = f"أعادت واجهة ZATCA خطأ: {status_code}"
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail
            )
    
    # Generic ZATCA error
    logger.error(
        f"ZATCA error: {str(error)}, invoice_number={invoice_number}, tenant_id={tenant_id}",
        extra={
            "error_type": "zatca_error",
            "error_message": str(error),
            "invoice_number": invoice_number,
            "tenant_id": tenant_id,
            **(context or {})
        },
        exc_info=True
    )
    error_detail = get_bilingual_error("ZATCA_ERROR")
    error_detail["reason"] = "unknown_error"
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=error_detail
    )


def handle_ai_provider_error(
    error: Exception,
    tenant_context: Optional[TenantContext],
    context: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """
    Handles AI provider errors with structured logging.
    
    Args:
        error: Exception from AI provider call
        tenant_context: Tenant context (for logging)
        context: Additional context for logging
        
    Returns:
        HTTPException with appropriate status and message
    """
    tenant_id = tenant_context.tenant_id if tenant_context else None
    
    if isinstance(error, httpx.TimeoutException):
        logger.error(
            f"AI provider timeout: tenant_id={tenant_id}",
            extra={
                "error_type": "ai_timeout",
                "tenant_id": tenant_id,
                **(context or {})
            }
        )
        error_detail = get_bilingual_error("AI_PROVIDER_TIMEOUT")
        error_detail["reason"] = "timeout"
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=error_detail
        )
    
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        logger.error(
            f"AI provider HTTP error: status={status_code}, tenant_id={tenant_id}",
            extra={
                "error_type": "ai_http_error",
                "status_code": status_code,
                "tenant_id": tenant_id,
                **(context or {})
            }
        )
        
        if status_code == 429:
            error_detail = get_bilingual_error("AI_RATE_LIMIT")
            error_detail["reason"] = "rate_limit"
            return HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_detail
            )
        
        if status_code >= 500:
            error_detail = get_bilingual_error("AI_PROVIDER_ERROR")
            error_detail["reason"] = "server_error"
            return HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=error_detail
            )
    
    logger.error(
        f"AI provider error: {str(error)}, tenant_id={tenant_id}",
        extra={
            "error_type": "ai_error",
            "error_message": str(error),
            "tenant_id": tenant_id,
            **(context or {})
        },
        exc_info=True
    )
    error_detail = get_bilingual_error("AI_PROVIDER_ERROR")
    error_detail["reason"] = "unknown_error"
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=error_detail
    )


def handle_subscription_limit_error(
    limit_type: str,
    tenant_context: Optional[TenantContext],
    context: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """
    Handles subscription limit exceeded errors with structured logging.
    
    Args:
        limit_type: Type of limit exceeded (INVOICE, AI, RATE_LIMIT)
        tenant_context: Tenant context (for logging)
        context: Additional context for logging
        
    Returns:
        HTTPException with appropriate status and message
    """
    tenant_id = tenant_context.tenant_id if tenant_context else None
    
    logger.warning(
        f"Subscription limit exceeded: limit_type={limit_type}, tenant_id={tenant_id}",
        extra={
            "error_type": "subscription_limit_exceeded",
            "limit_type": limit_type,
            "tenant_id": tenant_id,
            **(context or {})
        }
    )
    
    if limit_type == "RATE_LIMIT":
        error_detail = get_bilingual_error("RATE_LIMIT_EXCEEDED")
        error_detail["reason"] = "rate_limit"
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_detail
        )
    
    error_detail = get_bilingual_error("SUBSCRIPTION_LIMIT_EXCEEDED")
    error_detail["reason"] = "subscription_limit"
    error_detail["limit_type"] = limit_type
    # Add dynamic limit type to messages
    limit_type_lower = limit_type.lower()
    error_detail["message_en"] = f"Subscription limit exceeded for {limit_type_lower}. Please upgrade your plan."
    error_detail["message_ar"] = f"تم تجاوز حد الاشتراك لـ {limit_type_lower}. يرجى ترقية خطتك."
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=error_detail
    )

