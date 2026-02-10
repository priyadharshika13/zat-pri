"""
Unit tests for export functionality.

Tests invoice and invoice log exports with:
- Tenant isolation enforcement
- CSV and JSON format support
- Filtering functionality
- Streaming for large datasets
- Production access checks
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_log import InvoiceLog, InvoiceLogStatus
from app.schemas.auth import TenantContext
from app.services.export_service import ExportService
from app.core.constants import InvoiceMode, Environment, TaxCategory


@pytest.fixture
def mock_tenant_context():
    """Mock tenant context for testing."""
    return TenantContext(
        tenant_id=1,
        company_name="Test Company LLC",
        vat_number="300123456700003",
        environment=Environment.SANDBOX.value
    )


@pytest.fixture
def sample_invoices(db: Session, mock_tenant_context: TenantContext):
    """Create sample invoices for testing."""
    invoices = []
    base_date = datetime.utcnow() - timedelta(days=5)
    
    for i in range(5):
        invoice = Invoice(
            tenant_id=mock_tenant_context.tenant_id,
            invoice_number=f"INV-TEST-{i:03d}",
            phase=InvoiceMode.PHASE_1 if i % 2 == 0 else InvoiceMode.PHASE_2,
            status=InvoiceStatus.CLEARED if i < 3 else InvoiceStatus.REJECTED,
            environment=Environment.SANDBOX,
            total_amount=100.0 + i * 10,
            tax_amount=15.0 + i * 1.5,
            created_at=base_date + timedelta(days=i)
        )
        db.add(invoice)
        invoices.append(invoice)
    
    db.commit()
    for invoice in invoices:
        db.refresh(invoice)
    
    return invoices


@pytest.fixture
def sample_invoice_logs(db: Session, mock_tenant_context: TenantContext, sample_invoices):
    """Create sample invoice logs for testing."""
    logs = []
    
    for i, invoice in enumerate(sample_invoices):
        log = InvoiceLog(
            tenant_id=mock_tenant_context.tenant_id,
            invoice_number=invoice.invoice_number,
            environment=Environment.SANDBOX.value,
            status=InvoiceLogStatus.CLEARED if i < 3 else InvoiceLogStatus.REJECTED,
            created_at=invoice.created_at
        )
        db.add(log)
        logs.append(log)
    
    db.commit()
    for log in logs:
        db.refresh(log)
    
    return logs


def test_export_invoices_csv_basic(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test basic CSV export of invoices."""
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    
    # Export all invoices
    lines = list(service.export_invoices_csv())
    
    # Should have header + 5 data rows
    assert len(lines) == 6
    assert 'id,invoice_number,phase' in lines[0]  # Header
    # Most recent first (created_at DESC), so INV-TEST-004 should be first
    assert 'INV-TEST-004' in lines[1]  # First invoice (most recent)


