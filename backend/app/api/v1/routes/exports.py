"""
Export API endpoints.

Provides data export functionality for invoices and invoice logs.
Supports CSV, JSON, and XML formats with streaming for large datasets.
All exports are tenant-scoped and require authentication.
"""

import logging
from datetime import datetime
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.security import verify_api_key_and_resolve_tenant
from app.schemas.auth import TenantContext
from app.models.invoice import InvoiceStatus
from app.models.invoice_log import InvoiceLogStatus
from app.core.constants import InvoiceMode, Environment
from app.core.production_guards import check_production_access
from app.services.export_service import ExportService
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exports", tags=["exports"])


def get_export_service(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)]
) -> ExportService:
    """Dependency function for export service."""
    return ExportService(db=db, tenant_context=tenant)


def generate_filename(export_type: str, format: str) -> str:
    """
    Generates export filename with timestamp.
    
    Format: {type}_export_{YYYYMMDD_HHMMSS}.{ext}
    
    Args:
        export_type: Type of export ('invoices' or 'invoice_logs')
        format: Export format ('csv', 'json', 'xml')
        
    Returns:
        Filename string
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{export_type}_export_{timestamp}.{format}"


@router.get(
    "/invoices",
    summary="Export invoices to CSV or JSON"
)
async def export_invoices(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    service: Annotated[ExportService, Depends(get_export_service)],
    db: Annotated[Session, Depends(get_db)],
    format: str = Query("csv", regex="^(csv|json)$", description="Export format (csv or json)"),
    date_from: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter by end date (ISO format)"),
    invoice_number: Optional[str] = Query(None, description="Filter by invoice number (partial match)"),
    status: Optional[InvoiceStatus] = Query(None, description="Filter by invoice status"),
    phase: Optional[InvoiceMode] = Query(None, description="Filter by invoice phase"),
    environment: Optional[Environment] = Query(None, description="Filter by environment")
) -> StreamingResponse:
    """
    Exports invoices to CSV or JSON format.
    
    **CRITICAL: Only exports invoices belonging to the authenticated tenant.**
    
    **Filters:**
    - date_from: Filter invoices created on or after this date
    - date_to: Filter invoices created on or before this date
    - invoice_number: Filter by invoice number (partial match, case-insensitive)
    - status: Filter by invoice status (CREATED, PROCESSING, CLEARED, REJECTED, FAILED)
    - phase: Filter by invoice phase (PHASE_1, PHASE_2)
    - environment: Filter by environment (SANDBOX, PRODUCTION)
    
    **Production Access:**
    - Production exports require active subscription (paid plan)
    - Sandbox exports are always allowed
    
    **Response:**
    - Streaming response for efficient handling of large datasets
    - Proper Content-Type and Content-Disposition headers
    - Filename includes timestamp: invoices_export_YYYYMMDD_HHMMSS.{format}
    
    **Formats:**
    - CSV: Comma-separated values with header row
    - JSON: Newline-delimited JSON (NDJSON) format
    """
    # Check production access if filtering by production environment
    if environment == Environment.PRODUCTION:
        check_production_access(tenant, db, environment)
    
    try:
        # Generate filename
        filename = generate_filename("invoices", format)
        
        # Determine content type and export method
        if format == "csv":
            content_type = "text/csv; charset=utf-8"
            export_generator = service.export_invoices_csv(
                date_from=date_from,
                date_to=date_to,
                invoice_number=invoice_number,
                status=status,
                phase=phase,
                environment=environment
            )
        elif format == "json":
            content_type = "application/json; charset=utf-8"
            export_generator = service.export_invoices_json(
                date_from=date_from,
                date_to=date_to,
                invoice_number=invoice_number,
                status=status,
                phase=phase,
                environment=environment
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {format}. Supported formats: csv, json"
            )
        
        # Create streaming response
        return StreamingResponse(
            export_generator,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invoice export error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during invoice export"
        )


@router.get(
    "/invoice-logs",
    summary="Export invoice logs (audit trail) to CSV or JSON"
)
async def export_invoice_logs(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    service: Annotated[ExportService, Depends(get_export_service)],
    db: Annotated[Session, Depends(get_db)],
    format: str = Query("csv", regex="^(csv|json)$", description="Export format (csv or json)"),
    date_from: Optional[datetime] = Query(None, description="Filter by start date (ISO format)"),
    date_to: Optional[datetime] = Query(None, description="Filter by end date (ISO format)"),
    invoice_number: Optional[str] = Query(None, description="Filter by invoice number (partial match)"),
    status: Optional[InvoiceLogStatus] = Query(None, description="Filter by log status"),
    environment: Optional[Environment] = Query(None, description="Filter by environment")
) -> StreamingResponse:
    """
    Exports invoice logs (audit trail) to CSV or JSON format.
    
    **CRITICAL: Only exports logs belonging to the authenticated tenant.**
    
    **Filters:**
    - date_from: Filter logs created on or after this date
    - date_to: Filter logs created on or before this date
    - invoice_number: Filter by invoice number (partial match, case-insensitive)
    - status: Filter by log status (SUBMITTED, CLEARED, REJECTED, ERROR)
    - environment: Filter by environment (SANDBOX, PRODUCTION)
    
    **Production Access:**
    - Production exports require active subscription (paid plan)
    - Sandbox exports are always allowed
    
    **Response:**
    - Streaming response for efficient handling of large datasets
    - Proper Content-Type and Content-Disposition headers
    - Filename includes timestamp: invoice_logs_export_YYYYMMDD_HHMMSS.{format}
    
    **ZATCA Compliance:**
    - Invoice logs provide complete audit trail for compliance
    - Includes all processing events, retries, and ZATCA responses
    - Essential for ZATCA audit requirements
    
    **Formats:**
    - CSV: Comma-separated values with header row
    - JSON: Newline-delimited JSON (NDJSON) format
    """
    # Check production access if filtering by production environment
    if environment == Environment.PRODUCTION:
        check_production_access(tenant, db, environment)
    
    try:
        # Generate filename
        filename = generate_filename("invoice_logs", format)
        
        # Determine content type and export method
        if format == "csv":
            content_type = "text/csv; charset=utf-8"
            export_generator = service.export_invoice_logs_csv(
                date_from=date_from,
                date_to=date_to,
                invoice_number=invoice_number,
                status=status,
                environment=environment
            )
        elif format == "json":
            content_type = "application/json; charset=utf-8"
            export_generator = service.export_invoice_logs_json(
                date_from=date_from,
                date_to=date_to,
                invoice_number=invoice_number,
                status=status,
                environment=environment
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {format}. Supported formats: csv, json"
            )
        
        # Create streaming response
        return StreamingResponse(
            export_generator,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invoice log export error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during invoice log export"
        )

