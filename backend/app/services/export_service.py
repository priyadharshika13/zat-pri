"""
Export service for invoices and invoice logs.

Provides data export functionality with tenant isolation and streaming support.
Supports CSV, JSON, and XML formats with efficient chunked processing.
"""

import logging
import csv
import json
from datetime import datetime
from typing import Optional, Iterator, Dict, Any, List
from io import StringIO, BytesIO
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_log import InvoiceLog, InvoiceLogStatus
from app.schemas.auth import TenantContext
from app.core.constants import InvoiceMode, Environment

logger = logging.getLogger(__name__)


class ExportService:
    """
    Service for exporting invoices and invoice logs.
    
    CRITICAL: All operations enforce tenant isolation.
    No cross-tenant data access is possible.
    
    Features:
    - Streaming support for large datasets
    - Multiple export formats (CSV, JSON, XML)
    - Efficient chunked database queries
    - Tenant-scoped filtering
    """
    
    # Chunk size for database queries (prevents memory issues)
    CHUNK_SIZE = 1000
    
    def __init__(self, db: Session, tenant_context: TenantContext):
        """
        Initializes export service.
        
        Args:
            db: Database session
            tenant_context: Tenant context from request (enforces isolation)
        """
        self.db = db
        self.tenant_context = tenant_context
    
    def export_invoices_csv(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        invoice_number: Optional[str] = None,
        status: Optional[InvoiceStatus] = None,
        phase: Optional[InvoiceMode] = None,
        environment: Optional[Environment] = None
    ) -> Iterator[str]:
        """
        Exports invoices to CSV format with streaming support.
        
        CRITICAL: Only exports invoices belonging to the authenticated tenant.
        
        Args:
            date_from: Filter by start date
            date_to: Filter by end date
            invoice_number: Filter by invoice number (partial match)
            status: Filter by invoice status
            phase: Filter by invoice phase
            environment: Filter by environment
            
        Yields:
            CSV lines (including header)
        """
        # Build query with tenant isolation
        query = self._build_invoice_query(
            date_from=date_from,
            date_to=date_to,
            invoice_number=invoice_number,
            status=status,
            phase=phase,
            environment=environment
        )
        
        # CSV header
        header = [
            'id', 'invoice_number', 'phase', 'status', 'environment',
            'total_amount', 'tax_amount', 'hash', 'uuid',
            'error_message', 'created_at', 'updated_at'
        ]
        yield ','.join(header) + '\n'
        
        # Stream results in chunks
        offset = 0
        while True:
            chunk = query.offset(offset).limit(self.CHUNK_SIZE).all()
            if not chunk:
                break
            
            for invoice in chunk:
                row = [
                    str(invoice.id),
                    self._escape_csv_field(invoice.invoice_number),
                    invoice.phase.value if invoice.phase else '',
                    invoice.status.value if invoice.status else '',
                    invoice.environment.value if invoice.environment else '',
                    str(invoice.total_amount),
                    str(invoice.tax_amount),
                    self._escape_csv_field(invoice.hash or ''),
                    self._escape_csv_field(invoice.uuid or ''),
                    self._escape_csv_field(invoice.error_message or ''),
                    invoice.created_at.isoformat() if invoice.created_at else '',
                    invoice.updated_at.isoformat() if invoice.updated_at else ''
                ]
                yield ','.join(row) + '\n'
            
            offset += self.CHUNK_SIZE
            
            # If we got fewer than CHUNK_SIZE, we're done
            if len(chunk) < self.CHUNK_SIZE:
                break
    
    def export_invoices_json(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        invoice_number: Optional[str] = None,
        status: Optional[InvoiceStatus] = None,
        phase: Optional[InvoiceMode] = None,
        environment: Optional[Environment] = None
    ) -> Iterator[str]:
        """
        Exports invoices to JSON format with streaming support.
        
        CRITICAL: Only exports invoices belonging to the authenticated tenant.
        
        Args:
            date_from: Filter by start date
            date_to: Filter by end date
            invoice_number: Filter by invoice number (partial match)
            status: Filter by invoice status
            phase: Filter by invoice phase
            environment: Filter by environment
            
        Yields:
            JSON lines (newline-delimited JSON)
        """
        # Build query with tenant isolation
        query = self._build_invoice_query(
            date_from=date_from,
            date_to=date_to,
            invoice_number=invoice_number,
            status=status,
            phase=phase,
            environment=environment
        )
        
        # Stream results in chunks
        offset = 0
        while True:
            chunk = query.offset(offset).limit(self.CHUNK_SIZE).all()
            if not chunk:
                break
            
            for invoice in chunk:
                record = {
                    'id': invoice.id,
                    'invoice_number': invoice.invoice_number,
                    'phase': invoice.phase.value if invoice.phase else None,
                    'status': invoice.status.value if invoice.status else None,
                    'environment': invoice.environment.value if invoice.environment else None,
                    'total_amount': float(invoice.total_amount),
                    'tax_amount': float(invoice.tax_amount),
                    'hash': invoice.hash,
                    'uuid': invoice.uuid,
                    'error_message': invoice.error_message,
                    'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
                    'updated_at': invoice.updated_at.isoformat() if invoice.updated_at else None
                }
                yield json.dumps(record, ensure_ascii=False) + '\n'
            
            offset += self.CHUNK_SIZE
            
            # If we got fewer than CHUNK_SIZE, we're done
            if len(chunk) < self.CHUNK_SIZE:
                break
    
    def export_invoice_logs_csv(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        invoice_number: Optional[str] = None,
        status: Optional[InvoiceLogStatus] = None,
        environment: Optional[Environment] = None
    ) -> Iterator[str]:
        """
        Exports invoice logs to CSV format with streaming support.
        
        CRITICAL: Only exports logs belonging to the authenticated tenant.
        
        Args:
            date_from: Filter by start date
            date_to: Filter by end date
            invoice_number: Filter by invoice number (partial match)
            status: Filter by log status
            environment: Filter by environment
            
        Yields:
            CSV lines (including header)
        """
        # Build query with tenant isolation
        query = self._build_invoice_log_query(
            date_from=date_from,
            date_to=date_to,
            invoice_number=invoice_number,
            status=status,
            environment=environment
        )
        
        # CSV header
        header = [
            'id', 'invoice_number', 'uuid', 'hash', 'environment',
            'status', 'zatca_response_code', 'action', 'previous_status',
            'submitted_at', 'cleared_at', 'created_at'
        ]
        yield ','.join(header) + '\n'
        
        # Stream results in chunks
        offset = 0
        while True:
            chunk = query.offset(offset).limit(self.CHUNK_SIZE).all()
            if not chunk:
                break
            
            for log in chunk:
                row = [
                    str(log.id),
                    self._escape_csv_field(log.invoice_number),
                    self._escape_csv_field(log.uuid or ''),
                    self._escape_csv_field(log.hash or ''),
                    self._escape_csv_field(log.environment),
                    log.status.value if log.status else '',
                    self._escape_csv_field(log.zatca_response_code or ''),
                    self._escape_csv_field(log.action or ''),
                    self._escape_csv_field(log.previous_status or ''),
                    log.submitted_at.isoformat() if log.submitted_at else '',
                    log.cleared_at.isoformat() if log.cleared_at else '',
                    log.created_at.isoformat() if log.created_at else ''
                ]
                yield ','.join(row) + '\n'
            
            offset += self.CHUNK_SIZE
            
            # If we got fewer than CHUNK_SIZE, we're done
            if len(chunk) < self.CHUNK_SIZE:
                break
    
    def export_invoice_logs_json(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        invoice_number: Optional[str] = None,
        status: Optional[InvoiceLogStatus] = None,
        environment: Optional[Environment] = None
    ) -> Iterator[str]:
        """
        Exports invoice logs to JSON format with streaming support.
        
        CRITICAL: Only exports logs belonging to the authenticated tenant.
        
        Args:
            date_from: Filter by start date
            date_to: Filter by end date
            invoice_number: Filter by invoice number (partial match)
            status: Filter by log status
            environment: Filter by environment
            
        Yields:
            JSON lines (newline-delimited JSON)
        """
        # Build query with tenant isolation
        query = self._build_invoice_log_query(
            date_from=date_from,
            date_to=date_to,
            invoice_number=invoice_number,
            status=status,
            environment=environment
        )
        
        # Stream results in chunks
        offset = 0
        while True:
            chunk = query.offset(offset).limit(self.CHUNK_SIZE).all()
            if not chunk:
                break
            
            for log in chunk:
                record = {
                    'id': log.id,
                    'invoice_number': log.invoice_number,
                    'uuid': log.uuid,
                    'hash': log.hash,
                    'environment': log.environment,
                    'status': log.status.value if log.status else None,
                    'zatca_response_code': log.zatca_response_code,
                    'action': log.action,
                    'previous_status': log.previous_status,
                    'submitted_at': log.submitted_at.isoformat() if log.submitted_at else None,
                    'cleared_at': log.cleared_at.isoformat() if log.cleared_at else None,
                    'created_at': log.created_at.isoformat() if log.created_at else None
                }
                yield json.dumps(record, ensure_ascii=False) + '\n'
            
            offset += self.CHUNK_SIZE
            
            # If we got fewer than CHUNK_SIZE, we're done
            if len(chunk) < self.CHUNK_SIZE:
                break
    
    def _build_invoice_query(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        invoice_number: Optional[str] = None,
        status: Optional[InvoiceStatus] = None,
        phase: Optional[InvoiceMode] = None,
        environment: Optional[Environment] = None
    ):
        """
        Builds invoice query with tenant isolation and filters.
        
        CRITICAL: Always filters by tenant_id.
        """
        # Base query with tenant isolation
        query = (
            self.db.query(Invoice)
            .filter(Invoice.tenant_id == self.tenant_context.tenant_id)
            .order_by(Invoice.created_at.desc(), Invoice.id.desc())
        )
        
        # Apply filters
        if date_from:
            query = query.filter(Invoice.created_at >= date_from)
        
        if date_to:
            # Include the entire end date
            date_to_end = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(Invoice.created_at <= date_to_end)
        
        if invoice_number:
            query = query.filter(Invoice.invoice_number.ilike(f'%{invoice_number}%'))
        
        if status:
            query = query.filter(Invoice.status == status)
        
        if phase:
            query = query.filter(Invoice.phase == phase)
        
        if environment:
            query = query.filter(Invoice.environment == environment)
        
        return query
    
    def _build_invoice_log_query(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        invoice_number: Optional[str] = None,
        status: Optional[InvoiceLogStatus] = None,
        environment: Optional[Environment] = None
    ):
        """
        Builds invoice log query with tenant isolation and filters.
        
        CRITICAL: Always filters by tenant_id.
        """
        # Base query with tenant isolation
        query = (
            self.db.query(InvoiceLog)
            .filter(InvoiceLog.tenant_id == self.tenant_context.tenant_id)
            .order_by(InvoiceLog.created_at.desc(), InvoiceLog.id.desc())
        )
        
        # Apply filters
        if date_from:
            query = query.filter(InvoiceLog.created_at >= date_from)
        
        if date_to:
            # Include the entire end date
            date_to_end = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.filter(InvoiceLog.created_at <= date_to_end)
        
        if invoice_number:
            query = query.filter(InvoiceLog.invoice_number.ilike(f'%{invoice_number}%'))
        
        if status:
            query = query.filter(InvoiceLog.status == status)
        
        if environment:
            query = query.filter(InvoiceLog.environment == environment.value)
        
        return query
    
    def _escape_csv_field(self, value: str) -> str:
        """
        Escapes CSV field value.
        
        Handles:
        - Quotes (double them)
        - Commas (wrap in quotes)
        - Newlines (wrap in quotes)
        """
        if value is None:
            return ''
        
        value_str = str(value)
        
        # If value contains comma, quote, or newline, wrap in quotes and escape quotes
        if ',' in value_str or '"' in value_str or '\n' in value_str or '\r' in value_str:
            return '"' + value_str.replace('"', '""') + '"'
        
        return value_str

