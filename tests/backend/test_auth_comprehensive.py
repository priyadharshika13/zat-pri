"""
Comprehensive tests for authentication.

Tests API key validation, missing keys, invalid keys, and access control.
"""

import pytest


@pytest.mark.asyncio
async def test_missing_api_key(async_client):
    """Test that missing X-API-Key returns 401."""
    response = await async_client.get("/api/v1/plans/usage")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_invalid_api_key(async_client):
    """Test that invalid X-API-Key returns 401."""
    headers = {
        "X-API-Key": "invalid-key-12345",
        "Content-Type": "application/json"
    }
    response = await async_client.get("/api/v1/plans/usage", headers=headers)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_valid_api_key(async_client, headers, test_subscription_trial):
    """Test that valid API key allows access."""
    response = await async_client.get("/api/v1/plans/usage", headers=headers)
    # Should return 200 or 404 (if no usage data), but not 401
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_api_key_case_sensitive(async_client, test_api_key):
    """Test that API key is case-sensitive."""
    # Use wrong case
    headers = {
        "X-API-Key": test_api_key.api_key.upper(),  # Wrong case
        "Content-Type": "application/json"
    }
    response = await async_client.get("/api/v1/plans/usage", headers=headers)
    # Should fail if case-sensitive
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_inactive_api_key(async_client, db, test_tenant):
    """Test that inactive API key returns 401."""
    # Create inactive API key
    from app.models.api_key import ApiKey
    inactive_key = ApiKey(
        api_key="inactive-key",
        tenant_id=test_tenant.id,
        is_active=False
    )
    db.add(inactive_key)
    db.commit()
    
    headers = {
        "X-API-Key": "inactive-key",
        "Content-Type": "application/json"
    }
    response = await async_client.get("/api/v1/plans/usage", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_public_endpoint_no_auth(async_client):
    """Test that public endpoints don't require authentication."""
    # Health endpoint is public
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    
    # System health is public
    response = await async_client.get("/api/v1/system/health")
    assert response.status_code == 200
    
    # Plans list is public
    response = await async_client.get("/api/v1/plans")
    assert response.status_code == 200

