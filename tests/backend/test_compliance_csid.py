"""
Tests for ZATCA Compliance CSID API integration.

Tests CSR submission to ZATCA Compliance CSID API, certificate retrieval,
and automatic certificate storage. All tests use mocked HTTP responses.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi import status

from app.integrations.zatca.compliance_csid import ComplianceCSIDService
from app.integrations.zatca.oauth_service import ZatcaAccessToken


@pytest.fixture
def mock_settings():
    """Mock settings with OAuth credentials."""
    settings = MagicMock()
    settings.zatca_sandbox_base_url = "https://test-sandbox.zatca.gov.sa/e-invoicing/developer-portal"
    settings.zatca_oauth_timeout = 10.0
    return settings


@pytest.fixture
def mock_oauth_service():
    """Mock OAuth service that returns valid tokens."""
    service = MagicMock()
    token = ZatcaAccessToken(
        access_token="test_access_token_12345",
        token_type="Bearer",
        expires_in=3600
    )
    service.get_access_token = AsyncMock(return_value=token)
    return service


@pytest.fixture
def compliance_csid_service(mock_settings, mock_oauth_service):
    """Create Compliance CSID service with mocked dependencies."""
    with patch('app.integrations.zatca.compliance_csid.get_settings', return_value=mock_settings), \
         patch('app.integrations.zatca.compliance_csid.get_oauth_service', return_value=mock_oauth_service):
        service = ComplianceCSIDService(environment="SANDBOX")
        return service


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
async def test_submit_csr_success(compliance_csid_service, sample_csr, valid_zatca_response):
    """Test successful CSR submission to ZATCA Compliance CSID API."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = valid_zatca_response
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance
        
        # Submit CSR
        result = await compliance_csid_service.submit_csr(csr_pem=sample_csr)
        
        # Verify result
        assert result["requestID"] == "12345678-1234-1234-1234-123456789012"
        assert result["dispositionMessage"] == "Certificate issued successfully"
        assert result["secret"] == "base64-encoded-secret-value"
        assert "-----BEGIN CERTIFICATE-----" in result["binarySecurityToken"]
        assert "-----END CERTIFICATE-----" in result["binarySecurityToken"]
        
        # Verify request was made correctly
        mock_client_instance.post.assert_called_once()
        call_args = mock_client_instance.post.call_args
        assert "/compliance/csid" in call_args[0][0]
        assert "Authorization" in call_args[1]["headers"]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_access_token_12345"
        assert call_args[1]["headers"]["Content-Type"] == "application/json"
        assert call_args[1]["json"]["csr"] == sample_csr.strip()


@pytest.mark.asyncio
async def test_submit_csr_invalid_format(compliance_csid_service):
    """Test CSR submission with invalid format."""
    invalid_csr = "This is not a valid CSR"
    
    with pytest.raises(ValueError) as exc_info:
        await compliance_csid_service.submit_csr(csr_pem=invalid_csr)
    
    assert "Invalid CSR format" in str(exc_info.value)


@pytest.mark.asyncio
async def test_submit_csr_empty(compliance_csid_service):
    """Test CSR submission with empty CSR."""
    with pytest.raises(ValueError) as exc_info:
        await compliance_csid_service.submit_csr(csr_pem="")
    
    assert "CSR cannot be empty" in str(exc_info.value)


@pytest.mark.asyncio
async def test_submit_csr_400_bad_request(compliance_csid_service, sample_csr):
    """Test handling of 400 Bad Request from ZATCA."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock 400 response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "message": "Invalid CSR format",
            "error": "CSR validation failed"
        }
        mock_response.text = '{"message": "Invalid CSR format"}'
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance
        
        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await compliance_csid_service.submit_csr(csr_pem=sample_csr)
        
        assert "Invalid CSR or request format" in str(exc_info.value)
        assert "Invalid CSR format" in str(exc_info.value)


@pytest.mark.asyncio
async def test_submit_csr_401_unauthorized(compliance_csid_service, sample_csr, mock_oauth_service):
    """Test handling of 401 Unauthorized with automatic token refresh."""
    call_count = 0
    
    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_response = MagicMock()
        mock_response.status_code = 401 if call_count == 1 else 200
        mock_response.headers = {"content-type": "application/json"}
        
        if call_count == 1:
            # First call: 401
            mock_response.text = "Unauthorized"
            return mock_response
        else:
            # Second call: Success
            mock_response.json.return_value = {
                "requestID": "12345678-1234-1234-1234-123456789012",
                "dispositionMessage": "Certificate issued successfully",
                "secret": "secret",
                "binarySecurityToken": "-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"
            }
            mock_response.raise_for_status = MagicMock()
            return mock_response
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post = AsyncMock(side_effect=mock_post)
        mock_client.return_value = mock_client_instance
        
        # Should refresh token and retry
        result = await compliance_csid_service.submit_csr(csr_pem=sample_csr, retry_on_401=True)
        
        # Verify token refresh was called
        assert mock_oauth_service.get_access_token.call_count >= 1
        assert result["requestID"] == "12345678-1234-1234-1234-123456789012"


@pytest.mark.asyncio
async def test_submit_csr_409_conflict(compliance_csid_service, sample_csr):
    """Test handling of 409 Conflict (CSR already submitted)."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock 409 response
        mock_response = MagicMock()
        mock_response.status_code = 409
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "message": "CSR already submitted",
            "error": "Duplicate request"
        }
        mock_response.text = '{"message": "CSR already submitted"}'
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance
        
        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await compliance_csid_service.submit_csr(csr_pem=sample_csr)
        
        assert "CSR submission conflict" in str(exc_info.value)
        assert "already been submitted" in str(exc_info.value)


