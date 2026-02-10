"""
Tenant seed service for development environment.

Creates default tenant and test API key for local development.
Only runs in local/dev environment.
"""

import logging
import secrets
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.api_key import ApiKey
from app.models.subscription import Plan, Subscription, SubscriptionStatus
from app.core.constants import Environment
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def seed_default_tenant(db: Session) -> tuple[Tenant, ApiKey]:
    """
    Seeds default tenant and API key for development.
    
    Creates:
    - Default tenant: "Demo Tenant", VAT: "000000000000003", environment: "SANDBOX"
    - Default API key: "test-key" (if not exists)
    
    Args:
        db: Database session
        
    Returns:
        Tuple of (Tenant, ApiKey)
        
    Raises:
        Exception: If seeding fails
    """
    # Check if default tenant already exists
    existing_tenant = db.query(Tenant).filter(
        Tenant.vat_number == "000000000000003"
    ).first()
    
    if existing_tenant:
        logger.info(f"Default tenant already exists: {existing_tenant.company_name}")
        tenant = existing_tenant
    else:
        # Create default tenant
        tenant = Tenant(
            company_name="Demo Tenant",
            vat_number="000000000000003",
            environment=Environment.SANDBOX.value,
            is_active=True
        )
        db.add(tenant)
        db.flush()  # Flush to get tenant.id
        logger.info(f"Created default tenant: {tenant.company_name} (ID: {tenant.id})")
    
    # Check if test API key already exists
    existing_api_key = db.query(ApiKey).filter(
        ApiKey.api_key == "test-key"
    ).first()
    
    if existing_api_key:
        logger.info("Test API key 'test-key' already exists")
        api_key = existing_api_key
    else:
        # Create test API key
        api_key = ApiKey(
            api_key="test-key",
            tenant_id=tenant.id,
            is_active=True
        )
        db.add(api_key)
        logger.info(f"Created test API key 'test-key' for tenant {tenant.id}")
    
    db.commit()
    return tenant, api_key


def ensure_default_tenant_subscription(db: Session, tenant: Tenant) -> None:
    """
    Ensures the default (seeded) tenant has an active subscription for local/dev.
    If subscription is missing, creates a Trial with long expiry. If EXPIRED/SUSPENDED, sets ACTIVE.
    """
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == tenant.id
    ).first()

    if not subscription:
        trial_plan = db.query(Plan).filter(Plan.name == "Trial").first()
        if not trial_plan:
            trial_plan = db.query(Plan).filter(Plan.name == "Free Sandbox").first()
        if trial_plan:
            trial_ends_at = datetime.utcnow() + timedelta(days=365)
            sub = Subscription(
                tenant_id=tenant.id,
                plan_id=trial_plan.id,
                status=SubscriptionStatus.TRIAL,
                trial_starts_at=datetime.utcnow(),
                trial_ends_at=trial_ends_at,
            )
            db.add(sub)
            db.commit()
            logger.info(f"Created subscription for default tenant {tenant.id} (Trial until {trial_ends_at.date()})")
        return
    if subscription.status in (SubscriptionStatus.EXPIRED, SubscriptionStatus.SUSPENDED):
        old_status = subscription.status
        subscription.status = SubscriptionStatus.ACTIVE
        db.commit()
        logger.info(f"Reactivated subscription for default tenant {tenant.id} (was {old_status})")


def seed_tenants_if_needed(db: Session, environment: str) -> None:
    """
    Seeds default tenant and API key if in local/dev environment.
    Also ensures the default tenant has an active subscription so Swagger/local testing works.
    
    Args:
        db: Database session
        environment: Current environment (local, dev, production, etc.)
    """
    # Only seed in local/dev environments
    if environment.lower() not in ("local", "dev", "development"):
        logger.info(f"Skipping tenant seeding - not in local/dev environment (current: {environment})")
        return

    try:
        logger.info("Starting tenant seeding for local/dev environment...")
        tenant, api_key = seed_default_tenant(db)
        ensure_default_tenant_subscription(db, tenant)
        logger.info(
            f"Tenant seeding completed successfully. "
            f"Tenant: {tenant.company_name} (ID: {tenant.id}), "
            f"API Key: {api_key.api_key}"
        )
    except Exception as e:
        logger.error(f"Failed to seed default tenant: {e}")
        db.rollback()
        raise

