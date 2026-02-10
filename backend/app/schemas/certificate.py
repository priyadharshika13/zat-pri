"""
Certificate Pydantic schemas.

Defines request/response schemas for certificate management.
Handles validation of certificate data and file uploads.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.core.constants import Environment
from app.models.certificate import CertificateStatus


class CertificateUploadRequest(BaseModel):
    """Schema for certificate upload request."""
    environment: Environment = Field(..., description="Target environment (SANDBOX or PRODUCTION)")
    # Note: certificate and private_key files are handled via multipart/form-data in the route


class CertificateResponse(BaseModel):
    """Schema for certificate response."""
    id: int
    tenant_id: int
    environment: str
    certificate_serial: Optional[str] = None
    issuer: Optional[str] = None
    expiry_date: Optional[datetime] = None
    status: CertificateStatus
    is_active: bool
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CertificateListResponse(BaseModel):
    """Schema for certificate list response with metadata."""
    certificates: list[CertificateResponse]
    total: int
    active_count: int
    expired_count: int

