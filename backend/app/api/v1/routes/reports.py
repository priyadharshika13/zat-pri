"""
Reporting API endpoints.

Provides read-only reporting endpoints for invoice and VAT analytics.
All reports are tenant-scoped and require authentication.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import math

from app.core.security import verify_api_key_and_resolve_tenant
from app.schemas.auth import TenantContext
from app.schemas.reporting import (
    InvoiceReportResponse,
    VATSummaryResponse,
    StatusBreakdownResponse,
    RevenueSummaryResponse
)
from app.models.invoice import InvoiceStatus
from app.core.constants import InvoiceMode
from app.services.reporting_service import ReportingService
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


def get_reporting_service(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)]
) -> ReportingService:
    """Dependency function for reporting service."""
    return ReportingService(db=db, tenant_context=tenant)


@router.get(
    "/invoices",
    response_model=InvoiceReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get paginated invoice report with filtering"
)
async def get_invoice_report(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    service: Annotated[ReportingService, Depends(get_reporting_service)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page (max 100)"),
    date_from: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter by end date (ISO format)"),
    status: Optional[InvoiceStatus] = Query(None, description="Filter by invoice status"),
    phase: Optional[InvoiceMode] = Query(None, description="Filter by invoice phase")
) -> InvoiceReportResponse:
    """
    Gets paginated invoice report with filtering options.
    
    CRITICAL: Only returns invoices belonging to the authenticated tenant.
    
    Filters:
    - date_from: Filter invoices created on or after this date
    - date_to: Filter invoices created on or before this date
    - status: Filter by invoice status (CREATED, PROCESSING, CLEARED, REJECTED, FAILED)
    - phase: Filter by invoice phase (PHASE_1, PHASE_2)
    
    Pagination:
    - page: Page number (default: 1, minimum: 1)
    - page_size: Items per page (default: 50, maximum: 100)
    
    Returns:
    - List of invoices with metadata
    - Total count and pagination information
    """
    try:
        invoices, total = service.get_invoice_report(
            page=page,
            page_size=page_size,
            date_from=date_from,
            date_to=date_to,
            status=status,
            phase=phase
        )
        
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        return InvoiceReportResponse(
            invoices=invoices,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Invoice report error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during invoice report generation"
        )


@router.get(
    "/vat-summary",
    response_model=VATSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get VAT summary aggregated by day or month"
)
async def get_vat_summary(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    service: Annotated[ReportingService, Depends(get_reporting_service)],
    date_from: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter by end date (ISO format)"),
    group_by: str = Query("day", description="Aggregation period: 'day' or 'month'")
) -> VATSummaryResponse:
    """
    Gets VAT summary aggregated by day or month.
    
    CRITICAL: Only returns data for the authenticated tenant.
    
    Query Parameters:
    - date_from: Filter by start date (ISO format)
    - date_to: Filter by end date (ISO format)
    - group_by: Aggregation period - 'day' (default) or 'month'
    
    Returns:
    - Summary items with date, tax amount, invoice amount, and invoice count
    - Total tax amount, total invoice amount, and total invoice count
    """
    try:
        if group_by not in ["day", "month"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="group_by must be 'day' or 'month'"
            )
        
        summary_items, total_tax, total_amount, total_count = service.get_vat_summary(
            date_from=date_from,
            date_to=date_to,
            group_by=group_by
        )
        
        return VATSummaryResponse(
            summary=summary_items,
            total_tax_amount=total_tax,
            total_invoice_amount=total_amount,
            total_invoice_count=total_count,
            date_from=date_from,
            date_to=date_to,
            group_by=group_by
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"VAT summary error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during VAT summary generation"
        )


@router.get(
    "/status-breakdown",
    response_model=StatusBreakdownResponse,
    status_code=status.HTTP_200_OK,
    summary="Get invoice status breakdown"
)
async def get_status_breakdown(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    service: Annotated[ReportingService, Depends(get_reporting_service)]
) -> StatusBreakdownResponse:
    """
    Gets invoice status breakdown for the authenticated tenant.
    
    CRITICAL: Only returns data for the authenticated tenant.
    
    Returns:
    - Breakdown of invoices by status (CREATED, PROCESSING, CLEARED, REJECTED, FAILED)
    - Total invoice count
    """
    try:
        breakdown_items, total = service.get_status_breakdown()
        
        return StatusBreakdownResponse(
            breakdown=breakdown_items,
            total_invoices=total
        )
        
    except Exception as e:
        logger.error(f"Status breakdown error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during status breakdown generation"
        )


@router.get(
    "/revenue-summary",
    response_model=RevenueSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get revenue summary"
)
async def get_revenue_summary(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    service: Annotated[ReportingService, Depends(get_reporting_service)]
) -> RevenueSummaryResponse:
    """
    Gets revenue summary for the authenticated tenant.
    
    CRITICAL: Only returns data for the authenticated tenant.
    
    Returns:
    - Total revenue (sum of all invoice amounts)
    - Total tax (sum of all tax amounts)
    - Net revenue (total revenue - total tax)
    - Cleared invoice count
    - Total invoice count
    """
    try:
        total_revenue, total_tax, net_revenue, cleared_count, total_count = service.get_revenue_summary()
        
        return RevenueSummaryResponse(
            total_revenue=total_revenue,
            total_tax=total_tax,
            net_revenue=net_revenue,
            cleared_invoice_count=cleared_count,
            total_invoice_count=total_count
        )
        
    except Exception as e:
        logger.error(f"Revenue summary error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during revenue summary generation"
        )

