"""
Internal operations endpoints for admin/ops visibility.

CRITICAL: These endpoints are INTERNAL-ONLY and must be protected with INTERNAL_SECRET_KEY.
Not exposed to customers or public API.
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.config import get_settings
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.subscription import Subscription, Plan
from app.models.invoice_log import InvoiceLog, InvoiceLogStatus
from app.models.api_key import ApiKey
from app.core.constants import InvoiceMode
from app.services.retention_service import RetentionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


def verify_internal_secret(
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret")
) -> None:
    """
    Verifies internal secret key for admin endpoints.
    
    CRITICAL: These endpoints must never be exposed to customers.
    """
    settings = get_settings()
    internal_secret = getattr(settings, 'internal_secret_key', None)
    
    if not internal_secret:
        logger.error("INTERNAL_SECRET_KEY not configured - internal endpoints disabled")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal endpoints not configured"
        )
    
    if not x_internal_secret or x_internal_secret != internal_secret:
        logger.warning(f"Invalid internal secret key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal secret"
        )


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Get platform metrics (internal only)"
)
async def get_metrics(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(verify_internal_secret)]
) -> dict:
    """
    Returns platform-wide metrics for operations monitoring.
    
    CRITICAL: Internal-only endpoint. Requires INTERNAL_SECRET_KEY.
    
    Returns:
        - Total tenants
        - Total invoices (today, month)
        - Phase-1 vs Phase-2 counts
        - AI requests (today, month)
        - ZATCA failures count
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Total tenants
    total_tenants = db.query(func.count(Tenant.id)).scalar() or 0
    
    # Invoices today
    invoices_today = db.query(func.count(InvoiceLog.id)).filter(
        InvoiceLog.created_at >= today_start
    ).scalar() or 0
    
    # Invoices this month
    invoices_month = db.query(func.count(InvoiceLog.id)).filter(
        InvoiceLog.created_at >= month_start
    ).scalar() or 0
    
    # Phase-1 vs Phase-2 (inferred from UUID presence)
    phase1_count = db.query(func.count(InvoiceLog.id)).filter(
        InvoiceLog.uuid.is_(None)
    ).scalar() or 0
    
    phase2_count = db.query(func.count(InvoiceLog.id)).filter(
        InvoiceLog.uuid.isnot(None)
    ).scalar() or 0
    
    # ZATCA failures (REJECTED + ERROR status)
    zatca_failures = db.query(func.count(InvoiceLog.id)).filter(
        InvoiceLog.status.in_([InvoiceLogStatus.REJECTED, InvoiceLogStatus.ERROR])
    ).scalar() or 0
    
    # AI requests (approximated from usage counters - this is a placeholder)
    # In a real implementation, you'd track AI usage separately
    ai_requests_today = 0  # TODO: Implement AI usage tracking
    ai_requests_month = 0  # TODO: Implement AI usage tracking
    
    return {
        "timestamp": now.isoformat(),
        "tenants": {
            "total": total_tenants
        },
        "invoices": {
            "today": invoices_today,
            "this_month": invoices_month,
            "phase1": phase1_count,
            "phase2": phase2_count,
            "total": invoices_today + invoices_month  # Approximate
        },
        "ai_requests": {
            "today": ai_requests_today,
            "this_month": ai_requests_month
        },
        "zatca_failures": zatca_failures
    }


@router.get(
    "/tenants/summary",
    status_code=status.HTTP_200_OK,
    summary="Get tenant summary (internal only)"
)
async def get_tenants_summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(verify_internal_secret)],
    limit: int = 100
) -> dict:
    """
    Returns summary of all tenants for operations visibility.
    
    CRITICAL: Internal-only endpoint. Requires INTERNAL_SECRET_KEY.
    
    Returns:
        List of tenants with:
        - Tenant ID
        - Plan name
        - Subscription status
        - Invoice volume
        - AI usage (if tracked)
    """
    tenants = db.query(Tenant).limit(limit).all()
    
    summaries = []
    for tenant in tenants:
        # Get subscription
        subscription = db.query(Subscription).filter(
            Subscription.tenant_id == tenant.id
        ).first()
        
        plan_name = subscription.plan.name if subscription and subscription.plan else "No Plan"
        subscription_status = subscription.status.value if subscription else "none"
        
        # Get invoice count
        invoice_count = db.query(func.count(InvoiceLog.id)).filter(
            InvoiceLog.tenant_id == tenant.id
        ).scalar() or 0
        
        # Get active API keys
        active_keys = db.query(func.count(ApiKey.id)).filter(
            and_(
                ApiKey.tenant_id == tenant.id,
                ApiKey.is_active == True
            )
        ).scalar() or 0
        
        summaries.append({
            "tenant_id": tenant.id,
            "plan_name": plan_name,
            "subscription_status": subscription_status,
            "invoice_count": invoice_count,
            "active_api_keys": active_keys,
            "environment": tenant.environment.value if tenant.environment else "SANDBOX"
        })
    
    return {
        "total": len(summaries),
        "tenants": summaries
    }


@router.post(
    "/retention/cleanup",
    status_code=status.HTTP_200_OK,
    summary="Run retention cleanup (internal only)"
)
async def run_retention_cleanup(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[None, Depends(verify_internal_secret)],
    dry_run: bool = False,
    retention_days: Optional[int] = None
) -> dict:
    """
    Runs retention cleanup to remove or anonymize old invoice artifacts.
    
    CRITICAL: Internal-only endpoint. Requires INTERNAL_SECRET_KEY.
    
    Args:
        dry_run: If True, only reports what would be cleaned
        retention_days: Override retention period (defaults to configured value)
        
    Returns:
        Cleanup statistics
    """
    retention_service = RetentionService(db)
    stats = retention_service.cleanup_old_artifacts(
        retention_days=retention_days,
        dry_run=dry_run
    )
    
    return stats