@pytest.mark.asyncio
async def test_submit_csr_500_server_error(compliance_csid_service, sample_csr):
    """Test handling of 500 Internal Server Error from ZATCA."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock 500 response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "message": "Internal server error",
            "error": "ZATCA service temporarily unavailable"
        }
        mock_response.text = '{"message": "Internal server error"}'
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance
        
        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await compliance_csid_service.submit_csr(csr_pem=sample_csr)
        
        assert "ZATCA server error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_submit_csr_timeout(compliance_csid_service, sample_csr):
    """Test handling of network timeout."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock timeout exception
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
        mock_client.return_value = mock_client_instance
        
        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await compliance_csid_service.submit_csr(csr_pem=sample_csr)
        
        assert "timed out" in str(exc_info.value).lower() or "timeout" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_submit_csr_invalid_response_missing_fields(compliance_csid_service, sample_csr):
    """Test handling of invalid ZATCA response (missing required fields)."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock response missing binarySecurityToken
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "requestID": "12345678-1234-1234-1234-123456789012",
            "dispositionMessage": "Success"
            # Missing binarySecurityToken
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance
        
        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await compliance_csid_service.submit_csr(csr_pem=sample_csr)
        
        assert "missing required fields" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_submit_csr_invalid_certificate_format(compliance_csid_service, sample_csr):
    """Test handling of invalid certificate format in response."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock response with invalid certificate
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "requestID": "12345678-1234-1234-1234-123456789012",
            "dispositionMessage": "Success",
            "binarySecurityToken": "Invalid certificate format"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance
        
        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await compliance_csid_service.submit_csr(csr_pem=sample_csr)
        
        assert "Invalid certificate format" in str(exc_info.value)


@pytest.mark.asyncio
async def test_submit_csr_oauth_failure(compliance_csid_service, sample_csr, mock_oauth_service):
    """Test handling of OAuth authentication failure."""
    # Make OAuth service raise error
    mock_oauth_service.get_access_token = AsyncMock(side_effect=ValueError("OAuth credentials not configured"))
    
    # Should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        await compliance_csid_service.submit_csr(csr_pem=sample_csr)
    
    assert "OAuth authentication failed" in str(exc_info.value)


def test_prepare_csr_for_submission(compliance_csid_service, sample_csr):
    """Test CSR preparation for submission."""
    prepared = compliance_csid_service._prepare_csr_for_submission(sample_csr)
    
    # Should clean whitespace but preserve structure
    assert "-----BEGIN CERTIFICATE REQUEST-----" in prepared
    assert "-----END CERTIFICATE REQUEST-----" in prepared
    assert prepared == sample_csr.strip()


def test_compliance_csid_service_initialization():
    """Test Compliance CSID service initialization."""
    with patch('app.integrations.zatca.compliance_csid.get_settings') as mock_settings, \
         patch('app.integrations.zatca.compliance_csid.get_oauth_service') as mock_oauth:
        mock_settings.return_value.zatca_sandbox_base_url = "https://test.com"
        mock_oauth.return_value = MagicMock()
        
        service = ComplianceCSIDService(environment="SANDBOX")
        assert service.environment == "SANDBOX"
        assert service.compliance_csid_endpoint == "/compliance/csid"
        
        # Test invalid environment
        with pytest.raises(ValueError):
            ComplianceCSIDService(environment="INVALID")

