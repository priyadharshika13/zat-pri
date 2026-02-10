"""
Tests for automatic reporting after successful clearance.

Verifies that when Phase-2 invoice clearance succeeds with status CLEARED,
the system automatically calls the ZATCA Reporting API and stores the result.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.invoice_service import InvoiceService
from app.schemas.invoice import InvoiceRequest, LineItem
from app.core.constants import InvoiceMode, Environment, TaxCategory


@pytest.mark.asyncio
async def test_auto_reporting_after_cleared_clearance():
    """Test that reporting is automatically called when clearance status is CLEARED."""
    
    # Create invoice request
    request = InvoiceRequest(
        mode=InvoiceMode.PHASE_2,
        environment=Environment.SANDBOX,
        invoice_number="INV-AUTO-REPORT-001",
        invoice_date=datetime.utcnow(),
        seller_name="Test Seller",
        seller_tax_number="123456789012345",
        line_items=[
            LineItem(
                name="Test Item",
                quantity=1.0,
                unit_price=100.0,
                tax_rate=15.0,
                tax_category=TaxCategory.STANDARD
            )
        ],
        total_tax_exclusive=100.0,
        total_tax_amount=15.0,
        total_amount=115.0,
        uuid="test-uuid-123"
    )
    
    # Mock services
    with patch('app.services.invoice_service.XMLGenerator') as mock_xml_gen, \
         patch('app.services.invoice_service.CryptoService') as mock_crypto, \
         patch('app.services.invoice_service.Phase2QRService') as mock_qr, \
         patch('app.services.invoice_service.ClearanceService') as mock_clearance_service:
        
        # Setup mocks
        mock_xml_gen_instance = MagicMock()
        mock_xml_gen_instance.generate.return_value = "<Invoice>Test XML</Invoice>"
        mock_xml_gen.return_value = mock_xml_gen_instance
        
        mock_crypto_instance = MagicMock()
        mock_crypto_instance.compute_xml_hash.return_value = "test-hash-123"
        mock_crypto_instance.sign = AsyncMock(return_value=("<SignedInvoice>...</SignedInvoice>", "test-signature"))
        mock_crypto.return_value = mock_crypto_instance
        
        mock_qr_instance = MagicMock()
        mock_qr_instance.generate.return_value = {"qr_code_base64": "test-qr-code"}
        mock_qr.return_value = mock_qr_instance
        
        # Mock clearance service - returns CLEARED status
        mock_clearance_service_instance = MagicMock()
        mock_clearance_service_instance.submit_clearance = AsyncMock(return_value={
            "status": "CLEARED",
            "uuid": "test-uuid-123",
            "qr_code": "test-qr-code-from-zatca"
        })
        
        # Mock reporting - should be called automatically
        mock_reporting_result = {
            "status": "REPORTED",
            "message": "Invoice reported successfully"
        }
        mock_clearance_service_instance.report = AsyncMock(return_value=mock_reporting_result)
        mock_clearance_service.return_value = mock_clearance_service_instance
        
        # Create invoice service
        service = InvoiceService()
        service.xml_generator = mock_xml_gen_instance
        service.crypto_service = mock_crypto_instance
        service.phase2_qr_service = mock_qr_instance
        service.clearance_service = mock_clearance_service_instance
        
        # Mock validator to pass
        with patch.object(service, 'phase2_validator') as mock_validator:
            mock_validation_result = MagicMock()
            mock_validation_result.status = "PASS"
            mock_validation_result.issues = []
            mock_validator.validate = AsyncMock(return_value=mock_validation_result)
            
            # Process invoice
            result = await service._process_phase2(request)
        
        # Verify clearance was called
        mock_clearance_service_instance.submit_clearance.assert_called_once()
        
        # Verify reporting was called automatically (because clearance status is CLEARED)
        mock_clearance_service_instance.report.assert_called_once()
        
        # Verify reporting was called with correct parameters
        report_call_args = mock_clearance_service_instance.report.call_args
        assert report_call_args.kwargs['invoice_uuid'] == "test-uuid-123"
        assert report_call_args.kwargs['clearance_status'] == "CLEARED"
        
        # Verify response includes reporting result
        assert result.success is True
        assert result.clearance.clearance_status == "CLEARED"
        assert result.reporting is not None
        assert result.reporting['status'] == "REPORTED"
        assert result.reporting['message'] == "Invoice reported successfully"


@pytest.mark.asyncio
async def test_auto_reporting_not_called_when_clearance_rejected():
    """Test that reporting is NOT called when clearance status is REJECTED."""
    
    request = InvoiceRequest(
        mode=InvoiceMode.PHASE_2,
        environment=Environment.SANDBOX,
        invoice_number="INV-REJECTED-001",
        invoice_date=datetime.utcnow(),
        seller_name="Test Seller",
        seller_tax_number="123456789012345",
        line_items=[
            LineItem(
                name="Test Item",
                quantity=1.0,
                unit_price=100.0,
                tax_rate=15.0,
                tax_category=TaxCategory.STANDARD
            )
        ],
        total_tax_exclusive=100.0,
        total_tax_amount=15.0,
        total_amount=115.0,
        uuid="test-uuid-rejected"
    )
    
    with patch('app.services.invoice_service.XMLGenerator') as mock_xml_gen, \
         patch('app.services.invoice_service.CryptoService') as mock_crypto, \
         patch('app.services.invoice_service.Phase2QRService') as mock_qr, \
         patch('app.services.invoice_service.ClearanceService') as mock_clearance_service:
        
        mock_xml_gen_instance = MagicMock()
        mock_xml_gen_instance.generate.return_value = "<Invoice>Test XML</Invoice>"
        mock_xml_gen.return_value = mock_xml_gen_instance
        
        mock_crypto_instance = MagicMock()
        mock_crypto_instance.compute_xml_hash.return_value = "test-hash-123"
        mock_crypto_instance.sign = AsyncMock(return_value=("<SignedInvoice>...</SignedInvoice>", "test-signature"))
        mock_crypto.return_value = mock_crypto_instance
        
        mock_qr_instance = MagicMock()
        mock_qr_instance.generate.return_value = {"qr_code_base64": "test-qr-code"}
        mock_qr.return_value = mock_qr_instance
        
        # Mock clearance service - returns REJECTED status
        mock_clearance_service_instance = MagicMock()
        mock_clearance_service_instance.submit_clearance = AsyncMock(return_value={
            "status": "REJECTED",
            "uuid": "test-uuid-rejected",
            "qr_code": None,
            "error": "Validation failed"
        })
        mock_clearance_service_instance.report = AsyncMock()
        mock_clearance_service.return_value = mock_clearance_service_instance
        
        service = InvoiceService()
        service.xml_generator = mock_xml_gen_instance
        service.crypto_service = mock_crypto_instance
        service.phase2_qr_service = mock_qr_instance
        service.clearance_service = mock_clearance_service_instance
        
        with patch.object(service, 'phase2_validator') as mock_validator:
            mock_validation_result = MagicMock()
            mock_validation_result.status = "PASS"
            mock_validation_result.issues = []
            mock_validator.validate = AsyncMock(return_value=mock_validation_result)
            
            result = await service._process_phase2(request)
        
        # Verify clearance was called
        mock_clearance_service_instance.submit_clearance.assert_called_once()
        
        # Verify reporting was NOT called (because clearance status is REJECTED)
        mock_clearance_service_instance.report.assert_not_called()
        
        # Verify response does not include reporting
        assert result.success is True
        assert result.clearance.clearance_status == "REJECTED"
        assert result.reporting is None


@pytest.mark.asyncio
async def test_reporting_failure_does_not_fail_invoice():
    """Test that if reporting fails, invoice clearance still succeeds."""
    
    request = InvoiceRequest(
        mode=InvoiceMode.PHASE_2,
        environment=Environment.SANDBOX,
        invoice_number="INV-REPORT-FAIL-001",
        invoice_date=datetime.utcnow(),
        seller_name="Test Seller",
        seller_tax_number="123456789012345",
        line_items=[
            LineItem(
                name="Test Item",
                quantity=1.0,
                unit_price=100.0,
                tax_rate=15.0,
                tax_category=TaxCategory.STANDARD
            )
        ],
        total_tax_exclusive=100.0,
        total_tax_amount=15.0,
        total_amount=115.0,
        uuid="test-uuid-report-fail"
    )
    
    with patch('app.services.invoice_service.XMLGenerator') as mock_xml_gen, \
         patch('app.services.invoice_service.CryptoService') as mock_crypto, \
         patch('app.services.invoice_service.Phase2QRService') as mock_qr, \
         patch('app.services.invoice_service.ClearanceService') as mock_clearance_service:
        
        mock_xml_gen_instance = MagicMock()
        mock_xml_gen_instance.generate.return_value = "<Invoice>Test XML</Invoice>"
        mock_xml_gen.return_value = mock_xml_gen_instance
        
        mock_crypto_instance = MagicMock()
        mock_crypto_instance.compute_xml_hash.return_value = "test-hash-123"
        mock_crypto_instance.sign = AsyncMock(return_value=("<SignedInvoice>...</SignedInvoice>", "test-signature"))
        mock_crypto.return_value = mock_crypto_instance
        
        mock_qr_instance = MagicMock()
        mock_qr_instance.generate.return_value = {"qr_code_base64": "test-qr-code"}
        mock_qr.return_value = mock_qr_instance
        
        # Mock clearance service - returns CLEARED status
        mock_clearance_service_instance = MagicMock()
        mock_clearance_service_instance.submit_clearance = AsyncMock(return_value={
            "status": "CLEARED",
            "uuid": "test-uuid-report-fail",
            "qr_code": "test-qr-code-from-zatca"
        })
        
        # Mock reporting to fail
        mock_clearance_service_instance.report = AsyncMock(side_effect=Exception("Reporting API error"))
        mock_clearance_service.return_value = mock_clearance_service_instance
        
        service = InvoiceService()
        service.xml_generator = mock_xml_gen_instance
        service.crypto_service = mock_crypto_instance
        service.phase2_qr_service = mock_qr_instance
        service.clearance_service = mock_clearance_service_instance
        
        with patch.object(service, 'phase2_validator') as mock_validator:
            mock_validation_result = MagicMock()
            mock_validation_result.status = "PASS"
            mock_validation_result.issues = []
            mock_validator.validate = AsyncMock(return_value=mock_validation_result)
            
            # Process should succeed even if reporting fails
            result = await service._process_phase2(request)
        
        # Verify clearance was called and succeeded
        mock_clearance_service_instance.submit_clearance.assert_called_once()
        
        # Verify reporting was attempted
        mock_clearance_service_instance.report.assert_called_once()
        
        # Verify invoice still succeeds (clearance succeeded)
        assert result.success is True
        assert result.clearance.clearance_status == "CLEARED"
        
        # Verify reporting error is captured in response
        assert result.reporting is not None
        assert result.reporting['status'] == "FAILED"
        assert "error" in result.reporting
        assert "Reporting API error" in result.reporting['error']
        assert "clearance was successful" in result.reporting.get('note', '').lower()


@pytest.mark.asyncio
async def test_reporting_headers_include_clearance_status():
    """Test that reporting API is called with Clearance-Status and Accept-Version headers."""
    
    from app.integrations.zatca.sandbox import ZATCASandboxClient
    
    with patch('app.integrations.zatca.sandbox.get_oauth_service') as mock_oauth, \
         patch('httpx.AsyncClient') as mock_client_class:
        
        # Mock OAuth service
        mock_oauth_service = MagicMock()
        mock_oauth_service.get_access_token = AsyncMock(return_value="test-token-123")
        mock_oauth.return_value = mock_oauth_service
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "REPORTED",
            "message": "Invoice reported successfully"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Create client and call reporting
        client = ZATCASandboxClient()
        result = await client.report_invoice(
            invoice_uuid="test-uuid-123",
            clearance_status="CLEARED"
        )
        
        # Verify request was made
        mock_client.post.assert_called_once()
        
        # Verify headers include Clearance-Status and Accept-Version
        call_args = mock_client.post.call_args
        headers = call_args.kwargs['headers']
        
        assert 'Authorization' in headers
        assert headers['Clearance-Status'] == "CLEARED"
        assert headers['Accept-Version'] == "1.0"
        
        # Verify result
        assert result['status'] == "REPORTED"

