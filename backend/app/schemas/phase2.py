"""
Phase-2 invoice schemas.

Defines request and response schemas specific to Phase-2 processing.
Handles XML data structures, clearance responses, and Phase-2 validation.
Does not contain Phase-1 schemas or business logic.
"""

from typing import Optional
from pydantic import BaseModel, Field


class XMLData(BaseModel):
    """XML invoice data structure for Phase-2."""
    xml_content: str = Field(..., description="XML invoice content")
    xml_hash: str = Field(..., description="SHA-256 hash of XML content")
    signed_xml: Optional[str] = Field(None, description="Signed XML content")
    digital_signature: Optional[str] = Field(None, description="Digital signature value")


class ClearanceResponse(BaseModel):
    """ZATCA clearance response for Phase-2."""
    clearance_status: str = Field(..., description="Clearance status")
    clearance_uuid: str = Field(..., description="Clearance UUID")
    qr_code: str = Field(..., description="QR code from clearance")
    reporting_status: Optional[str] = Field(None, description="Reporting status")

