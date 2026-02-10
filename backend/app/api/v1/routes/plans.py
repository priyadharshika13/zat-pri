"""
Subscription plans API endpoint.

Provides subscription plan information and management.
Handles plan listing, details retrieval, and current subscription status.
Does not contain billing logic or payment processing.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy.orm import Session

from app.core.security import verify_api_key_and_resolve_tenant
from app.schemas.auth import TenantContext
from app.schemas.subscription import PlanResponse, SubscriptionResponse, UsageCounterResponse
from app.services.subscription_service import SubscriptionService
from app.db.session import get_db
from app.models.subscription import Plan

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[PlanResponse])
async def list_plans(
    db: Annotated[Session, Depends(get_db)]
) -> list[PlanResponse]:
    """
    Returns all available subscription plans.
    
    Includes plan limits, features, and trial eligibility.
    """
    plans = db.query(Plan).filter(Plan.is_active == True).all()
    return [PlanResponse.model_validate(plan) for plan in plans]


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> SubscriptionResponse:
    """
    Returns current tenant's subscription information.
    
    Includes:
    - Plan details and limits
    - Trial status and remaining days
    - Custom limits (if Enterprise)
    """
    subscription_service = SubscriptionService(db, tenant)
    subscription = subscription_service.get_current_subscription()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found. Trial plan may not be available."
        )
    
    trial_days = subscription_service.get_trial_days_remaining(subscription)
    
    return SubscriptionResponse(
        id=subscription.id,
        tenant_id=subscription.tenant_id,
        plan_id=subscription.plan_id,
        plan_name=subscription.plan.name,
        status=subscription.status,
        trial_starts_at=subscription.trial_starts_at,
        trial_ends_at=subscription.trial_ends_at,
        trial_days_remaining=trial_days,
        custom_limits=subscription.custom_limits,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at
    )


@router.get("/usage", response_model=UsageCounterResponse)
async def get_usage_summary(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> UsageCounterResponse:
    """
    Returns current usage summary for tenant.
    
    Includes:
    - Current billing period
    - Invoice count vs limit
    - AI request count vs limit
    - Remaining limits
    """
    subscription_service = SubscriptionService(db, tenant)
    usage_summary = subscription_service.get_usage_summary()
    
    if not usage_summary.get("has_subscription"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    return UsageCounterResponse(
        tenant_id=tenant.tenant_id,
        billing_period=usage_summary["billing_period"],
        invoice_count=usage_summary["invoice_count"],
        invoice_limit=usage_summary["invoice_limit"],
        ai_request_count=usage_summary["ai_request_count"],
        ai_limit=usage_summary["ai_limit"],
        invoice_limit_exceeded=usage_summary.get("invoice_remaining", 0) == 0 and usage_summary["invoice_limit"] > 0,
        ai_limit_exceeded=usage_summary.get("ai_remaining", 0) == 0 and usage_summary["ai_limit"] > 0
    )

