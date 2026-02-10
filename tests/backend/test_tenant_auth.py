"""
Tests for tenant authentication and resolution.

Validates API key authentication and tenant context resolution.
"""


def test_tenant_resolution(client, headers):
    """Test that tenant information is correctly resolved from API key."""
    res = client.get("/api/v1/tenants/me", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "company_name" in data
    assert "vat_number" in data
    assert "environment" in data
    assert data["company_name"] in ["Test Company", "Demo Tenant"]
    assert data["vat_number"] in ["123456789012345", "000000000000003"]


def test_invalid_api_key(client):
    """Test that invalid API key is rejected."""
    res = client.get(
        "/api/v1/tenants/me",
        headers={"X-API-Key": "invalid-key"}
    )
    assert res.status_code in (401, 403)


def test_missing_api_key(client):
    """Test that missing API key is rejected."""
    res = client.get("/api/v1/tenants/me")
    assert res.status_code == 401


def test_inactive_api_key(client, db, test_tenant):
    """Test that inactive API key is rejected."""
    from app.models.api_key import ApiKey
    
    # Get-or-create inactive API key (UNIQUE constraint: api_key)
    inactive_key = db.query(ApiKey).filter(
        ApiKey.api_key == "inactive-key"
    ).first()
    if not inactive_key:
        inactive_key = ApiKey(
            api_key="inactive-key",
            tenant_id=test_tenant.id,
            is_active=False
        )
        db.add(inactive_key)
        db.commit()
        db.refresh(inactive_key)
    else:
        # Update existing key to be inactive
        inactive_key.is_active = False
        db.commit()
    
    res = client.get(
        "/api/v1/tenants/me",
        headers={"X-API-Key": "inactive-key"}
    )
    assert res.status_code in (401, 403)

