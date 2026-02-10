"""
Invoice processing API endpoints.

Handles invoice submission, validation, and ZATCA compliance processing.
Routes requests to appropriate service layer based on phase and environment.
Does not contain business logic - delegates to service layer.
"""

import logging
from fastapi import APIRouter, Body, Depends, HTTPException, status, Request, Query
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import math

from app.core.security import verify_api_key_and_resolve_tenant
from app.schemas.invoice import InvoiceRequest, InvoiceResponse
from app.schemas.invoice_history import (
    InvoiceListResponse, InvoiceDetailResponse, InvoiceStatusResponse, InvoiceListItem
)
from app.schemas.auth import TenantContext
from app.schemas.subscription import LimitExceededError
from app.services.invoice_service import InvoiceService
from app.services.invoice_history_service import InvoiceHistoryService
from app.services.invoice_log_service import InvoiceLogService
from app.services.subscription_service import SubscriptionService
from app.models.invoice_log import InvoiceLogStatus
from app.core.constants import Environment
from app.core.production_guards import check_production_access, require_production_confirmation, validate_write_action
from app.core.error_handling import handle_zatca_error, handle_subscription_limit_error
from app.core.i18n import get_bilingual_error, get_language_from_request, Language
from app.core.exceptions import SigningNotConfiguredError
from app.db.session import get_db
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoices", tags=["invoices"])

# Example request body for Swagger UI so "Try it out" sends all required fields
INVOICE_REQUEST_EXAMPLE = {
    "mode": "PHASE_2",
    "environment": "SANDBOX",
    "invoice_number": "INV-001",
    "invoice_date": "2025-01-15T10:00:00",
    "invoice_type": "388",
    "seller_name": "Acme Trading Co",
    "seller_tax_number": "300000000000003",
    "buyer_tax_number": "300000000000004",
    "line_items": [
        {
            "name": "Software Service",
            "quantity": 1,
            "unit_price": 100,
            "tax_rate": 15,
            "tax_category": "S",
            "discount": 0,
        }
    ],
    "total_tax_exclusive": 100,
    "total_tax_amount": 15,
    "total_amount": 115,
    "uuid": "INV-001-UUID",
    "previous_invoice_hash": "",
    "confirm_production": False,
}


