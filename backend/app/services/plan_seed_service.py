"""
Plan seed service for initializing default subscription plans.

Creates Free Sandbox, Trial, and paid plans (Starter, Pro, Enterprise).
Only runs in local/dev environment or on first deployment.
"""

import logging
from sqlalchemy.orm import Session

from app.models.subscription import Plan

logger = logging.getLogger(__name__)


def seed_default_plans(db: Session) -> None:
    """
    Seeds default subscription plans.
    
    Creates:
    - Free Sandbox: Limited forever plan
    - Trial: 7-day trial plan (auto-assigned on signup)
    - Starter: Basic paid plan
    - Pro: Advanced paid plan
    - Enterprise: Custom limits plan
    """
    plans_data = [
        {
            "name": "Free Sandbox",
            "monthly_invoice_limit": 10,
            "monthly_ai_limit": 5,
            "rate_limit_per_minute": 10,
            "features": {
                "phase1": True,
                "phase2": False,
                "ai_explanations": False,
                "production_access": False
            }
        },
        {
            "name": "Trial",
            "monthly_invoice_limit": 50,
            "monthly_ai_limit": 20,
            "rate_limit_per_minute": 30,
            "features": {
                "phase1": True,
                "phase2": True,
                "ai_explanations": True,
                "production_access": False
            }
        },
        {
            "name": "Starter",
            "monthly_invoice_limit": 500,
            "monthly_ai_limit": 100,
            "rate_limit_per_minute": 60,
            "features": {
                "phase1": True,
                "phase2": True,
                "ai_explanations": True,
                "production_access": True
            }
        },
        {
            "name": "Pro",
            "monthly_invoice_limit": 5000,
            "monthly_ai_limit": 1000,
            "rate_limit_per_minute": 120,
            "features": {
                "phase1": True,
                "phase2": True,
                "ai_explanations": True,
                "production_access": True,
                "priority_support": True
            }
        },
        {
            "name": "Enterprise",
            "monthly_invoice_limit": 0,  # Unlimited
            "monthly_ai_limit": 0,  # Unlimited
            "rate_limit_per_minute": 300,
            "features": {
                "phase1": True,
                "phase2": True,
                "ai_explanations": True,
                "production_access": True,
                "priority_support": True,
                "custom_limits": True,
                "dedicated_support": True
            }
        }
    ]
    
    for plan_data in plans_data:
        existing = db.query(Plan).filter(Plan.name == plan_data["name"]).first()
        if not existing:
            plan = Plan(**plan_data)
            db.add(plan)
            logger.info(f"Created plan: {plan_data['name']}")
        else:
            logger.debug(f"Plan already exists: {plan_data['name']}")
    
    db.commit()
    logger.info("Plan seeding completed")


def seed_plans_if_needed(db: Session, environment: str) -> None:
    """
    Seeds default plans if in local/dev environment or if no plans exist.
    
    Args:
        db: Database session
        environment: Current environment (local, dev, production, etc.)
    """
    # Check if plans already exist
    plan_count = db.query(Plan).count()
    
    if plan_count > 0:
        logger.info(f"Plans already exist ({plan_count}). Skipping seed.")
        return
    
    # Seed plans if none exist (first deployment)
    try:
        logger.info("No plans found. Seeding default plans...")
        seed_default_plans(db)
        logger.info("Plan seeding completed successfully.")
    except Exception as e:
        logger.error(f"Failed to seed default plans: {e}")
        db.rollback()
        raise

