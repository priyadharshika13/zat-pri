"""
Tenant Pydantic schemas.

Defines request/response schemas for tenant management.
Handles validation of tenant data according to business rules.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.core.constants import Environment


class TenantBase(BaseModel):
    """Base tenant schema with common fields."""
    company_name: str = Field(..., min_length=1, max_length=200, description="Company legal name")
    vat_number: str = Field(..., min_length=15, max_length=15, description="VAT registration number (15 digits)")
    environment: Environment = Field(..., description="ZATCA environment (SANDBOX or PRODUCTION)")
    is_active: bool = Field(default=True, description="Whether tenant is active")


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""
    pass


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""
    company_name: Optional[str] = Field(None, min_length=1, max_length=200)
    environment: Optional[Environment] = None
    is_active: Optional[bool] = None


class TenantResponse(TenantBase):
    """Schema for tenant response."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class TenantContext(BaseModel):
    """
    Tenant context resolved from API key.
    
    This is attached to request.state.tenant for easy access across services.
    """
    tenant_id: int
    company_name: str
    vat_number: str
    environment: Environment
    
    class Config:
        from_attributes = True

