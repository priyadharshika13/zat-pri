"""
Invoice log service for tenant-scoped invoice tracking.

Provides CRUD operations for invoice logs with strict tenant isolation.
All operations are automatically scoped to the requesting tenant.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.invoice_log import InvoiceLog, InvoiceLogStatus
from app.schemas.auth import TenantContext
from app.utils.data_masking import mask_sensitive_fields, safe_json_dump, safe_xml_storage

logger = logging.getLogger(__name__)


class InvoiceLogService:
    """
    Service for managing tenant-scoped invoice logs.
    
    CRITICAL: All operations enforce tenant isolation.
    No cross-tenant access is possible.
    """
    
    def __init__(self, db: Session, tenant_context: TenantContext):
        """
        Initializes invoice log service.
        
        Args:
            db: Database session
            tenant_context: Tenant context from request (enforces isolation)
        """
        self.db = db
        self.tenant_context = tenant_context
    
    def create_log(
        self,
        invoice_number: str,
        uuid: Optional[str] = None,
        hash: Optional[str] = None,
        environment: Optional[str] = None,
        status: InvoiceLogStatus = InvoiceLogStatus.SUBMITTED,
        zatca_response_code: Optional[str] = None,
        request_payload: Optional[Dict[str, Any]] = None,
        generated_xml: Optional[str] = None,
        zatca_response: Optional[Dict[str, Any]] = None,
        submitted_at: Optional[datetime] = None,
        cleared_at: Optional[datetime] = None,
        action: Optional[str] = None,
        previous_status: Optional[str] = None
    ) -> InvoiceLog:
        """
        Creates a new invoice log entry with optional observability fields.
        
        CRITICAL: tenant_id is automatically set from tenant_context.
        Caller cannot override tenant_id - this enforces isolation.
        
        Phase 8: Stores request payload, XML, and ZATCA response only after successful generation.
        Sensitive fields are masked before storage.
        
        Args:
            invoice_number: Invoice number
            uuid: Invoice UUID (optional)
            hash: XML hash (optional)
            environment: Environment (defaults to tenant environment)
            status: Log status
            zatca_response_code: ZATCA response code (optional)
            request_payload: Original invoice request payload (will be masked)
            generated_xml: Generated XML content (for Phase-2)
            zatca_response: Full ZATCA API response (will be masked)
            submitted_at: Timestamp when invoice was submitted to ZATCA
            cleared_at: Timestamp when invoice was cleared by ZATCA
            
        Returns:
            Created InvoiceLog instance
        """
        # Mask sensitive fields in request payload
        safe_request_payload = None
        if request_payload:
            masked_payload = mask_sensitive_fields(request_payload)
            safe_request_payload = json.loads(safe_json_dump(masked_payload)) if safe_json_dump(masked_payload) else None
        
        # Mask sensitive fields in ZATCA response
        safe_zatca_response = None
        if zatca_response:
            masked_response = mask_sensitive_fields(zatca_response)
            safe_zatca_response = json.loads(safe_json_dump(masked_response)) if safe_json_dump(masked_response) else None
        
        # Validate and store XML safely
        safe_xml = safe_xml_storage(generated_xml) if generated_xml else None
        
        log_entry = InvoiceLog(
            tenant_id=self.tenant_context.tenant_id,  # CRITICAL: Always from context
            invoice_number=invoice_number,
            uuid=uuid,
            hash=hash,
            environment=environment or self.tenant_context.environment,
            status=status,
            zatca_response_code=zatca_response_code,
            request_payload=safe_request_payload,
            generated_xml=safe_xml,
            zatca_response=safe_zatca_response,
            submitted_at=submitted_at,
            cleared_at=cleared_at,
            action=action,
            previous_status=previous_status
        )
        
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        
        logger.info(
            f"Created invoice log: invoice_number={invoice_number}, "
            f"tenant_id={self.tenant_context.tenant_id}, status={status.value}"
        )
        
        return log_entry
    
    def update_log_with_artifacts(
        self,
        invoice_number: str,
        request_payload: Optional[Dict[str, Any]] = None,
        generated_xml: Optional[str] = None,
        zatca_response: Optional[Dict[str, Any]] = None,
        submitted_at: Optional[datetime] = None,
        cleared_at: Optional[datetime] = None
    ) -> Optional[InvoiceLog]:
        """
        Updates an existing invoice log with observability artifacts.
        
        CRITICAL: Only updates logs belonging to current tenant.
        Data is masked and validated before storage.
        
        Args:
            invoice_number: Invoice number
            request_payload: Original invoice request payload
            generated_xml: Generated XML content
            zatca_response: Full ZATCA API response
            submitted_at: Timestamp when invoice was submitted
            cleared_at: Timestamp when invoice was cleared
            
        Returns:
            Updated InvoiceLog or None if not found
        """
        log_entry = self.get_log_by_invoice_number(invoice_number)
        
        if not log_entry:
            logger.warning(
                f"Log entry not found for invoice_number={invoice_number}, "
                f"tenant_id={self.tenant_context.tenant_id}"
            )
            return None
        
        # Mask and validate data before updating
        if request_payload:
            masked_payload = mask_sensitive_fields(request_payload)
            safe_payload = json.loads(safe_json_dump(masked_payload)) if safe_json_dump(masked_payload) else None
            log_entry.request_payload = safe_payload
        
        if generated_xml:
            log_entry.generated_xml = safe_xml_storage(generated_xml)
        
        if zatca_response:
            masked_response = mask_sensitive_fields(zatca_response)
            safe_response = json.loads(safe_json_dump(masked_response)) if safe_json_dump(masked_response) else None
            log_entry.zatca_response = safe_response
        
        if submitted_at:
            log_entry.submitted_at = submitted_at
        
        if cleared_at:
            log_entry.cleared_at = cleared_at
        
        self.db.commit()
        self.db.refresh(log_entry)
        
        logger.info(
            f"Updated invoice log artifacts: invoice_number={invoice_number}, "
            f"tenant_id={self.tenant_context.tenant_id}"
        )
        
        return log_entry
    
    def get_logs(
        self,
        invoice_number: Optional[str] = None,
        status: Optional[InvoiceLogStatus] = None,
        limit: int = 100
    ) -> List[InvoiceLog]:
        """
        Retrieves invoice logs for the current tenant.
        
        CRITICAL: All queries are automatically filtered by tenant_id.
        No cross-tenant access is possible.
        
        Args:
            invoice_number: Optional filter by invoice number
            status: Optional filter by status
            limit: Maximum number of records to return
            
        Returns:
            List of InvoiceLog instances (tenant-scoped)
        """
        query = self.db.query(InvoiceLog).filter(
            InvoiceLog.tenant_id == self.tenant_context.tenant_id  # CRITICAL: Tenant isolation
        )
        
        if invoice_number:
            query = query.filter(InvoiceLog.invoice_number == invoice_number)
        
        if status:
            query = query.filter(InvoiceLog.status == status)
        
        query = query.order_by(InvoiceLog.created_at.desc())
        query = query.limit(limit)
        
        return query.all()
    
    def get_log_by_invoice_number(self, invoice_number: str) -> Optional[InvoiceLog]:
        """
        Gets the most recent log entry for an invoice.
        
        CRITICAL: Automatically scoped to current tenant.
        
        Args:
            invoice_number: Invoice number to query
            
        Returns:
            Most recent InvoiceLog or None
        """
        return self.db.query(InvoiceLog).filter(
            InvoiceLog.tenant_id == self.tenant_context.tenant_id,
            InvoiceLog.invoice_number == invoice_number
        ).order_by(InvoiceLog.created_at.desc()).first()
    
    def update_log_status(
        self,
        invoice_number: str,
        status: InvoiceLogStatus,
        zatca_response_code: Optional[str] = None,
        cleared_at: Optional[datetime] = None
    ) -> Optional[InvoiceLog]:
        """
        Updates the status of an invoice log entry.
        
        CRITICAL: Only updates logs belonging to current tenant.
        
        Args:
            invoice_number: Invoice number
            status: New status
            zatca_response_code: Optional ZATCA response code
            cleared_at: Timestamp when invoice was cleared (if status is CLEARED)
            
        Returns:
            Updated InvoiceLog or None if not found
        """
        log_entry = self.get_log_by_invoice_number(invoice_number)
        
        if not log_entry:
            logger.warning(
                f"Log entry not found for invoice_number={invoice_number}, "
                f"tenant_id={self.tenant_context.tenant_id}"
            )
            return None
        
        log_entry.status = status
        if zatca_response_code:
            log_entry.zatca_response_code = zatca_response_code
        
        # Set cleared_at timestamp if status is CLEARED
        if status == InvoiceLogStatus.CLEARED and cleared_at:
            log_entry.cleared_at = cleared_at
        elif status == InvoiceLogStatus.CLEARED and not log_entry.cleared_at:
            # Auto-set cleared_at if not provided
            log_entry.cleared_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(log_entry)
        
        logger.info(
            f"Updated invoice log status: invoice_number={invoice_number}, "
            f"status={status.value}, tenant_id={self.tenant_context.tenant_id}"
        )
        
        return log_entry

