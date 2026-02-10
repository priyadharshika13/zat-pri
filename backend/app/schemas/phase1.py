"""
Phase-1 invoice schemas.

Defines request and response schemas specific to Phase-1 processing.
Handles QR code data structures and Phase-1 validation.
Does not contain Phase-2 schemas or business logic.
"""

from pydantic import BaseModel, Field


class QRCodeData(BaseModel):
    """QR code data structure for Phase-1."""
    seller_name: str = Field(..., description="Seller legal name")
    seller_tax_number: str = Field(..., description="Seller VAT registration number")
    invoice_date: str = Field(..., description="Invoice date in ISO format")
    invoice_total: str = Field(..., description="Total invoice amount")
    invoice_tax_amount: str = Field(..., description="Total tax amount")
    qr_code_base64: str = Field(default="", description="Base64-encoded QR code image (optional - may be empty if QR generation fails)")

