"""
Tests for subscription limit enforcement.

Validates that subscription limits are properly enforced for AI and invoice endpoints.
"""

import pytest
from datetime import datetime


def test_subscription_limit_enforced_ai(client, headers, db, test_tenant, test_plan, monkeypatch):
    """Test that AI subscription limits are enforced."""
    from app.models.subscription import Subscription, SubscriptionStatus, UsageCounter
    from datetime import datetime
    
    # Enable AI for testing
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "true")
    
    # Get-or-update subscription (tenant already has one from fixture)
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == test_tenant.id
    ).first()
    if subscription:
        # Update existing subscription to use test_plan
        subscription.plan_id = test_plan.id
        subscription.status = SubscriptionStatus.ACTIVE
    else:
        # Create new subscription if none exists
        subscription = Subscription(
            tenant_id=test_tenant.id,
            plan_id=test_plan.id,
            status=SubscriptionStatus.ACTIVE
        )
        db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    # Create usage counter and set it to the limit
    current_period = datetime.utcnow().strftime("%Y-%m")
    counter = UsageCounter(
        tenant_id=test_tenant.id,
        subscription_id=subscription.id,
        billing_period=current_period,
        ai_request_count=test_plan.monthly_ai_limit  # At the limit
    )
    db.add(counter)
    db.commit()
    
    # Try to make an AI request - should be blocked
    res = client.get(
        "/api/v1/ai/readiness-score",
        headers=headers
    )
    # Should return 403 (Forbidden) when limit exceeded
    assert res.status_code in (403, 429)


def test_subscription_limit_not_exceeded(client, headers, db, test_tenant, test_plan, monkeypatch):
    """Test that requests work when limit is not exceeded."""
    from app.models.subscription import Subscription, SubscriptionStatus, UsageCounter
    from datetime import datetime
    
    # Enable AI for testing
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "true")
    
    # Get-or-update subscription (tenant already has one from fixture)
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == test_tenant.id
    ).first()
    if subscription:
        # Update existing subscription to use test_plan
        subscription.plan_id = test_plan.id
        subscription.status = SubscriptionStatus.ACTIVE
    else:
        # Create new subscription if none exists
        subscription = Subscription(
            tenant_id=test_tenant.id,
            plan_id=test_plan.id,
            status=SubscriptionStatus.ACTIVE
        )
        db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    # Create usage counter below limit
    current_period = datetime.utcnow().strftime("%Y-%m")
    counter = UsageCounter(
        tenant_id=test_tenant.id,
        subscription_id=subscription.id,
        billing_period=current_period,
        ai_request_count=0  # Well below limit
    )
    db.add(counter)
    db.commit()
    
    # Make an AI request - should succeed
    res = client.get(
        "/api/v1/ai/readiness-score",
        headers=headers
    )
    # Should return 200 (may be UNKNOWN if OpenAI not configured, but not 403)
    assert res.status_code == 200


def test_invoice_limit_enforced(client, headers, db, test_tenant, test_plan):
    """Test that invoice subscription limits are enforced."""
    from app.models.subscription import Subscription, SubscriptionStatus, UsageCounter
    from datetime import datetime
    
    # Get-or-update subscription (tenant already has one from fixture)
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == test_tenant.id
    ).first()
    if subscription:
        # Update existing subscription to use test_plan
        subscription.plan_id = test_plan.id
        subscription.status = SubscriptionStatus.ACTIVE
    else:
        # Create new subscription if none exists
        subscription = Subscription(
            tenant_id=test_tenant.id,
            plan_id=test_plan.id,
            status=SubscriptionStatus.ACTIVE
        )
        db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    # Create usage counter at the limit
    current_period = datetime.utcnow().strftime("%Y-%m")
    counter = UsageCounter(
        tenant_id=test_tenant.id,
        subscription_id=subscription.id,
        billing_period=current_period,
        invoice_count=test_plan.monthly_invoice_limit  # At the limit
    )
    db.add(counter)
    db.commit()
    
    # Try to submit an invoice - should be blocked
    payload = {
        "mode": "PHASE_1",
        "environment": "SANDBOX",
        "invoice_number": "INV-LIMIT-TEST",
        "invoice_date": datetime.now().isoformat(),
        "seller_name": "Test Seller",
        "seller_tax_number": "123456789012345",
        "line_items": [
            {
                "name": "Test Item",
                "quantity": 1.0,
                "unit_price": 100.0,
                "tax_rate": 15.0,
                "tax_category": "S"
            }
        ],
        "total_tax_exclusive": 100.0,
        "total_tax_amount": 15.0,
        "total_amount": 115.0
    }
    
    res = client.post("/api/v1/invoices", json=payload, headers=headers)
    # Should return 403 or 429 when limit exceeded
    assert res.status_code in (403, 429)


def test_unlimited_subscription_allows_requests(client, headers, db, test_tenant, monkeypatch):
    """Test that unlimited subscriptions (limit=0) allow all requests."""
    from app.models.subscription import Plan, Subscription, SubscriptionStatus, UsageCounter
    from datetime import datetime
    
    # Enable AI for testing
    monkeypatch.setenv("ENABLE_AI_EXPLANATION", "true")
    
    # Clean up existing usage counters for this tenant to ensure test isolation
    db.query(UsageCounter).filter(UsageCounter.tenant_id == test_tenant.id).delete()
    db.commit()
    
    # Get-or-create plan with unlimited AI (limit=0)
    unlimited_plan = db.query(Plan).filter(Plan.name == "Unlimited Plan").first()
    if not unlimited_plan:
        unlimited_plan = Plan(
            name="Unlimited Plan",
            monthly_invoice_limit=0,  # Unlimited
            monthly_ai_limit=0,  # Unlimited
            rate_limit_per_minute=60,
            is_active=True
        )
        db.add(unlimited_plan)
        db.commit()
        db.refresh(unlimited_plan)
    
    # Get-or-update subscription (tenant already has one from fixture)
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == test_tenant.id
    ).first()
    if subscription:
        # Update existing subscription to use unlimited_plan
        subscription.plan_id = unlimited_plan.id
        subscription.status = SubscriptionStatus.ACTIVE
    else:
        # Create new subscription if none exists
        subscription = Subscription(
            tenant_id=test_tenant.id,
            plan_id=unlimited_plan.id,
            status=SubscriptionStatus.ACTIVE
        )
        db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    # Create usage counter with high usage
    current_period = datetime.utcnow().strftime("%Y-%m")
    counter = UsageCounter(
        tenant_id=test_tenant.id,
        subscription_id=subscription.id,
        billing_period=current_period,
        ai_request_count=1000  # High usage, but should still work
    )
    db.add(counter)
    db.commit()
    
    # Make an AI request - should succeed (unlimited)
    res = client.get(
        "/api/v1/ai/readiness-score",
        headers=headers
    )
    assert res.status_code == 200

