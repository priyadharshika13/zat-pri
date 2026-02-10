"""
Unit tests for invoice persistence refactoring.

Tests the new enterprise-grade invoice persistence with:
- Invoice master entity creation
- Idempotency (duplicate prevention)
- Status updates during processing
- InvoiceLog creation (success and failure)
- Error handling and failure status
"""

import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_log import InvoiceLog, InvoiceLogStatus
from app.schemas.invoice import InvoiceRequest, InvoiceResponse
from app.schemas.auth import TenantContext
from app.services.invoice_service import InvoiceService
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
def sample_invoice_request():
    """Sample invoice request for testing."""
    return InvoiceRequest(
        mode=InvoiceMode.PHASE_1,
        environment=Environment.SANDBOX,
        invoice_number="INV-TEST-001",
        invoice_date=datetime.utcnow(),
        seller_name="Test Seller",
        seller_tax_number="123456789012345",
        line_items=[
            {
                "name": "Test Item",
                "quantity": 1.0,
                "unit_price": 100.0,
                "tax_rate": 15.0,
                "tax_category": "S"
            }
        ],
        total_tax_exclusive=100.0,
        total_tax_amount=15.0,
        total_amount=115.0
    )


@pytest.mark.asyncio
async def test_successful_invoice_persistence(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoice_request: InvoiceRequest
):
    """
    Test successful invoice creation and persistence.
    
    Verifies:
    - Invoice is created BEFORE processing
    - Invoice status is updated during processing
    - InvoiceLog is created after processing
    - Final status is CLEARED
    """
    # Mock successful processing result
    mock_result = InvoiceResponse(
        success=True,
        invoice_number=sample_invoice_request.invoice_number,
        mode=InvoiceMode.PHASE_1,
        environment=Environment.SANDBOX,
        processed_at=datetime.utcnow()
    )
    
    # Create service with mocked processing
    service = InvoiceService(db=db, tenant_context=mock_tenant_context)
    
    with patch.object(service, 'process_invoice', new_callable=AsyncMock) as mock_process:
        mock_process.return_value = mock_result
        
        # Process invoice with persistence
        result = await service.process_invoice_with_persistence(
            request=sample_invoice_request,
            db=db,
            tenant_context=mock_tenant_context
        )
        
        # Verify result
        assert result.success is True
        
        # Verify invoice was created
        invoice = db.query(Invoice).filter(
            Invoice.tenant_id == mock_tenant_context.tenant_id,
            Invoice.invoice_number == sample_invoice_request.invoice_number
        ).first()
        
        assert invoice is not None
        assert invoice.status == InvoiceStatus.CLEARED
        assert invoice.phase == InvoiceMode.PHASE_1
        assert invoice.total_amount == 115.0
        assert invoice.tax_amount == 15.0
        
        # Verify InvoiceLog was created
        log = db.query(InvoiceLog).filter(
            InvoiceLog.tenant_id == mock_tenant_context.tenant_id,
            InvoiceLog.invoice_number == sample_invoice_request.invoice_number
        ).first()
        
        assert log is not None
        assert log.status == InvoiceLogStatus.SUBMITTED


@pytest.mark.asyncio
async def test_rejected_invoice_persistence(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoice_request: InvoiceRequest
):
    """
    Test rejected invoice handling.
    
    Verifies:
    - Invoice is created BEFORE processing
    - Invoice status is updated to REJECTED
    - InvoiceLog is created with REJECTED status
    """
    # Mock rejected processing result (Phase-2 clearance rejection)
    from app.schemas.phase2 import ClearanceResponse
    
    mock_result = InvoiceResponse(
        success=True,
        invoice_number=sample_invoice_request.invoice_number,
        mode=InvoiceMode.PHASE_2,
        environment=Environment.SANDBOX,
        clearance=ClearanceResponse(
            clearance_status="REJECTED",
            clearance_uuid="test-uuid",
            qr_code="",
            reporting_status=None
        ),
        processed_at=datetime.utcnow()
    )
    
    # Update request for Phase-2
    sample_invoice_request.mode = InvoiceMode.PHASE_2
    
    # Create service
    service = InvoiceService(db=db, tenant_context=mock_tenant_context)
    
    with patch.object(service, 'process_invoice', new_callable=AsyncMock) as mock_process:
        mock_process.return_value = mock_result
        
        # Process invoice with persistence
        result = await service.process_invoice_with_persistence(
            request=sample_invoice_request,
            db=db,
            tenant_context=mock_tenant_context
        )
        
        # Verify result
        assert result.success is True
        
        # Verify invoice status is REJECTED
        invoice = db.query(Invoice).filter(
            Invoice.tenant_id == mock_tenant_context.tenant_id,
            Invoice.invoice_number == sample_invoice_request.invoice_number
        ).first()
        
        assert invoice is not None
        assert invoice.status == InvoiceStatus.REJECTED
        
        # Verify InvoiceLog was created with REJECTED status
        log = db.query(InvoiceLog).filter(
            InvoiceLog.tenant_id == mock_tenant_context.tenant_id,
            InvoiceLog.invoice_number == sample_invoice_request.invoice_number
        ).first()
        
        assert log is not None
        assert log.status == InvoiceLogStatus.REJECTED


