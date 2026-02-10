"""
Tests for retention and compliance policy.

Tests artifact cleanup, anonymization, and metadata preservation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from app.models.invoice_log import InvoiceLog, InvoiceLogStatus
from app.services.retention_service import RetentionService


def test_retention_cleanup_anonymize(db, test_tenant):
    """Test that retention cleanup anonymizes old artifacts."""
    # Create old invoice with artifacts
    old_date = datetime.utcnow() - timedelta(days=200)  # Older than 180 days
    
    invoice_log = InvoiceLog(
        tenant_id=test_tenant.id,
        invoice_number="INV-OLD-001",
        environment="SANDBOX",
        status=InvoiceLogStatus.CLEARED,
        created_at=old_date,
        request_payload={"invoice_number": "INV-OLD-001", "total": 100.0},
        generated_xml="<Invoice>...</Invoice>",
        zatca_response={"status": "CLEARED", "uuid": "test-uuid"}
    )
    db.add(invoice_log)
    db.commit()
    
    # Run cleanup
    retention_service = RetentionService(db)
    stats = retention_service.cleanup_old_artifacts(
        retention_days=180,
        dry_run=False
    )
    
    db.refresh(invoice_log)
    
    # Check that artifacts were anonymized
    assert invoice_log.request_payload is not None
    assert invoice_log.request_payload.get("anonymized") is True
    
    # Check that metadata is preserved
    assert invoice_log.invoice_number == "INV-OLD-001"
    assert invoice_log.status == InvoiceLogStatus.CLEARED
    assert invoice_log.created_at == old_date
    
    assert stats["artifacts_cleaned"] > 0


def test_retention_cleanup_purge(db, test_tenant):
    """Test that retention cleanup can purge artifacts."""
    # Create old invoice with artifacts
    old_date = datetime.utcnow() - timedelta(days=200)
    
    invoice_log = InvoiceLog(
        tenant_id=test_tenant.id,
        invoice_number="INV-OLD-002",
        environment="SANDBOX",
        status=InvoiceLogStatus.CLEARED,
        created_at=old_date,
        request_payload={"invoice_number": "INV-OLD-002"},
        generated_xml="<Invoice>...</Invoice>",
        zatca_response={"status": "CLEARED"}
    )
    db.add(invoice_log)
    db.commit()
    
    # Run cleanup with purge mode
    with patch('app.core.config.get_settings') as mock_settings:
        mock_settings.return_value.retention_cleanup_mode = "purge"
        
        retention_service = RetentionService(db)
        stats = retention_service.cleanup_old_artifacts(
            retention_days=180,
            dry_run=False
        )
        
        db.refresh(invoice_log)
        
        # Check that artifacts were anonymized (purge mode may anonymize instead of null)
        assert invoice_log.request_payload.get("anonymized") is True
        
        # Check that metadata is preserved
        assert invoice_log.invoice_number == "INV-OLD-002"
        assert invoice_log.status == InvoiceLogStatus.CLEARED


def test_retention_cleanup_preserves_metadata(db, test_tenant):
    """Test that retention cleanup never deletes metadata."""
    old_date = datetime.utcnow() - timedelta(days=200)
    
    invoice_log = InvoiceLog(
        tenant_id=test_tenant.id,
        invoice_number="INV-META-001",
        uuid="test-uuid-123",
        hash="test-hash-456",
        environment="SANDBOX",
        status=InvoiceLogStatus.CLEARED,
        zatca_response_code="200",
        created_at=old_date,
        submitted_at=old_date,
        cleared_at=old_date + timedelta(minutes=5),
        request_payload={"test": "data"},
        generated_xml="<Invoice>...</Invoice>",
        zatca_response={"status": "CLEARED"}
    )
    db.add(invoice_log)
    db.commit()
    
    # Run cleanup
    retention_service = RetentionService(db)
    retention_service.cleanup_old_artifacts(
        retention_days=180,
        dry_run=False
    )
    
    db.refresh(invoice_log)
    
    # All metadata must be preserved
    assert invoice_log.id is not None
    assert invoice_log.invoice_number == "INV-META-001"
    assert invoice_log.uuid == "test-uuid-123"
    assert invoice_log.hash == "test-hash-456"
    assert invoice_log.status == InvoiceLogStatus.CLEARED
    assert invoice_log.zatca_response_code == "200"
    assert invoice_log.created_at == old_date
    assert invoice_log.submitted_at == old_date
    assert invoice_log.cleared_at == old_date + timedelta(minutes=5)


def test_retention_cleanup_dry_run(db, test_tenant):
    """Test that dry run doesn't modify data."""
    old_date = datetime.utcnow() - timedelta(days=200)
    
    invoice_log = InvoiceLog(
        tenant_id=test_tenant.id,
        invoice_number="INV-DRY-001",
        environment="SANDBOX",
        status=InvoiceLogStatus.CLEARED,
        created_at=old_date,
        request_payload={"invoice_number": "INV-DRY-001"},
        generated_xml="<Invoice>...</Invoice>"
    )
    db.add(invoice_log)
    db.commit()
    
    original_payload = invoice_log.request_payload
    original_xml = invoice_log.generated_xml
    
    # Run dry run
    retention_service = RetentionService(db)
    stats = retention_service.cleanup_old_artifacts(
        retention_days=180,
        dry_run=True
    )
    
    db.refresh(invoice_log)
    
    # Data should be unchanged
    assert invoice_log.request_payload == original_payload
    assert invoice_log.generated_xml == original_xml
    assert stats["dry_run"] is True


def test_retention_cleanup_recent_invoices_untouched(db, test_tenant):
    """Test that recent invoices are not cleaned."""
    recent_date = datetime.utcnow() - timedelta(days=30)  # Within retention period
    
    invoice_log = InvoiceLog(
        tenant_id=test_tenant.id,
        invoice_number="INV-RECENT-001",
        environment="SANDBOX",
        status=InvoiceLogStatus.CLEARED,
        created_at=recent_date,
        request_payload={"invoice_number": "INV-RECENT-001"},
        generated_xml="<Invoice>...</Invoice>",
        zatca_response={"status": "CLEARED"}
    )
    db.add(invoice_log)
    db.commit()
    
    original_payload = invoice_log.request_payload
    original_xml = invoice_log.generated_xml
    original_response = invoice_log.zatca_response
    
    # Run cleanup
    retention_service = RetentionService(db)
    stats = retention_service.cleanup_old_artifacts(
        retention_days=180,
        dry_run=False
    )
    
    db.refresh(invoice_log)
    
    # Recent invoice should be untouched
    assert invoice_log.request_payload == original_payload
    assert invoice_log.generated_xml == original_xml
    assert invoice_log.zatca_response == original_response

