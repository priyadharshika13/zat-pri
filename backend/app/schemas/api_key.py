"""
API Key Pydantic schemas.

Defines request/response schemas for API key management.
Handles validation of API key data.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ApiKeyBase(BaseModel):
    """Base API key schema with common fields."""
    is_active: bool = Field(default=True, description="Whether API key is active")


class ApiKeyCreate(BaseModel):
    """Schema for creating a new API key."""
    # API key will be generated if not provided
    api_key: Optional[str] = Field(None, min_length=10, max_length=255, description="API key (auto-generated if not provided)")
    is_active: bool = Field(default=True, description="Whether API key is active")


class ApiKeyUpdate(BaseModel):
    """Schema for updating an API key."""
    is_active: Optional[bool] = None


class ApiKeyResponse(BaseModel):
    """Schema for API key response."""
    id: int
    api_key: str
    tenant_id: int
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ApiKeyResponseWithTenant(ApiKeyResponse):
    """API key response with tenant information."""
    tenant: "TenantResponse"  # Forward reference
    
    class Config:
        from_attributes = True

