"""
Invoice log database model.

Defines the invoice log entity for tenant-scoped invoice tracking.
Each log entry is tied to a specific tenant and cannot be accessed by other tenants.
"""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum as SQLEnum, Text, JSON
from datetime import datetime
from typing import Optional
import enum

from app.db.models import Base


class InvoiceLogStatus(str, enum.Enum):
    """Invoice log status values."""
    SUBMITTED = "SUBMITTED"
    CLEARED = "CLEARED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class InvoiceLog(Base):
    """
    Invoice log database model.
    
    Tracks invoice processing events with tenant isolation.
    Each log entry belongs to exactly one tenant.
    """
    
    __tablename__ = "invoice_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    invoice_number = Column(String(50), nullable=False, index=True)
    uuid = Column(String(100), nullable=True)
    hash = Column(String(64), nullable=True)
    environment = Column(String(20), nullable=False)
    status = Column(SQLEnum(InvoiceLogStatus), nullable=False, index=True)
    zatca_response_code = Column(Text, nullable=True, comment="ZATCA response code or error message (TEXT for long messages)")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Phase 8: Invoice observability fields
    request_payload = Column(JSON, nullable=True, comment="Original invoice request payload (JSON)")
    generated_xml = Column(Text, nullable=True, comment="Generated XML content (for Phase-2)")
    zatca_response = Column(JSON, nullable=True, comment="Full ZATCA API response (JSON)")
    submitted_at = Column(DateTime, nullable=True, comment="Timestamp when invoice was submitted to ZATCA")
    cleared_at = Column(DateTime, nullable=True, comment="Timestamp when invoice was cleared by ZATCA")
    
    # Retry tracking
    action = Column(String(20), nullable=True, comment="Action type (e.g., 'RETRY', 'SUBMIT')")
    previous_status = Column(String(20), nullable=True, comment="Previous invoice status before action")
    
    def __repr__(self):
        return f"<InvoiceLog(id={self.id}, tenant_id={self.tenant_id}, invoice_number='{self.invoice_number}', status='{self.status}')>"

