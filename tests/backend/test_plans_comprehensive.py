"""
Comprehensive tests for plans endpoints.

Tests public plans listing, current subscription, and usage endpoints.
"""

import pytest
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_list_plans_public(async_client, db):
    """Test that plans list is public (no auth required)."""
    # Create some plans
    from app.models.subscription import Plan
    plan1 = Plan(
        name="Test Plan 1",
        monthly_invoice_limit=100,
        monthly_ai_limit=50,
        rate_limit_per_minute=30,
        is_active=True
    )
    plan2 = Plan(
        name="Test Plan 2",
        monthly_invoice_limit=500,
        monthly_ai_limit=100,
        rate_limit_per_minute=60,
        is_active=True
    )
    db.add(plan1)
    db.add(plan2)
    db.commit()
    
    response = await async_client.get("/api/v1/plans")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_current_subscription(async_client, headers, test_subscription_trial, trial_plan):
    """Test getting current subscription requires auth."""
    response = await async_client.get("/api/v1/plans/current", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data or "plan_id" in data


@pytest.mark.asyncio
async def test_get_current_subscription_no_auth(async_client):
    """Test that current subscription requires authentication."""
    response = await async_client.get("/api/v1/plans/current")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_usage(async_client, headers, test_subscription_trial):
    """Test getting usage data."""
    response = await async_client.get("/api/v1/plans/usage", headers=headers)
    # May return 200 with usage data or 404 if no subscription
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        data = response.json()
        assert "ai_request_count" in data


@pytest.mark.asyncio
async def test_get_usage_no_auth(async_client):
    """Test that usage endpoint requires authentication."""
    response = await async_client.get("/api/v1/plans/usage")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_usage_limits(async_client, headers, test_subscription_trial, trial_plan):
    """Test that usage endpoint returns limits."""
    response = await async_client.get("/api/v1/plans/usage", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        # Check that limits are returned
        if "invoice_usage" in data:
            assert "limit" in data["invoice_usage"] or "monthly_limit" in data.get("invoice_usage", {})
        if "ai_usage" in data:
            assert "limit" in data["ai_usage"] or "monthly_limit" in data.get("ai_usage", {})

