"""
Tests for ZATCA Compliance CSID API endpoint.

Tests the /api/v1/zatca/compliance/csid/submit endpoint with:
- Successful CSR submission and certificate storage
- Error handling (400, 401, 409, 500)
- Input validation
- Tenant isolation
"""

import pytest
from fastapi import status
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

from app.integrations.zatca.compliance_csid import ComplianceCSIDService
from app.integrations.zatca.oauth_service import ZatcaAccessToken


@pytest.fixture
def sample_csr():
    """Sample CSR in PEM format."""
    return """-----BEGIN CERTIFICATE REQUEST-----
MIIBkTCB+wIBADBUMQswCQYDVQQGEwJTQTEPMA0GA1UECAwGUml5YWRoMQ8wDQYD
VQQHDAZSaXlhZGgxFTATBgNVBAoMDFRlc3QgQ29tcGFueTEMMAoGA1UECwwDSVQw
WTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAAR7VJTUt9Us8cKjKzKzKzKzKzKzKzKz
KzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKz
-----END CERTIFICATE REQUEST-----"""


@pytest.fixture
def sample_private_key():
    """Sample private key in PEM format."""
    return """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKj
KzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKz
KzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKz
-----END PRIVATE KEY-----"""


@pytest.fixture
def valid_zatca_response():
    """Valid ZATCA Compliance CSID API response."""
    return {
        "requestID": "12345678-1234-1234-1234-123456789012",
        "dispositionMessage": "Certificate issued successfully",
        "secret": "base64-encoded-secret-value",
        "binarySecurityToken": """-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKL7Q8Q3Q3Q3QzANBgkqhkiG9w0BAQsFADBUMQswCQYD
VQQGEwJTQTEPMA0GA1UECAwGUml5YWRoMQ8wDQYDVQQHDAZSaXlhZGgxFTATBgNV
BAoMDFRlc3QgQ29tcGFueTEMMAoGA1UECwwDSVQwHhcNMjQwMTAxMDAwMDAwWhcN
MjUwMTAxMDAwMDAwWjBUMQswCQYDVQQGEwJTQTEPMA0GA1UECAwGUml5YWRoMQ8w
DQYDVQQHDAZSaXlhZGgxFTATBgNVBAoMDFRlc3QgQ29tcGFueTEMMAoGA1UECwwD
SVQwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC7VJTUt9Us8cKjKzKz
KzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKzKz
-----END CERTIFICATE-----"""
    }


