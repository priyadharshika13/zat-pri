"""
Unit tests for reporting APIs.

Tests invoice and VAT reporting endpoints with tenant isolation.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.auth import TenantContext
from app.services.reporting_service import ReportingService
from app.core.constants import InvoiceMode, Environment


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
def mock_tenant_context_2():
    """Second mock tenant context for isolation testing."""
    return TenantContext(
        tenant_id=2,
        company_name="Another Company LLC",
        vat_number="300123456700004",
        environment=Environment.SANDBOX.value
    )


@pytest.fixture
def sample_invoices(db: Session, mock_tenant_context: TenantContext):
    """Create sample invoices for testing."""
    invoices = []
    
    # Create invoices with different statuses
    for i in range(5):
        invoice = Invoice(
            tenant_id=mock_tenant_context.tenant_id,
            invoice_number=f"INV-TEST-{i+1:03d}",
            phase=InvoiceMode.PHASE_1 if i % 2 == 0 else InvoiceMode.PHASE_2,
            status=InvoiceStatus.CLEARED if i < 3 else InvoiceStatus.REJECTED if i == 3 else InvoiceStatus.FAILED,
            environment=Environment.SANDBOX,
            total_amount=100.0 * (i + 1),
            tax_amount=15.0 * (i + 1),
            created_at=datetime.utcnow() - timedelta(days=i)
        )
        db.add(invoice)
        invoices.append(invoice)
    
    db.commit()
    
    for inv in invoices:
        db.refresh(inv)
    
    return invoices


def test_invoice_report_pagination(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test invoice report pagination."""
    service = ReportingService(db, mock_tenant_context)
    
    # Get first page
    invoices, total = service.get_invoice_report(page=1, page_size=2)
    
    assert total == 5
    assert len(invoices) == 2
    # With ORDER BY created_at DESC, id DESC:
    # INV-TEST-001 has created_at = now - 0 days (most recent)
    # INV-TEST-002 has created_at = now - 1 day
    # So INV-TEST-001 should be first
    assert invoices[0].invoice_number == "INV-TEST-001"  # Most recent first
    assert invoices[1].invoice_number == "INV-TEST-002"  # Second most recent


