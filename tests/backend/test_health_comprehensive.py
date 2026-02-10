"""
Comprehensive tests for health endpoints.

Tests both /api/v1/health and /api/v1/system/health endpoints.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    """Test basic health endpoint returns 200."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_system_health_endpoint(async_client, mock_httpx_client):
    """Test system health endpoint returns comprehensive status."""
    with patch('app.api.v1.routes.system.get_settings') as mock_settings:
        mock_settings.return_value.zatca_environment = "SANDBOX"
        mock_settings.return_value.zatca_sandbox_base_url = "https://test.zatca.gov.sa"
        mock_settings.return_value.zatca_production_base_url = "https://prod.zatca.gov.sa"
        mock_settings.return_value.enable_ai_explanation = True
        mock_settings.return_value.openrouter_api_key = "test-key"
        mock_settings.return_value.app_version = "1.0.0"
        mock_settings.return_value.environment_name = "test"
        
        # Mock application start time
        with patch('app.api.v1.routes.system._application_start_time', 1000.0):
            with patch('time.time', return_value=2000.0):
                response = await async_client.get("/api/v1/system/health")
                
                assert response.status_code == 200
                data = response.json()
                
                # Check structure
                assert "environment" in data
                assert "zatca" in data
                assert "ai" in data
                assert "system" in data
                assert "timestamp" in data
                
                # Check ZATCA status
                assert "status" in data["zatca"]
                assert "environment" in data["zatca"]
                assert "last_checked" in data["zatca"]
                
                # Check AI status
                assert "status" in data["ai"]
                assert "provider" in data["ai"]
                
                # Check system status
                assert "uptime_seconds" in data["system"]
                assert "version" in data["system"]
                assert data["system"]["uptime_seconds"] == 1000


@pytest.mark.asyncio
async def test_system_health_zatca_disconnected(async_client):
    """Test system health when ZATCA is disconnected."""
    with patch('app.api.v1.routes.system.get_settings') as mock_settings, \
         patch('httpx.AsyncClient') as mock_client:
        
        mock_settings.return_value.zatca_environment = "SANDBOX"
        mock_settings.return_value.zatca_sandbox_base_url = "https://test.zatca.gov.sa"
        mock_settings.return_value.enable_ai_explanation = False
        mock_settings.return_value.app_version = "1.0.0"
        mock_settings.return_value.environment_name = "test"
        
        # Mock timeout exception
        import httpx
        mock_instance = AsyncMock()
        mock_instance.head = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.api.v1.routes.system._application_start_time', 1000.0):
            with patch('time.time', return_value=2000.0):
                response = await async_client.get("/api/v1/system/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["zatca"]["status"] == "DISCONNECTED"
                assert data["ai"]["status"] == "DISABLED"


@pytest.mark.asyncio
async def test_system_health_ai_error(async_client):
    """Test system health when AI provider has error."""
    with patch('app.api.v1.routes.system.get_settings') as mock_settings, \
         patch('app.api.v1.routes.system.get_openrouter_service') as mock_openrouter:
        
        mock_settings.return_value.zatca_environment = "SANDBOX"
        mock_settings.return_value.zatca_sandbox_base_url = "https://test.zatca.gov.sa"
        mock_settings.return_value.enable_ai_explanation = True
        mock_settings.return_value.openrouter_api_key = None  # Missing key
        mock_settings.return_value.app_version = "1.0.0"
        mock_settings.return_value.environment_name = "test"
        
        # Mock ZATCA success
        import httpx
        mock_zatca_client = AsyncMock()
        mock_zatca_response = MagicMock()
        mock_zatca_response.status_code = 200
        mock_zatca_client.head = AsyncMock(return_value=mock_zatca_response)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_zatca_client)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            
            with patch('app.api.v1.routes.system._application_start_time', 1000.0):
                with patch('time.time', return_value=2000.0):
                    response = await async_client.get("/api/v1/system/health")
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["ai"]["status"] == "ERROR"
                    assert "error_message" in data["ai"]