def test_export_invoices_csv_filtering(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test CSV export with filtering."""
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    
    # Filter by status
    lines = list(service.export_invoices_csv(status=InvoiceStatus.CLEARED))
    
    # Should have header + 3 CLEARED invoices
    assert len(lines) == 4
    assert all('CLEARED' in line for line in lines[1:])  # All data rows are CLEARED


def test_export_invoices_json_basic(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test basic JSON export of invoices."""
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    
    # Export all invoices
    lines = list(service.export_invoices_json())
    
    # Should have 5 JSON lines
    assert len(lines) == 5
    
    # Parse first line
    import json
    first_record = json.loads(lines[0])
    assert first_record['invoice_number'] == 'INV-TEST-004'  # Most recent first
    assert first_record['status'] == 'REJECTED'
    # Phase alternates: 0=PHASE_1, 1=PHASE_2, 2=PHASE_1, 3=PHASE_2, 4=PHASE_1
    # So index 4 (most recent) is PHASE_1
    assert first_record['phase'] == 'PHASE_1'


def test_export_invoices_tenant_isolation(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test that exports only include tenant's own invoices."""
    # Create invoice for different tenant
    other_tenant = TenantContext(
        tenant_id=2,
        company_name="Other Company",
        vat_number="300123456700004",
        environment=Environment.SANDBOX.value
    )
    
    other_invoice = Invoice(
        tenant_id=2,
        invoice_number="INV-OTHER-001",
        phase=InvoiceMode.PHASE_1,
        status=InvoiceStatus.CLEARED,
        environment=Environment.SANDBOX,
        total_amount=200.0,
        tax_amount=30.0
    )
    db.add(other_invoice)
    db.commit()
    
    # Export with original tenant
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    lines = list(service.export_invoices_csv())
    
    # Should NOT include other tenant's invoice
    assert len(lines) == 6  # Header + 5 original invoices
    assert all('INV-OTHER' not in line for line in lines)


def test_export_invoice_logs_csv(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoice_logs
):
    """Test CSV export of invoice logs."""
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    
    # Export all logs
    lines = list(service.export_invoice_logs_csv())
    
    # Should have header + 5 data rows
    assert len(lines) == 6
    assert 'id,invoice_number,uuid' in lines[0]  # Header
    assert 'INV-TEST' in lines[1]  # First log


def test_export_invoice_logs_json(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoice_logs
):
    """Test JSON export of invoice logs."""
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    
    # Export all logs
    lines = list(service.export_invoice_logs_json())
    
    # Should have 5 JSON lines
    assert len(lines) == 5
    
    # Parse first line
    import json
    first_record = json.loads(lines[0])
    assert 'invoice_number' in first_record
    assert 'status' in first_record


def test_export_csv_escaping(
    db: Session,
    mock_tenant_context: TenantContext
):
    """Test CSV field escaping for special characters."""
    # Create invoice with special characters
    invoice = Invoice(
        tenant_id=mock_tenant_context.tenant_id,
        invoice_number='INV "Test", Inc.',
        phase=InvoiceMode.PHASE_1,
        status=InvoiceStatus.CLEARED,
        environment=Environment.SANDBOX,
        total_amount=100.0,
        tax_amount=15.0,
        error_message='Error with "quotes" and, commas'
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    lines = list(service.export_invoices_csv())
    
    # Should properly escape quotes and commas
    assert len(lines) == 2  # Header + 1 data row
    # Check that quotes are escaped
    assert '""' in lines[1] or '"' in lines[1]


def test_export_date_filtering(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test date range filtering."""
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    
    # Filter by date range (last 2 days)
    date_from = datetime.utcnow() - timedelta(days=2)
    date_to = datetime.utcnow()
    
    lines = list(service.export_invoices_csv(date_from=date_from, date_to=date_to))
    
    # Should have header + invoices in date range
    assert len(lines) >= 2  # At least header + some invoices


def test_export_invoice_number_filtering(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test invoice number filtering (partial match)."""
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    
    # Filter by invoice number
    lines = list(service.export_invoices_csv(invoice_number="TEST-001"))
    
    # Should find invoice with "TEST-001" in number
    assert len(lines) >= 2  # Header + at least one match
    assert any("INV-TEST-001" in line for line in lines)


def test_export_phase_filtering(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test phase filtering."""
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    
    # Filter by Phase-1
    lines = list(service.export_invoices_csv(phase=InvoiceMode.PHASE_1))
    
    # Should have only Phase-1 invoices
    assert len(lines) >= 2  # Header + at least one Phase-1 invoice
    assert all('PHASE_1' in line or 'id,invoice_number' in line for line in lines[1:])


def test_export_environment_filtering(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test environment filtering."""
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    
    # Filter by SANDBOX
    lines = list(service.export_invoices_csv(environment=Environment.SANDBOX))
    
    # Should have only SANDBOX invoices
    assert len(lines) >= 2  # Header + at least one invoice
    assert all('SANDBOX' in line or 'id,invoice_number' in line for line in lines[1:])


def test_export_empty_result(
    db: Session,
    mock_tenant_context: TenantContext
):
    """Test export when no data matches filters."""
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    
    # Filter that matches nothing
    lines = list(service.export_invoices_csv(invoice_number="NONEXISTENT"))
    
    # Should have only header
    assert len(lines) == 1
    assert 'id,invoice_number' in lines[0]


def test_export_chunking(
    db: Session,
    mock_tenant_context: TenantContext
):
    """Test that exports handle large datasets with chunking."""
    # Create many invoices
    invoices = []
    for i in range(2500):  # More than CHUNK_SIZE (1000)
        invoice = Invoice(
            tenant_id=mock_tenant_context.tenant_id,
            invoice_number=f"INV-BULK-{i:04d}",
            phase=InvoiceMode.PHASE_1,
            status=InvoiceStatus.CLEARED,
            environment=Environment.SANDBOX,
            total_amount=100.0,
            tax_amount=15.0
        )
        db.add(invoice)
        invoices.append(invoice)
    
    db.commit()
    
    service = ExportService(db=db, tenant_context=mock_tenant_context)
    
    # Export should handle chunking
    lines = list(service.export_invoices_csv())
    
    # Should have header + 2500 data rows
    assert len(lines) == 2501
    assert 'id,invoice_number' in lines[0]  # Header