@pytest.mark.asyncio
async def test_submit_csr_to_compliance_csid_success(
    async_client, headers, test_subscription_trial, sample_csr, sample_private_key, valid_zatca_response
):
    """Test successful CSR submission to Compliance CSID API endpoint."""
    with patch('app.integrations.zatca.compliance_csid.ComplianceCSIDService.submit_csr') as mock_submit, \
         patch('app.services.certificate_service.CertificateService.upload_certificate') as mock_upload:
        
        # Mock successful ZATCA response
        mock_submit.return_value = valid_zatca_response
        
        # Mock certificate storage
        from app.models.certificate import Certificate, CertificateStatus
        mock_cert = MagicMock(spec=Certificate)
        mock_cert.id = 1
        mock_cert.certificate_serial = "12345678901234567890"
        mock_cert.issuer = "CN=ZATCA Sandbox CA, O=ZATCA, C=SA"
        mock_cert.expiry_date = datetime.utcnow() + timedelta(days=365)
        mock_cert.uploaded_at = datetime.utcnow()
        mock_cert.environment = "SANDBOX"
        mock_cert.status = CertificateStatus.ACTIVE
        mock_cert.is_active = True
        mock_upload.return_value = mock_cert
        
        # Submit CSR
        form_data = {
            "csr": sample_csr,
            "private_key": sample_private_key,
            "environment": "SANDBOX"
        }
        
        # Remove Content-Type from headers to let httpx set it for form data
        form_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
        
        response = await async_client.post(
            "/api/v1/zatca/compliance/csid/submit",
            headers=form_headers,
            data=form_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert "message" in data
        assert "zatca_response" in data
        assert "certificate" in data
        assert data["zatca_response"]["requestID"] == "12345678-1234-1234-1234-123456789012"
        assert data["certificate"]["id"] == 1
        assert data["certificate"]["environment"] == "SANDBOX"
        assert data["certificate"]["status"] == "ACTIVE"
        
        # Verify service was called correctly
        mock_submit.assert_called_once()
        assert mock_submit.call_args[1]["csr_pem"] == sample_csr


@pytest.mark.asyncio
async def test_submit_csr_invalid_csr_format(
    async_client, headers, test_subscription_trial
):
    """Test CSR submission with invalid CSR format."""
    form_data = {
        "csr": "Invalid CSR format",
        "private_key": "-----BEGIN PRIVATE KEY-----\nTEST\n-----END PRIVATE KEY-----",
        "environment": "SANDBOX"
    }
    
    form_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
    
    response = await async_client.post(
        "/api/v1/zatca/compliance/csid/submit",
        headers=form_headers,
        data=form_data
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Invalid CSR format" in data["detail"]


@pytest.mark.asyncio
async def test_submit_csr_invalid_private_key_format(
    async_client, headers, test_subscription_trial, sample_csr
):
    """Test CSR submission with invalid private key format."""
    form_data = {
        "csr": sample_csr,
        "private_key": "Invalid private key format",
        "environment": "SANDBOX"
    }
    
    form_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
    
    response = await async_client.post(
        "/api/v1/zatca/compliance/csid/submit",
        headers=form_headers,
        data=form_data
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Invalid private key format" in data["detail"]


@pytest.mark.asyncio
async def test_submit_csr_invalid_environment(
    async_client, headers, test_subscription_trial, sample_csr, sample_private_key
):
    """Test CSR submission with invalid environment."""
    form_data = {
        "csr": sample_csr,
        "private_key": sample_private_key,
        "environment": "INVALID"
    }
    
    form_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
    
    response = await async_client.post(
        "/api/v1/zatca/compliance/csid/submit",
        headers=form_headers,
        data=form_data
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Invalid environment" in data["detail"]


@pytest.mark.asyncio
async def test_submit_csr_production_not_supported(
    async_client, headers, test_subscription_trial, sample_csr, sample_private_key
):
    """Test that Production environment is not supported (only SANDBOX)."""
    form_data = {
        "csr": sample_csr,
        "private_key": sample_private_key,
        "environment": "PRODUCTION"
    }
    
    form_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
    
    response = await async_client.post(
        "/api/v1/zatca/compliance/csid/submit",
        headers=form_headers,
        data=form_data
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "only available for SANDBOX" in data["detail"] or "Production Onboarding" in data["detail"]


@pytest.mark.asyncio
async def test_submit_csr_oauth_failure(
    async_client, headers, test_subscription_trial, sample_csr, sample_private_key
):
    """Test handling of OAuth authentication failure."""
    with patch('app.integrations.zatca.compliance_csid.ComplianceCSIDService.submit_csr') as mock_submit:
        # Mock OAuth failure
        mock_submit.side_effect = ValueError("ZATCA OAuth authentication failed: Invalid credentials")
        
        form_data = {
            "csr": sample_csr,
            "private_key": sample_private_key,
            "environment": "SANDBOX"
        }
        
        form_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
        
        response = await async_client.post(
            "/api/v1/zatca/compliance/csid/submit",
            headers=form_headers,
            data=form_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "OAuth authentication failed" in data["detail"]


@pytest.mark.asyncio
async def test_submit_csr_409_conflict(
    async_client, headers, test_subscription_trial, sample_csr, sample_private_key
):
    """Test handling of 409 Conflict (CSR already submitted)."""
    with patch('app.integrations.zatca.compliance_csid.ComplianceCSIDService.submit_csr') as mock_submit:
        # Mock 409 conflict
        mock_submit.side_effect = ValueError("CSR submission conflict. This CSR may have already been submitted.")
        
        form_data = {
            "csr": sample_csr,
            "private_key": sample_private_key,
            "environment": "SANDBOX"
        }
        
        form_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
        
        response = await async_client.post(
            "/api/v1/zatca/compliance/csid/submit",
            headers=form_headers,
            data=form_data
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already been submitted" in data["detail"] or "conflict" in data["detail"].lower()


@pytest.mark.asyncio
async def test_submit_csr_zatca_server_error(
    async_client, headers, test_subscription_trial, sample_csr, sample_private_key
):
    """Test handling of ZATCA server error (500)."""
    with patch('app.integrations.zatca.compliance_csid.ComplianceCSIDService.submit_csr') as mock_submit:
        # Mock 500 server error
        mock_submit.side_effect = ValueError("ZATCA server error. Please try again later.")
        
        form_data = {
            "csr": sample_csr,
            "private_key": sample_private_key,
            "environment": "SANDBOX"
        }
        
        form_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
        
        response = await async_client.post(
            "/api/v1/zatca/compliance/csid/submit",
            headers=form_headers,
            data=form_data
        )
        
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        data = response.json()
        assert "server error" in data["detail"].lower() or "ZATCA" in data["detail"]


@pytest.mark.asyncio
async def test_submit_csr_certificate_storage_failure(
    async_client, headers, test_subscription_trial, sample_csr, sample_private_key, valid_zatca_response
):
    """Test handling of certificate storage failure after successful ZATCA response."""
    with patch('app.integrations.zatca.compliance_csid.ComplianceCSIDService.submit_csr') as mock_submit, \
         patch('app.services.certificate_service.CertificateService.upload_certificate') as mock_upload:
        
        # Mock successful ZATCA response
        mock_submit.return_value = valid_zatca_response
        
        # Mock certificate storage failure
        mock_upload.side_effect = ValueError("Invalid certificate format")
        
        form_data = {
            "csr": sample_csr,
            "private_key": sample_private_key,
            "environment": "SANDBOX"
        }
        
        form_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
        
        response = await async_client.post(
            "/api/v1/zatca/compliance/csid/submit",
            headers=form_headers,
            data=form_data
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "failed to store" in data["detail"].lower()


@pytest.mark.asyncio
async def test_submit_csr_missing_fields(
    async_client, headers, test_subscription_trial
):
    """Test CSR submission with missing required fields."""
    # Missing CSR
    form_data = {
        "private_key": "-----BEGIN PRIVATE KEY-----\nTEST\n-----END PRIVATE KEY-----",
        "environment": "SANDBOX"
    }
    
    form_headers = {k: v for k, v in headers.items() if k.lower() != 'content-type'}
    
    response = await async_client.post(
        "/api/v1/zatca/compliance/csid/submit",
        headers=form_headers,
        data=form_data
    )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_submit_csr_requires_authentication(async_client, sample_csr, sample_private_key):
    """Test that Compliance CSID endpoint requires authentication."""
    form_data = {
        "csr": sample_csr,
        "private_key": sample_private_key,
        "environment": "SANDBOX"
    }
    
    response = await async_client.post(
        "/api/v1/zatca/compliance/csid/submit",
        data=form_data
    )
    
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

