"""
Invoice history Pydantic schemas.

Defines request/response schemas for invoice history and retrieval.
Handles pagination, filtering, and invoice status queries.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.invoice_log import InvoiceLogStatus
from app.core.constants import Environment, InvoiceMode


class InvoiceListItem(BaseModel):
    """Schema for invoice list item."""
    id: int
    invoice_number: str
    uuid: Optional[str] = None
    hash: Optional[str] = None
    environment: str
    status: InvoiceLogStatus
    zatca_response_code: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    """Schema for invoice list response with pagination."""
    invoices: list[InvoiceListItem]
    total: int
    page: int
    limit: int
    total_pages: int


class InvoiceDetailResponse(BaseModel):
    """Schema for invoice detail response."""
    id: int
    invoice_number: str
    uuid: Optional[str] = None
    hash: Optional[str] = None
    environment: str
    status: InvoiceLogStatus
    zatca_response_code: Optional[str] = None
    created_at: datetime
    
    # Additional metadata (if available from other sources)
    phase: Optional[InvoiceMode] = None  # Inferred from environment/status
    
    # Phase 8: Observability fields (optional)
    request_payload: Optional[dict] = None
    generated_xml: Optional[str] = None
    zatca_response: Optional[dict] = None
    submitted_at: Optional[datetime] = None
    cleared_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class InvoiceStatusResponse(BaseModel):
    """Schema for invoice status response."""
    invoice_number: str
    status: InvoiceLogStatus
    zatca_response_code: Optional[str] = None
    uuid: Optional[str] = None
    hash: Optional[str] = None
    environment: str
    created_at: datetime
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class InvoiceListFilters(BaseModel):
    """Schema for invoice list filters."""
    invoice_number: Optional[str] = Field(None, description="Filter by invoice number")
    status: Optional[InvoiceLogStatus] = Field(None, description="Filter by status")
    environment: Optional[Environment] = Field(None, description="Filter by environment")
    date_from: Optional[datetime] = Field(None, description="Filter by start date")
    date_to: Optional[datetime] = Field(None, description="Filter by end date")

