"""
Integration tests for ZATCA sandbox connectivity.

Tests the /api/v1/zatca/status endpoint with real connectivity checks.
All tests use mocked ZATCA API responses - no real API calls.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from datetime import datetime

from app.integrations.zatca.sandbox import ZATCASandboxClient
from app.integrations.zatca.oauth_service import ZatcaAccessToken


@pytest.fixture
def mock_oauth_service():
    """Mock OAuth service that returns valid tokens."""
    service = MagicMock()
    token = ZatcaAccessToken(
        access_token="test_token",
        token_type="Bearer",
        expires_in=3600
    )
    service.get_access_token = AsyncMock(return_value=token)
    return service


@pytest.fixture
def sandbox_client(mock_oauth_service):
    """Create sandbox client with mocked OAuth service."""
    client = ZATCASandboxClient()
    client.oauth_service = mock_oauth_service
    return client


@pytest.mark.asyncio
async def test_ping_success(sandbox_client):
    """Test successful ZATCA sandbox ping."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance
        
        # Perform ping
        result = await sandbox_client.ping()
        
        # Verify result
        assert result["connected"] is True
        assert result["error_message"] is None
        assert result["last_successful_ping"] is not None
        
        # Verify request was made with OAuth header
        mock_client_instance.get.assert_called_once()
        call_args = mock_client_instance.get.call_args
        assert "Authorization" in call_args[1]["headers"]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_token"


@pytest.mark.asyncio
async def test_ping_401_authentication_failed(sandbox_client):
    """Test ping when authentication fails (401)."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized",
            request=MagicMock(),
            response=mock_response
        )
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get = AsyncMock(side_effect=mock_response.raise_for_status.side_effect)
        mock_client.return_value = mock_client_instance
        
        # Perform ping
        result = await sandbox_client.ping()
        
        # Verify result
        assert result["connected"] is False
        assert result["error_message"] is not None
        assert "authentication" in result["error_message"].lower() or "401" in result["error_message"]
        assert result["last_successful_ping"] is None


@pytest.mark.asyncio
async def test_ping_timeout(sandbox_client):
    """Test ping when request times out."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock timeout
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
        mock_client.return_value = mock_client_instance
        
        # Perform ping
        result = await sandbox_client.ping()
        
        # Verify result
        assert result["connected"] is False
        assert result["error_message"] is not None
        assert "timeout" in result["error_message"].lower()
        assert result["last_successful_ping"] is None


@pytest.mark.asyncio
async def test_ping_404_status_endpoint_not_found(sandbox_client):
    """Test ping when status endpoint doesn't exist (404) - should still be considered connected if auth works."""
    with patch('httpx.AsyncClient') as mock_client:
        # Mock 404 response (endpoint doesn't exist, but auth worked)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response
        )
        
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.get = AsyncMock(side_effect=mock_response.raise_for_status.side_effect)
        mock_client.return_value = mock_client_instance
        
        # Perform ping
        result = await sandbox_client.ping()
        
        # Should be considered connected (auth worked, endpoint just doesn't exist)
        assert result["connected"] is True
        assert result["last_successful_ping"] is not None


@pytest.mark.asyncio
async def test_ping_oauth_credentials_missing():
    """Test ping when OAuth credentials are not configured."""
    client = ZATCASandboxClient()
    # Mock OAuth service to raise ValueError (credentials missing)
    client.oauth_service = MagicMock()
    client.oauth_service.get_access_token = AsyncMock(
        side_effect=ValueError("OAuth credentials not configured")
    )
    
    # Perform ping
    result = await client.ping()
    
    # Verify result
    assert result["connected"] is False
    assert result["error_message"] is not None
    assert "credentials" in result["error_message"].lower() or "configured" in result["error_message"].lower()
    assert result["last_successful_ping"] is None


@pytest.mark.asyncio
async def test_status_endpoint_with_real_connectivity(async_client, headers, test_subscription_trial):
    """Test /api/v1/zatca/status endpoint with mocked connectivity check."""
    with patch('app.integrations.zatca.factory.get_zatca_client') as mock_get_client:
        # Mock ZATCA client with ping method
        mock_client = MagicMock()
        mock_ping_result = {
            "connected": True,
            "error_message": None,
            "last_successful_ping": datetime.utcnow().isoformat()
        }
        mock_client.ping = AsyncMock(return_value=mock_ping_result)
        mock_get_client.return_value = mock_client
        
        # Call status endpoint
        response = await async_client.get(
            "/api/v1/zatca/status",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "connected" in data
        assert "environment" in data
        assert "connectivity" in data
        
        # Verify connectivity information
        connectivity = data["connectivity"]
        assert "has_certificate" in connectivity
        assert "real_connectivity" in connectivity
        assert connectivity["real_connectivity"] is True
        assert "last_successful_ping" in connectivity


@pytest.mark.asyncio
async def test_status_endpoint_connectivity_failed(async_client, headers, test_subscription_trial):
    """Test /api/v1/zatca/status endpoint when connectivity check fails."""
    with patch('app.integrations.zatca.factory.get_zatca_client') as mock_get_client:
        # Mock ZATCA client with failed ping
        mock_client = MagicMock()
        mock_ping_result = {
            "connected": False,
            "error_message": "OAuth authentication failed",
            "last_successful_ping": None
        }
        mock_client.ping = AsyncMock(return_value=mock_ping_result)
        mock_get_client.return_value = mock_client
        
        # Call status endpoint
        response = await async_client.get(
            "/api/v1/zatca/status",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify connectivity shows failure
        connectivity = data["connectivity"]
        assert connectivity["real_connectivity"] is False
        assert connectivity["error_message"] is not None
        # Overall connected should be False if connectivity failed
        assert data["connected"] is False

