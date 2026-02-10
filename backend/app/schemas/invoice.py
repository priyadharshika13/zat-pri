"""
Invoice request and response schemas.

Defines the structure for invoice submission and processing results.
Handles validation of invoice data according to ZATCA requirements.
Does not perform business logic or external API calls.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.core.constants import InvoiceMode, Environment, TaxCategory


class LineItem(BaseModel):
    """Invoice line item."""
    name: str = Field(..., description="Item name")
    quantity: float = Field(..., gt=0, description="Item quantity")
    unit_price: float = Field(..., ge=0, description="Unit price")
    tax_rate: float = Field(..., ge=0, le=100, description="Tax rate percentage")
    tax_category: TaxCategory = Field(..., description="Tax category")
    discount: Optional[float] = Field(None, ge=0, description="Discount amount")
    
    @property
    def taxable_amount(self) -> float:
        """
        Canonical line taxable amount (ZATCA Phase-2):
        taxable = (qty × unit_price) − discount
        """
        gross = self.quantity * self.unit_price
        discount_amount = self.discount or 0.0
        return gross - discount_amount
    
    @property
    def subtotal(self) -> float:
        """
        Backward-compatible alias for taxable amount.
        
        NOTE: Historically used as 'subtotal', but for Phase-2 compliance we treat
        subtotal == taxable_amount to prevent TaxExclusiveAmount drift.
        """
        return self.taxable_amount
    
    @property
    def tax_amount(self) -> float:
        """Calculates tax amount for the line item."""
        return self.taxable_amount * (self.tax_rate / 100.0)
    
    @property
    def total(self) -> float:
        """Calculates total including tax."""
        return self.taxable_amount + self.tax_amount


class InvoiceRequest(BaseModel):
    """Invoice processing request."""
    
    mode: InvoiceMode = Field(..., description="Processing mode (PHASE_1 or PHASE_2)")
    environment: Environment = Field(..., description="Target environment")
    
    # Invoice metadata
    invoice_number: str = Field(..., min_length=1, max_length=50, description="Unique invoice number")
    invoice_date: datetime = Field(..., description="Invoice date and time")
    invoice_type: str = Field(default="388", description="Invoice type code")
    
    # Seller information
    seller_name: str = Field(..., min_length=1, max_length=100, description="Seller legal name")
    seller_tax_number: str = Field(..., min_length=15, max_length=15, description="Seller VAT registration number")
    seller_address: Optional[str] = Field(None, max_length=200, description="Seller address")
    
    # Buyer information
    buyer_name: Optional[str] = Field(None, max_length=100, description="Buyer name")
    buyer_tax_number: Optional[str] = Field(None, min_length=15, max_length=15, description="Buyer VAT number")
    
    # Invoice items
    line_items: list[LineItem] = Field(..., min_length=1, description="Invoice line items")
    
    # Totals
    total_discount: Optional[float] = Field(None, ge=0, description="Total discount amount")
    total_tax_exclusive: float = Field(..., ge=0, description="Total amount excluding tax")
    total_tax_amount: float = Field(..., ge=0, description="Total tax amount")
    total_amount: float = Field(..., ge=0, description="Total amount including tax")
    
    # Phase-2 specific
    uuid: Optional[str] = Field(None, description="Invoice UUID for Phase-2")
    previous_invoice_hash: Optional[str] = Field(None, description="Previous invoice hash for Phase-2")
    
    # Phase 9: Production confirmation guard
    confirm_production: Optional[bool] = Field(None, description="Explicit confirmation required for Production submissions")
    
    @field_validator("invoice_date")
    @classmethod
    def validate_invoice_date(cls, v: datetime) -> datetime:
        """Validates invoice date is not in the future."""
        if v > datetime.now():
            raise ValueError("Invoice date cannot be in the future")
        return v
    
    @field_validator("line_items")
    @classmethod
    def validate_line_items(cls, v: list[LineItem]) -> list[LineItem]:
        """Validates at least one line item exists."""
        if not v:
            raise ValueError("At least one line item is required")
        return v
    
    def model_post_init(self, __context) -> None:
        """
        Post-initialization validation for Phase-2 mandatory fields.
        
        CRITICAL: When mode=PHASE_2, the following are MANDATORY:
        - seller_tax_number, invoice_type, uuid.
        - previous_invoice_hash: OPTIONAL for the first invoice in the chain;
          required for all subsequent invoices (omit or empty = first invoice).
        """
        if self.mode == InvoiceMode.PHASE_2:
            missing_fields = []
            
            if not self.seller_tax_number:
                missing_fields.append("seller_tax_number")
            
            if not self.invoice_type:
                missing_fields.append("invoice_type")
            
            if not self.uuid:
                missing_fields.append("uuid")
            
            # previous_invoice_hash is optional (first invoice has none)
            
            if missing_fields:
                raise ValueError(
                    f"Phase-2 invoices require the following mandatory fields: {', '.join(missing_fields)}. "
                    f"Please provide all required fields for Phase-2 compliance."
                )


class InvoiceResponse(BaseModel):
    """Invoice processing response."""
    
    success: bool = Field(..., description="Processing success status")
    invoice_number: str = Field(..., description="Invoice number")
    mode: InvoiceMode = Field(..., description="Processing mode used")
    environment: Environment = Field(..., description="Environment used")
    
    # Phase-1 response
    qr_code_data: Optional["QRCodeData"] = Field(None, description="QR code data for Phase-1")
    
    # Phase-2 response
    xml_data: Optional["XMLData"] = Field(None, description="XML data for Phase-2")
    clearance: Optional["ClearanceResponse"] = Field(None, description="Clearance response for Phase-2")
    
    # Reporting (automatic after clearance)
    reporting: Optional[dict] = Field(None, description="Reporting result if automatically reported after clearance")
    
    # Metadata
    processed_at: datetime = Field(default_factory=datetime.now, description="Processing timestamp")
    errors: Optional[list[str]] = Field(None, description="Processing errors if any")
    validation_result: Optional["ValidationResponse"] = Field(None, description="Validation result if validation failed")


# Forward references to avoid circular imports
from app.schemas.phase1 import QRCodeData
from app.schemas.phase2 import XMLData, ClearanceResponse
from app.schemas.validation import ValidationResponse

InvoiceResponse.model_rebuild()
