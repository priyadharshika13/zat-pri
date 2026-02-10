"""
Invoice audit trail logging service.

Provides immutable audit records for invoice processing.
Tracks invoice submissions, clearance status, ZATCA responses, and AI usage.

CRITICAL: Audit records are immutable - once created, they cannot be modified.
"""

import logging
import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InvoiceAuditRecord:
    """
    Immutable invoice audit record.
    
    CRITICAL: This is a frozen dataclass - records cannot be modified after creation.
    This ensures audit trail integrity and immutability.
    """
    invoice_number: str
    uuid: Optional[str]
    hash: Optional[str]
    submission_time: datetime
    clearance_status: Optional[str]
    zatca_response_code: Optional[str]
    ai_used: bool
    
    def to_dict(self) -> dict:
        """Converts audit record to dictionary for serialization."""
        return {
            "invoice_number": self.invoice_number,
            "uuid": self.uuid,
            "hash": self.hash,
            "submission_time": self.submission_time.isoformat(),
            "clearance_status": self.clearance_status,
            "zatca_response_code": self.zatca_response_code,
            "ai_used": self.ai_used
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "InvoiceAuditRecord":
        """Creates audit record from dictionary."""
        return cls(
            invoice_number=data["invoice_number"],
            uuid=data.get("uuid"),
            hash=data.get("hash"),
            submission_time=datetime.fromisoformat(data["submission_time"]),
            clearance_status=data.get("clearance_status"),
            zatca_response_code=data.get("zatca_response_code"),
            ai_used=data.get("ai_used", False)
        )


class InvoiceAuditService:
    """
    Service for logging immutable invoice audit records.
    
    Provides audit trail logging with immutability guarantees.
    Records are append-only and cannot be modified after creation.
    """
    
    def __init__(self, audit_file_path: Optional[str] = None):
        """
        Initializes audit service.
        
        Args:
            audit_file_path: Optional path to audit log file.
                            If not provided, uses default from config or creates in logs directory.
        """
        settings = get_settings()
        
        if audit_file_path:
            self.audit_file_path = Path(audit_file_path)
        else:
            # Default: logs/invoice_audit.jsonl (JSON Lines format for append-only)
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            self.audit_file_path = logs_dir / "invoice_audit.jsonl"
        
        # Ensure audit file directory exists
        self.audit_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Invoice audit service initialized. Audit file: {self.audit_file_path}")
    
    def log_invoice_submission(
        self,
        invoice_number: str,
        uuid: Optional[str] = None,
        hash: Optional[str] = None,
        submission_time: Optional[datetime] = None,
        clearance_status: Optional[str] = None,
        zatca_response_code: Optional[str] = None,
        ai_used: bool = False
    ) -> InvoiceAuditRecord:
        """
        Logs an immutable invoice audit record.
        
        CRITICAL: This creates an immutable record that cannot be modified.
        All audit records are append-only.
        
        Args:
            invoice_number: Invoice number
            uuid: Invoice UUID (for Phase-2)
            hash: XML hash value
            submission_time: Time of submission (defaults to now)
            clearance_status: ZATCA clearance status (CLEARED, REJECTED, etc.)
            zatca_response_code: ZATCA response error code (if any)
            ai_used: Whether AI was used in processing
            
        Returns:
            Immutable InvoiceAuditRecord
        """
        if submission_time is None:
            submission_time = datetime.now()
        
        # Create immutable audit record
        audit_record = InvoiceAuditRecord(
            invoice_number=invoice_number,
            uuid=uuid,
            hash=hash,
            submission_time=submission_time,
            clearance_status=clearance_status,
            zatca_response_code=zatca_response_code,
            ai_used=ai_used
        )
        
        # Write to audit log file (append-only)
        self._write_audit_record(audit_record)
        
        logger.info(
            f"Invoice audit record created: invoice_number={invoice_number}, "
            f"uuid={uuid}, clearance_status={clearance_status}, ai_used={ai_used}"
        )
        
        return audit_record
    
    def _write_audit_record(self, record: InvoiceAuditRecord) -> None:
        """
        Writes audit record to file (append-only).
        
        Uses JSON Lines format (one JSON object per line) for:
        - Easy append-only writes
        - Easy parsing and reading
        - Immutability (no in-place modifications)
        
        Args:
            record: Immutable audit record to write
        """
        try:
            # Convert to dictionary and serialize to JSON
            record_dict = record.to_dict()
            json_line = json.dumps(record_dict, ensure_ascii=False)
            
            # Append to file (append-only, ensures immutability)
            with open(self.audit_file_path, "a", encoding="utf-8") as f:
                f.write(json_line + "\n")
            
            logger.debug(f"Audit record written to {self.audit_file_path}")
            
        except Exception as e:
            # Log error but don't fail the main operation
            logger.error(f"Failed to write audit record: {e}")
    
    def read_audit_records(
        self,
        invoice_number: Optional[str] = None,
        limit: Optional[int] = None
    ) -> list[InvoiceAuditRecord]:
        """
        Reads audit records from file.
        
        Args:
            invoice_number: Optional filter by invoice number
            limit: Optional limit on number of records to return
            
        Returns:
            List of immutable audit records
        """
        if not self.audit_file_path.exists():
            return []
        
        records = []
        
        try:
            with open(self.audit_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        record_dict = json.loads(line)
                        record = InvoiceAuditRecord.from_dict(record_dict)
                        
                        # Filter by invoice number if specified
                        if invoice_number and record.invoice_number != invoice_number:
                            continue
                        
                        records.append(record)
                        
                        # Apply limit if specified
                        if limit and len(records) >= limit:
                            break
                            
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.warning(f"Failed to parse audit record line: {e}")
                        continue
            
            # Return in reverse chronological order (newest first)
            records.reverse()
            
        except Exception as e:
            logger.error(f"Failed to read audit records: {e}")
        
        return records
    
    def get_invoice_audit_history(self, invoice_number: str) -> list[InvoiceAuditRecord]:
        """
        Gets complete audit history for a specific invoice.
        
        Args:
            invoice_number: Invoice number to query
            
        Returns:
            List of audit records for the invoice (chronological order)
        """
        records = self.read_audit_records(invoice_number=invoice_number)
        # Return in chronological order (oldest first)
        return list(reversed(records))

