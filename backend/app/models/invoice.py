"""
Invoice master entity database model.

Defines the invoice master entity for tenant-scoped invoice persistence.
Each invoice is tied to a specific tenant and cannot be accessed by other tenants.
This is the source of truth for invoice data, while InvoiceLog tracks processing events.
"""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum as SQLEnum, Text, JSON, Float, UniqueConstraint, Index
from datetime import datetime
from typing import Optional
import enum

from app.db.models import Base
from app.core.constants import InvoiceMode, Environment


class InvoiceStatus(str, enum.Enum):
    """Invoice status values."""
    CREATED = "CREATED"
    PROCESSING = "PROCESSING"
    CLEARED = "CLEARED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class Invoice(Base):
    """
    Invoice master entity database model.
    
    This is the source of truth for invoice data. It persists invoice information
    BEFORE ZATCA processing begins, ensuring we have a record even if processing fails.
    
    CRITICAL: All invoices are tenant-scoped with strict isolation.
    Each invoice belongs to exactly one tenant.
    
    Idempotency: The combination of (tenant_id, invoice_number) must be unique.
    """
    
    __tablename__ = "invoices"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Tenant isolation (CRITICAL)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Invoice identification
    invoice_number = Column(String(50), nullable=False, index=True)
    
    # ZATCA compliance fields
    phase = Column(SQLEnum(InvoiceMode), nullable=False, comment="ZATCA phase (PHASE_1 or PHASE_2)")
    status = Column(SQLEnum(InvoiceStatus), nullable=False, default=InvoiceStatus.CREATED, index=True)
    environment = Column(SQLEnum(Environment), nullable=False, index=True)
    
    # Financial totals
    total_amount = Column(Float, nullable=False, comment="Total amount including tax")
    tax_amount = Column(Float, nullable=False, comment="Total tax amount")
    
    # ZATCA Phase-2 fields (nullable for Phase-1)
    hash = Column(String(64), nullable=True, index=True, comment="XML hash value")
    uuid = Column(String(100), nullable=True, index=True, comment="Invoice UUID from ZATCA")
    
    # XML content (nullable for Phase-1)
    xml_content = Column(Text, nullable=True, comment="Generated XML content (for Phase-2)")
    
    # ZATCA response (full JSON response from ZATCA API)
    zatca_response = Column(JSON, nullable=True, comment="Full ZATCA API response (JSON)")
    
    # Error tracking
    error_message = Column(Text, nullable=True, comment="Error message if processing failed")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Unique constraint for idempotency (tenant_id + invoice_number)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'invoice_number', name='uq_invoices_tenant_invoice_number'),
        Index('ix_invoices_tenant_status', 'tenant_id', 'status'),
        Index('ix_invoices_tenant_created', 'tenant_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Invoice(id={self.id}, tenant_id={self.tenant_id}, invoice_number='{self.invoice_number}', status='{self.status}', phase='{self.phase}')>"