def test_invoice_report_filtering_by_status(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test invoice report filtering by status."""
    service = ReportingService(db, mock_tenant_context)
    
    # Filter by CLEARED status
    invoices, total = service.get_invoice_report(status=InvoiceStatus.CLEARED)
    
    assert total == 3
    assert all(inv.status == InvoiceStatus.CLEARED for inv in invoices)


def test_invoice_report_filtering_by_phase(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test invoice report filtering by phase."""
    service = ReportingService(db, mock_tenant_context)
    
    # Filter by PHASE_1
    invoices, total = service.get_invoice_report(phase=InvoiceMode.PHASE_1)
    
    assert total == 3  # Even indices (0, 2, 4)
    assert all(inv.phase == InvoiceMode.PHASE_1 for inv in invoices)


def test_invoice_report_date_filtering(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test invoice report date filtering."""
    service = ReportingService(db, mock_tenant_context)
    
    # Filter by date range
    date_from = datetime.utcnow() - timedelta(days=2)
    date_to = datetime.utcnow()
    
    invoices, total = service.get_invoice_report(
        date_from=date_from,
        date_to=date_to
    )
    
    # Should include invoices from last 2 days (indices 0, 1)
    assert total >= 2
    assert all(
        date_from <= inv.created_at <= date_to
        for inv in invoices
    )


def test_tenant_isolation(
    db: Session,
    mock_tenant_context: TenantContext,
    mock_tenant_context_2: TenantContext,
    sample_invoices
):
    """Test that tenants cannot see each other's invoices."""
    # Create invoice for tenant 2
    invoice_tenant2 = Invoice(
        tenant_id=mock_tenant_context_2.tenant_id,
        invoice_number="INV-TENANT2-001",
        phase=InvoiceMode.PHASE_1,
        status=InvoiceStatus.CLEARED,
        environment=Environment.SANDBOX,
        total_amount=500.0,
        tax_amount=75.0,
        created_at=datetime.utcnow()
    )
    db.add(invoice_tenant2)
    db.commit()
    db.refresh(invoice_tenant2)
    
    # Query as tenant 1
    service1 = ReportingService(db, mock_tenant_context)
    invoices1, total1 = service1.get_invoice_report()
    
    # Should not see tenant 2's invoice
    assert total1 == 5
    assert all(inv.invoice_number != "INV-TENANT2-001" for inv in invoices1)
    
    # Query as tenant 2
    service2 = ReportingService(db, mock_tenant_context_2)
    invoices2, total2 = service2.get_invoice_report()
    
    # Should only see tenant 2's invoice
    assert total2 == 1
    assert invoices2[0].invoice_number == "INV-TENANT2-001"


def test_vat_summary_daily(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test VAT summary with daily grouping."""
    service = ReportingService(db, mock_tenant_context)
    
    summary_items, total_tax, total_amount, total_count = service.get_vat_summary(
        group_by="day"
    )
    
    assert len(summary_items) > 0
    assert total_tax > 0
    assert total_amount > 0
    assert total_count == 5
    
    # Verify date format (YYYY-MM-DD)
    for item in summary_items:
        assert len(item.date) == 10  # YYYY-MM-DD
        assert item.date.count('-') == 2


def test_vat_summary_monthly(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test VAT summary with monthly grouping."""
    service = ReportingService(db, mock_tenant_context)
    
    summary_items, total_tax, total_amount, total_count = service.get_vat_summary(
        group_by="month"
    )
    
    assert len(summary_items) > 0
    assert total_tax > 0
    assert total_amount > 0
    assert total_count == 5
    
    # Verify date format (YYYY-MM)
    for item in summary_items:
        assert len(item.date) == 7  # YYYY-MM
        assert item.date.count('-') == 1


def test_status_breakdown(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test status breakdown."""
    service = ReportingService(db, mock_tenant_context)
    
    breakdown_items, total = service.get_status_breakdown()
    
    assert total == 5
    
    # Check that we have the expected statuses
    status_counts = {item.status: item.count for item in breakdown_items}
    assert status_counts.get(InvoiceStatus.CLEARED, 0) == 3
    assert status_counts.get(InvoiceStatus.REJECTED, 0) == 1
    assert status_counts.get(InvoiceStatus.FAILED, 0) == 1


def test_revenue_summary(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoices
):
    """Test revenue summary."""
    service = ReportingService(db, mock_tenant_context)
    
    total_revenue, total_tax, net_revenue, cleared_count, total_count = service.get_revenue_summary()
    
    assert total_count == 5
    assert cleared_count == 3
    assert total_revenue > 0
    assert total_tax > 0
    assert net_revenue == total_revenue - total_tax


def test_empty_results(
    db: Session,
    mock_tenant_context: TenantContext
):
    """Test handling of empty results."""
    service = ReportingService(db, mock_tenant_context)
    
    # Invoice report with no data
    invoices, total = service.get_invoice_report()
    assert total == 0
    assert len(invoices) == 0
    
    # VAT summary with no data
    summary_items, total_tax, total_amount, total_count = service.get_vat_summary()
    assert total_count == 0
    assert total_tax == 0.0
    assert total_amount == 0.0
    assert len(summary_items) == 0
    
    # Status breakdown with no data
    breakdown_items, total = service.get_status_breakdown()
    assert total == 0
    assert len(breakdown_items) == 0
    
    # Revenue summary with no data
    total_revenue, total_tax, net_revenue, cleared_count, total_count = service.get_revenue_summary()
    assert total_count == 0
    assert cleared_count == 0
    assert total_revenue == 0.0
    assert total_tax == 0.0
    assert net_revenue == 0.0