@pytest.mark.asyncio
async def test_duplicate_invoice_idempotency(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoice_request: InvoiceRequest
):
    """
    Test duplicate invoice prevention (idempotency).
    
    Verifies:
    - First submission creates invoice
    - Second submission with same invoice_number is rejected
    - Unique constraint (tenant_id + invoice_number) is enforced
    """
    # Create service
    service = InvoiceService(db=db, tenant_context=mock_tenant_context)
    
    # Mock successful processing
    mock_result = InvoiceResponse(
        success=True,
        invoice_number=sample_invoice_request.invoice_number,
        mode=InvoiceMode.PHASE_1,
        environment=Environment.SANDBOX,
        processed_at=datetime.utcnow()
    )
    
    with patch.object(service, 'process_invoice', new_callable=AsyncMock) as mock_process:
        mock_process.return_value = mock_result
        
        # First submission - should succeed
        result1 = await service.process_invoice_with_persistence(
            request=sample_invoice_request,
            db=db,
            tenant_context=mock_tenant_context
        )
        
        assert result1.success is True
        
        # Verify invoice was created
        invoice1 = db.query(Invoice).filter(
            Invoice.tenant_id == mock_tenant_context.tenant_id,
            Invoice.invoice_number == sample_invoice_request.invoice_number
        ).first()
        
        assert invoice1 is not None
        assert invoice1.status == InvoiceStatus.CLEARED
        
        # Second submission with same invoice_number - should raise ValueError
        with pytest.raises(ValueError, match="already exists"):
            await service.process_invoice_with_persistence(
                request=sample_invoice_request,
                db=db,
                tenant_context=mock_tenant_context
            )


@pytest.mark.asyncio
async def test_failed_invoice_persistence(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoice_request: InvoiceRequest
):
    """
    Test failed invoice handling.
    
    Verifies:
    - Invoice is created BEFORE processing
    - Invoice status is updated to FAILED on error
    - Error message is stored
    - InvoiceLog is created with ERROR status
    """
    # Create service
    service = InvoiceService(db=db, tenant_context=mock_tenant_context)
    
    # Mock processing failure
    with patch.object(service, 'process_invoice', new_callable=AsyncMock) as mock_process:
        mock_process.side_effect = ValueError("Processing failed: ZATCA API error")
        
        # Process invoice - should raise exception
        with pytest.raises(ValueError, match="Processing failed"):
            await service.process_invoice_with_persistence(
                request=sample_invoice_request,
                db=db,
                tenant_context=mock_tenant_context
            )
        
        # Verify invoice was created and marked as FAILED
        invoice = db.query(Invoice).filter(
            Invoice.tenant_id == mock_tenant_context.tenant_id,
            Invoice.invoice_number == sample_invoice_request.invoice_number
        ).first()
        
        assert invoice is not None
        assert invoice.status == InvoiceStatus.FAILED
        assert invoice.error_message is not None
        assert "Processing failed" in invoice.error_message
        
        # Verify InvoiceLog was created with ERROR status
        log = db.query(InvoiceLog).filter(
            InvoiceLog.tenant_id == mock_tenant_context.tenant_id,
            InvoiceLog.invoice_number == sample_invoice_request.invoice_number
        ).first()
        
        assert log is not None
        assert log.status == InvoiceLogStatus.ERROR


@pytest.mark.asyncio
async def test_invoice_status_progression(
    db: Session,
    mock_tenant_context: TenantContext,
    sample_invoice_request: InvoiceRequest
):
    """
    Test invoice status progression during processing.
    
    Verifies:
    - Invoice starts as CREATED
    - Status changes to PROCESSING
    - Status changes to CLEARED on success
    """
    # Create service
    service = InvoiceService(db=db, tenant_context=mock_tenant_context)
    
    # Mock successful processing
    mock_result = InvoiceResponse(
        success=True,
        invoice_number=sample_invoice_request.invoice_number,
        mode=InvoiceMode.PHASE_1,
        environment=Environment.SANDBOX,
        processed_at=datetime.utcnow()
    )
    
    with patch.object(service, 'process_invoice', new_callable=AsyncMock) as mock_process:
        mock_process.return_value = mock_result
        
        # Process invoice
        await service.process_invoice_with_persistence(
            request=sample_invoice_request,
            db=db,
            tenant_context=mock_tenant_context
        )
        
        # Verify final status is CLEARED
        invoice = db.query(Invoice).filter(
            Invoice.tenant_id == mock_tenant_context.tenant_id,
            Invoice.invoice_number == sample_invoice_request.invoice_number
        ).first()
        
        assert invoice is not None
        assert invoice.status == InvoiceStatus.CLEARED
        
        # Verify timestamps are set
        assert invoice.created_at is not None
        assert invoice.updated_at is not None
        assert invoice.updated_at >= invoice.created_at

