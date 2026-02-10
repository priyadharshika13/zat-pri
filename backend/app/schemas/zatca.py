"""
ZATCA-specific schemas.

Defines schemas for ZATCA API requests and responses.
Handles clearance and reporting data structures.
Does not contain invoice business logic or validation rules.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ClearanceRequest(BaseModel):
    """ZATCA clearance request."""
    signed_xml: str = Field(..., description="Signed XML invoice")
    invoice_uuid: str = Field(..., description="Invoice UUID")


class ClearanceResponse(BaseModel):
    """ZATCA clearance response."""
    status: str = Field(..., description="Clearance status")
    uuid: str = Field(..., description="Clearance UUID")
    qr_code: str = Field(..., description="QR code")
    reporting_status: Optional[str] = Field(None, description="Reporting status")


class ReportingRequest(BaseModel):
    """ZATCA reporting request."""
    invoice_uuid: str = Field(..., description="Invoice UUID to report")


class ReportingResponse(BaseModel):
    """ZATCA reporting response."""
    status: str = Field(..., description="Reporting status")
    message: str = Field(..., description="Status message")

