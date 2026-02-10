"""
Invoice history service for tenant-scoped invoice retrieval.

Provides query operations for invoice history with strict tenant isolation.
All operations are automatically scoped to the requesting tenant.
"""

import logging
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.invoice_log import InvoiceLog, InvoiceLogStatus
from app.schemas.auth import TenantContext
from app.core.constants import Environment, InvoiceMode

logger = logging.getLogger(__name__)


class InvoiceHistoryService:
    """
    Service for querying tenant-scoped invoice history.
    
    CRITICAL: All operations enforce tenant isolation.
    No cross-tenant access is possible.
    """
    
    def __init__(self, db: Session, tenant_context: TenantContext):
        """
        Initializes invoice history service.
        
        Args:
            db: Database session
            tenant_context: Tenant context from request (enforces isolation)
        """
        self.db = db
        self.tenant_context = tenant_context
    
    def list_invoices(
        self,
        page: int = 1,
        limit: int = 50,
        invoice_number: Optional[str] = None,
        status: Optional[InvoiceLogStatus] = None,
        environment: Optional[Environment] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Tuple[List[InvoiceLog], int]:
        """
        Lists invoices with pagination and filtering.
        
        CRITICAL: All queries are automatically filtered by tenant_id.
        No cross-tenant access is possible.
        
        Args:
            page: Page number (1-indexed)
            limit: Number of items per page (max 100)
            invoice_number: Optional filter by invoice number (partial match)
            status: Optional filter by status
            environment: Optional filter by environment
            date_from: Optional filter by start date
            date_to: Optional filter by end date
            
        Returns:
            Tuple of (list of InvoiceLog instances, total count)
        """
        # Enforce max limit
        limit = min(limit, 100)
        offset = (page - 1) * limit
        
        # Build base query with tenant isolation
        query = self.db.query(InvoiceLog).filter(
            InvoiceLog.tenant_id == self.tenant_context.tenant_id  # CRITICAL: Tenant isolation
        )
        
        # Apply filters
        if invoice_number:
            query = query.filter(InvoiceLog.invoice_number.contains(invoice_number))
        
        if status:
            query = query.filter(InvoiceLog.status == status)
        
        if environment:
            query = query.filter(InvoiceLog.environment == environment.value)
        
        if date_from:
            query = query.filter(InvoiceLog.created_at >= date_from)
        
        if date_to:
            query = query.filter(InvoiceLog.created_at <= date_to)
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination and ordering
        query = query.order_by(InvoiceLog.created_at.desc())
        query = query.offset(offset).limit(limit)
        
        invoices = query.all()
        
        logger.debug(
            f"Listed invoices: tenant_id={self.tenant_context.tenant_id}, "
            f"page={page}, limit={limit}, total={total}, returned={len(invoices)}"
        )
        
        return invoices, total
    
    def get_invoice_by_id(self, invoice_id: int) -> Optional[InvoiceLog]:
        """
        Gets an invoice by ID.
        
        CRITICAL: Automatically scoped to current tenant.
        
        Args:
            invoice_id: Invoice log ID
            
        Returns:
            InvoiceLog or None if not found or belongs to different tenant
        """
        invoice = self.db.query(InvoiceLog).filter(
            InvoiceLog.id == invoice_id,
            InvoiceLog.tenant_id == self.tenant_context.tenant_id  # CRITICAL: Tenant isolation
        ).first()
        
        if not invoice:
            logger.debug(
                f"Invoice not found: id={invoice_id}, tenant_id={self.tenant_context.tenant_id}"
            )
        
        return invoice
    
    def get_invoice_by_number(self, invoice_number: str) -> Optional[InvoiceLog]:
        """
        Gets the most recent invoice log entry by invoice number.
        
        CRITICAL: Automatically scoped to current tenant.
        
        Args:
            invoice_number: Invoice number to query
            
        Returns:
            Most recent InvoiceLog or None
        """
        invoice = self.db.query(InvoiceLog).filter(
            InvoiceLog.tenant_id == self.tenant_context.tenant_id,
            InvoiceLog.invoice_number == invoice_number
        ).order_by(InvoiceLog.created_at.desc()).first()
        
        return invoice
    
    def get_invoice_status(self, invoice_number: str) -> Optional[InvoiceLog]:
        """
        Gets the current status of an invoice.
        
        CRITICAL: Automatically scoped to current tenant.
        
        Args:
            invoice_number: Invoice number to query
            
        Returns:
            Most recent InvoiceLog with status information or None
        """
        return self.get_invoice_by_number(invoice_number)
    
    def _infer_phase(self, invoice: InvoiceLog) -> Optional[InvoiceMode]:
        """
        Infers invoice phase from log data.
        
        Phase-2 invoices have UUID and hash, Phase-1 typically don't.
        This is a heuristic and may not be 100% accurate.
        
        Args:
            invoice: InvoiceLog instance
            
        Returns:
            Inferred InvoiceMode or None
        """
        if invoice.uuid and invoice.hash:
            return InvoiceMode.PHASE_2
        # Phase-1 invoices typically don't have UUID/hash in logs
        # We can't definitively determine Phase-1 without more context
        return None

