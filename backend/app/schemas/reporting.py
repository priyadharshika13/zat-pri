"""
Reporting API schemas.

Defines request/response schemas for invoice and VAT reporting endpoints.
All reports are tenant-scoped and read-only.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.invoice import InvoiceStatus
from app.core.constants import InvoiceMode, Environment


class InvoiceReportItem(BaseModel):
    """Schema for invoice report item."""
    invoice_number: str
    status: InvoiceStatus
    phase: InvoiceMode
    total_amount: float
    tax_amount: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class InvoiceReportResponse(BaseModel):
    """Schema for invoice report response with pagination."""
    invoices: list[InvoiceReportItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class VATSummaryItem(BaseModel):
    """Schema for VAT summary item (daily or monthly)."""
    date: str  # ISO format date string (YYYY-MM-DD or YYYY-MM)
    total_tax_amount: float
    total_invoice_amount: float
    invoice_count: int


class VATSummaryResponse(BaseModel):
    """Schema for VAT summary response."""
    summary: list[VATSummaryItem]
    total_tax_amount: float
    total_invoice_amount: float
    total_invoice_count: int
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    group_by: str  # "day" or "month"


class StatusBreakdownItem(BaseModel):
    """Schema for status breakdown item."""
    status: InvoiceStatus
    count: int


class StatusBreakdownResponse(BaseModel):
    """Schema for status breakdown response."""
    breakdown: list[StatusBreakdownItem]
    total_invoices: int


class RevenueSummaryResponse(BaseModel):
    """Schema for revenue summary response."""
    total_revenue: float
    total_tax: float
    net_revenue: float
    cleared_invoice_count: int
    total_invoice_count: int

