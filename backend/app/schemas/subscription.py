"""
Subscription Pydantic schemas.

Defines request/response schemas for subscription management.
Handles plan limits, trial status, and usage tracking.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.models.subscription import SubscriptionStatus


class PlanBase(BaseModel):
    """Base plan schema."""
    name: str = Field(..., min_length=1, max_length=50)
    monthly_invoice_limit: int = Field(..., ge=0, description="0 = unlimited")
    monthly_ai_limit: int = Field(..., ge=0, description="0 = unlimited")
    rate_limit_per_minute: int = Field(..., ge=1)
    features: Optional[Dict[str, Any]] = Field(None, description="JSON object with feature flags")


class PlanCreate(PlanBase):
    """Schema for creating a plan."""
    pass


class PlanResponse(PlanBase):
    """Schema for plan response."""
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    """Schema for subscription response."""
    id: int
    tenant_id: int
    plan_id: int
    plan_name: str
    status: SubscriptionStatus
    trial_starts_at: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    trial_days_remaining: Optional[int] = None
    custom_limits: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UsageCounterResponse(BaseModel):
    """Schema for usage counter response."""
    tenant_id: int
    billing_period: str
    invoice_count: int
    invoice_limit: int
    ai_request_count: int
    ai_limit: int
    invoice_limit_exceeded: bool
    ai_limit_exceeded: bool
    
    class Config:
        from_attributes = True


class LimitExceededError(BaseModel):
    """Structured error response for limit exceeded."""
    error_code: str = "LIMIT_EXCEEDED"
    limit_type: str = Field(..., description="AI_USAGE | INVOICE_COUNT | RATE_LIMIT | TRIAL_EXPIRED")
    message: str
    upgrade_required: bool = True
    current_usage: Optional[int] = None
    limit: Optional[int] = None
    plan_name: Optional[str] = None