def get_invoice_service(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)]
) -> InvoiceService:
    """Dependency function for invoice service with database and tenant context."""
    return InvoiceService(db=db, tenant_context=tenant)


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Process invoice for ZATCA compliance"
)
async def process_invoice(
    request: Annotated[InvoiceRequest, Body(example=INVOICE_REQUEST_EXAMPLE)],
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    db: Annotated[Session, Depends(get_db)]
) -> InvoiceResponse:
    """
    Processes an invoice according to ZATCA compliance requirements.
    
    Supports both Phase-1 (QR code generation) and Phase-2 (XML signing, clearance).
    Validates invoice data before processing and returns validation results on failure.
    Mode and environment are determined from the request payload.
    
    CRITICAL: Subscription limits are enforced before invoice creation.
    Phase 9: Production access and confirmation guards are enforced.
    """
    # Phase 9: Validate write action permission
    validate_write_action(tenant, db, "create_invoice")
    
    # Phase 9: Check production access (only paid plans can submit to Production)
    check_production_access(tenant, db, request.environment)
    
    # Phase 9: Require explicit confirmation for Production submissions
    require_production_confirmation(request, request.confirm_production)
    
    # CRITICAL: Enforce subscription limits before processing
    try:
        subscription_service = SubscriptionService(db, tenant)
        allowed, limit_error = subscription_service.check_invoice_limit()
        
        if not allowed:
            # Determine appropriate status code
            status_code = status.HTTP_403_FORBIDDEN
            if limit_error and limit_error.limit_type == "RATE_LIMIT":
                status_code = status.HTTP_429_TOO_MANY_REQUESTS
            
            raise HTTPException(
                status_code=status_code,
                detail=limit_error.model_dump() if limit_error else {"message": "Invoice limit exceeded"}
            )
    except HTTPException:
        # Re-raise HTTPException (limit exceeded)
        raise
    except Exception as e:
        # If subscription check fails, still raise proper HTTPException, not 500
        logger.error(f"Subscription limit check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Unable to verify subscription limits. Please contact support."}
        )
    
    try:
        # REFACTORED: Use new persistence method
        # This ensures invoice is persisted BEFORE processing and InvoiceLog is always written
        result = await service.process_invoice_with_persistence(
            request=request,
            db=db,
            tenant_context=tenant
        )
        
        # CRITICAL: Only increment counter on successful invoice creation
        # Do not count failed or rejected invoices
        success = (
            result.get("success")
            if isinstance(result, dict)
            else getattr(result, "success", False)
        )
        
        if success:
            subscription_service.increment_invoice_count()
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTPException (e.g. 503 from cert_manager for missing tenant certs)
        raise
    except SigningNotConfiguredError as e:
        # Phase-2: real signing required; no placeholder may reach ZATCA
        logger.warning(
            f"Phase-2 signing not available: {e}, invoice_number={request.invoice_number}, tenant_id={tenant.tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "SIGNING_NOT_CONFIGURED",
                "message_en": "Signing is not available for this tenant or environment. Upload per-tenant certificates (certs/tenant_<id>/sandbox or production) or contact support.",
                "message_ar": "التوقيع غير متاح لهذا المستأجر أو البيئة. قم بتحميل الشهادات لكل مستأجر أو اتصل بالدعم.",
                "reason": str(e),
            },
        )
    except FileNotFoundError as e:
        logger.warning(
            f"Invoice processing failed (missing file): {e}, invoice_number={request.invoice_number}, tenant_id={tenant.tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "SIGNING_NOT_CONFIGURED",
                "message_en": "Signing certificate or private key not found. Upload tenant certificates for Phase-2.",
                "message_ar": "شهادة التوقيع أو المفتاح الخاص غير موجود. قم بتحميل شهادات المستأجر للمرحلة الثانية.",
                "reason": str(e),
            },
        )
    except Exception as e:
        # Phase 9: Enhanced error handling with context
        import httpx
        if isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError)):
            raise handle_zatca_error(e, tenant, request.invoice_number, {"environment": request.environment.value})
        
        logger.error(
            f"Invoice processing error: {e}, invoice_number={request.invoice_number}, tenant_id={tenant.tenant_id}",
            extra={
                "error_type": "invoice_processing_error",
                "invoice_number": request.invoice_number,
                "tenant_id": tenant.tenant_id,
                "environment": request.environment.value
            },
            exc_info=True
        )
        error_detail = get_bilingual_error("SERVER_ERROR")
        error_detail["reason"] = "internal_error"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get(
    "",
    response_model=InvoiceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List invoices with pagination and filtering"
)
async def list_invoices(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(50, ge=1, le=100, description="Number of items per page (max 100)"),
    invoice_number: Optional[str] = Query(None, description="Filter by invoice number (partial match)"),
    status: Optional[InvoiceLogStatus] = Query(None, description="Filter by status"),
    environment: Optional[Environment] = Query(None, description="Filter by environment"),
    date_from: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter by end date (ISO format)")
) -> InvoiceListResponse:
    """
    Lists invoices for the current tenant with pagination and filtering.
    
    **CRITICAL: Only returns invoices belonging to the authenticated tenant.**
    
    **Pagination:**
    - page: Page number (default: 1, minimum: 1)
    - limit: Items per page (default: 50, maximum: 100)
    
    **Filters:**
    - invoice_number: Partial match on invoice number
    - status: Filter by status (SUBMITTED, CLEARED, REJECTED, ERROR)
    - environment: Filter by environment (SANDBOX or PRODUCTION)
    - date_from: Filter invoices created on or after this date
    - date_to: Filter invoices created on or before this date
    
    **Returns:**
    - List of invoices with metadata
    - Total count
    - Pagination information
    """
    try:
        service = InvoiceHistoryService(db, tenant)
        invoices, total = service.list_invoices(
            page=page,
            limit=limit,
            invoice_number=invoice_number,
            status=status,
            environment=environment,
            date_from=date_from,
            date_to=date_to
        )
        
        total_pages = math.ceil(total / limit) if total > 0 else 0
        
        return InvoiceListResponse(
            invoices=[InvoiceListItem.model_validate(inv) for inv in invoices],
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Invoice list error: {e}")
        error_detail = get_bilingual_error("SERVER_ERROR")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get invoice details by ID"
)
async def get_invoice(
    invoice_id: int,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> InvoiceDetailResponse:
    """
    Gets detailed information about a specific invoice.
    
    **CRITICAL: Only returns invoices belonging to the authenticated tenant.**
    
    **Returns:**
    - Invoice details including UUID, hash, status, ZATCA response code
    - Inferred phase (if determinable from log data)
    
    **Note:**
    - This endpoint fetches data from the database only
    - It does NOT re-call ZATCA APIs
    - Phase inference is heuristic-based (Phase-2 invoices have UUID/hash)
    """
    try:
        service = InvoiceHistoryService(db, tenant)
        invoice = service.get_invoice_by_id(invoice_id)
        
        if not invoice:
            error_detail = get_bilingual_error("INVOICE_NOT_FOUND")
            error_detail["invoice_id"] = invoice_id
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail
            )
        
        # Infer phase
        phase = service._infer_phase(invoice)
        
        response = InvoiceDetailResponse.model_validate(invoice)
        response.phase = phase
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invoice retrieval error: {e}")
        error_detail = get_bilingual_error("SERVER_ERROR")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get(
    "/{invoice_number}/status",
    response_model=InvoiceStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get invoice status by invoice number"
)
async def get_invoice_status(
    invoice_number: str,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> InvoiceStatusResponse:
    """
    Gets the current status of an invoice by invoice number.
    
    **CRITICAL: Only returns invoices belonging to the authenticated tenant.**
    
    **Returns:**
    - Current status (SUBMITTED, CLEARED, REJECTED, ERROR)
    - ZATCA response code (if available)
    - UUID and hash (if available)
    - Environment and timestamps
    
    **Note:**
    - This endpoint fetches data from the database only
    - It does NOT re-call ZATCA APIs
    - Returns the most recent log entry for the invoice number
    """
    try:
        service = InvoiceHistoryService(db, tenant)
        invoice = service.get_invoice_status(invoice_number)
        
        if not invoice:
            error_detail = get_bilingual_error("INVOICE_NOT_FOUND")
            error_detail["invoice_number"] = invoice_number
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail
            )
        
        return InvoiceStatusResponse(
            invoice_number=invoice.invoice_number,
            status=invoice.status,
            zatca_response_code=invoice.zatca_response_code,
            uuid=invoice.uuid,
            hash=invoice.hash,
            environment=invoice.environment,
            created_at=invoice.created_at,
            last_updated=invoice.created_at  # InvoiceLog doesn't have updated_at, use created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invoice status retrieval error: {e}")
        error_detail = get_bilingual_error("SERVER_ERROR")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.post(
    "/{invoice_id}/retry",
    response_model=InvoiceResponse,
    status_code=status.HTTP_200_OK,
    summary="Retry processing a FAILED or REJECTED invoice"
)
async def retry_invoice(
    invoice_id: int,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    service: Annotated[InvoiceService, Depends(get_invoice_service)],
    db: Annotated[Session, Depends(get_db)]
) -> InvoiceResponse:
    """
    Retries processing a FAILED or REJECTED invoice.
    
    **CRITICAL RULES:**
    1. Only invoices with status FAILED or REJECTED can be retried
    2. CLEARED invoices must NOT be retried (returns 400)
    3. Tenant isolation is enforced (invoice must belong to tenant)
    4. Invoice master record is reused (NO new invoice row)
    5. Status flow: FAILED/REJECTED → PROCESSING → CLEARED/REJECTED/FAILED
    6. Creates audit log entry with action="RETRY"
    7. Reuses existing invoice processing logic
    
    **Returns:**
    - Invoice processing response with updated status
    
    **Errors:**
    - 404: Invoice not found or doesn't belong to tenant
    - 400: Invoice status is CLEARED or invalid for retry
    - 500: Internal server error during retry processing
    """
    # Phase 9: Validate write action permission
    validate_write_action(tenant, db, "retry_invoice")
    
    try:
        result = await service.retry_invoice(db, invoice_id, tenant)
        return result
        
    except ValueError as e:
        # Handle validation errors (not found, invalid status, etc.)
        error_message = str(e)
        
        if "not found" in error_message.lower() or "access denied" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_message
            )
        else:
            # Invalid status or other validation errors
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., subscription limits)
        raise
    
    except Exception as e:
        logger.error(
            f"Invoice retry error: invoice_id={invoice_id}, tenant_id={tenant.tenant_id}, error={e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during invoice retry"
        )
