"""
Authentication schemas.

Defines request/response schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str = Field(..., description="Access token (API key)")
    token_type: str = Field(default="bearer", description="Token type")
    tenant_id: int = Field(..., description="Tenant ID")
    company_name: str = Field(..., description="Company name")
    email: Optional[str] = Field(None, description="User email")


class TenantContext(BaseModel):
    """Tenant context schema."""
    tenant_id: int
    company_name: str
    vat_number: str
    environment: str
