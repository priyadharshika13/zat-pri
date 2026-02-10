"""
Data retention and compliance policy service.

Handles automatic cleanup of old invoice artifacts according to retention policies.
Ensures compliance with data retention requirements.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.invoice_log import InvoiceLog
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RetentionService:
    """
    Service for managing data retention and cleanup.
    
    CRITICAL: Only cleans artifacts (request_payload, xml, zatca_response).
    Never deletes invoice metadata (ID, status, timestamps).
    """
    
    def __init__(self, db: Session):
        """
        Initializes retention service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.settings = get_settings()
    
    def get_retention_days(self) -> int:
        """
        Gets retention period in days from configuration.
        
        Default: 180 days (6 months)
        Configurable via RETENTION_DAYS environment variable.
        
        Returns:
            Retention period in days
        """
        return getattr(self.settings, 'retention_days', 180)
    
    def cleanup_old_artifacts(
        self,
        retention_days: Optional[int] = None,
        dry_run: bool = False
    ) -> dict:
        """
        Cleans up old invoice artifacts according to retention policy.
        
        CRITICAL: Only removes artifacts (request_payload, generated_xml, zatca_response).
        Invoice metadata (ID, status, timestamps) is NEVER deleted.
        
        Args:
            retention_days: Retention period in days (defaults to configured value)
            dry_run: If True, only reports what would be cleaned without making changes
            
        Returns:
            Dictionary with cleanup statistics
        """
        if retention_days is None:
            retention_days = self.get_retention_days()
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        # Find invoices with artifacts older than retention period
        old_invoices = self.db.query(InvoiceLog).filter(
            and_(
                InvoiceLog.created_at < cutoff_date,
                or_(
                    InvoiceLog.request_payload.isnot(None),
                    InvoiceLog.generated_xml.isnot(None),
                    InvoiceLog.zatca_response.isnot(None)
                )
            )
        ).all()
        
        stats = {
            "cutoff_date": cutoff_date.isoformat(),
            "retention_days": retention_days,
            "invoices_found": len(old_invoices),
            "artifacts_cleaned": 0,
            "dry_run": dry_run
        }
        
        if dry_run:
            logger.info(f"[DRY RUN] Would clean artifacts from {len(old_invoices)} invoices")
            return stats
        
        # Clean artifacts (anonymize or purge)
        cleanup_mode = getattr(self.settings, 'retention_cleanup_mode', 'anonymize')
        
        for invoice in old_invoices:
            artifacts_cleaned = 0
            
            if invoice.request_payload:
                if cleanup_mode == 'purge':
                    invoice.request_payload = None
                else:  # anonymize
                    invoice.request_payload = {"retention_expired": True, "anonymized": True}
                artifacts_cleaned += 1
            
            if invoice.generated_xml:
                if cleanup_mode == 'purge':
                    invoice.generated_xml = None
                else:  # anonymize
                    invoice.generated_xml = "<retention_expired>Anonymized</retention_expired>"
                artifacts_cleaned += 1
            
            if invoice.zatca_response:
                if cleanup_mode == 'purge':
                    invoice.zatca_response = None
                else:  # anonymize
                    invoice.zatca_response = {"retention_expired": True, "anonymized": True}
                artifacts_cleaned += 1
            
            if artifacts_cleaned > 0:
                stats["artifacts_cleaned"] += artifacts_cleaned
                logger.info(
                    f"Cleaned artifacts from invoice log id={invoice.id}, "
                    f"invoice_number={invoice.invoice_number}, "
                    f"artifacts={artifacts_cleaned}, mode={cleanup_mode}"
                )
        
        if stats["artifacts_cleaned"] > 0:
            self.db.commit()
            logger.info(
                f"Retention cleanup completed: {stats['artifacts_cleaned']} artifacts cleaned "
                f"from {stats['invoices_found']} invoices"
            )
        else:
            logger.info("No artifacts to clean")
        
        return stats

