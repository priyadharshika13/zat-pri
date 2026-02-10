"""
Subscription enforcement service.

Centralized service for subscription management and limit enforcement.
All plan-specific logic is contained here - controllers must not contain plan checks.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.subscription import Plan, Subscription, UsageCounter, SubscriptionStatus
from app.schemas.subscription import LimitExceededError
from app.schemas.auth import TenantContext

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Centralized subscription enforcement service.
    
    CRITICAL: All plan-specific logic is contained here.
    Controllers must NOT contain plan checks - they must use this service.
    """
    
    def __init__(self, db: Session, tenant_context: TenantContext):
        """
        Initializes subscription service.
        
        Args:
            db: Database session
            tenant_context: Tenant context from request
        """
        self.db = db
        self.tenant_context = tenant_context
    
    def get_current_subscription(self) -> Optional[Subscription]:
        """
        Gets the current tenant's subscription.
        
        Auto-assigns Trial subscription if tenant has no subscription.
        
        Returns:
            Subscription instance or None if not found
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.tenant_id == self.tenant_context.tenant_id
        ).first()
        
        if not subscription:
            # Auto-assign Trial subscription to new tenant
            subscription = self._auto_assign_trial()
        
        if subscription:
            # Check trial expiry and auto-downgrade if needed
            subscription = self._check_and_handle_trial_expiry(subscription)
        
        return subscription
    
    def ensure_trial_plan(self) -> Plan:
        """
        Ensures Trial plan exists in database, creating it if missing.
        
        This is safe for test/dev environments and ensures tenants can always
        get a trial subscription. In production, plans should be seeded via migrations.
        
        Returns:
            Plan instance (Trial plan)
        """
        trial_plan = self.db.query(Plan).filter(Plan.name == "Trial").first()
        if not trial_plan:
            # Create Trial plan with reasonable defaults
            trial_plan = Plan(
                name="Trial",
                monthly_invoice_limit=50,
                monthly_ai_limit=20,
                rate_limit_per_minute=30,
                features={"ai": True, "phase1": True, "phase2": True},
                is_active=True
            )
            self.db.add(trial_plan)
            self.db.commit()
            self.db.refresh(trial_plan)
            logger.info("Created Trial plan (was missing)")
        
        return trial_plan
    
    def _auto_assign_trial(self) -> Optional[Subscription]:
        """
        Auto-assigns Trial subscription to tenant if no subscription exists.
        
        Ensures Trial plan exists before attempting assignment.
        
        Returns:
            Subscription instance or None if assignment fails
        """
        # Ensure Trial plan exists (creates if missing)
        trial_plan = self.ensure_trial_plan()
        
        trial_starts_at = datetime.utcnow()
        trial_ends_at = trial_starts_at + timedelta(days=7)
        
        subscription = Subscription(
            tenant_id=self.tenant_context.tenant_id,
            plan_id=trial_plan.id,
            status=SubscriptionStatus.TRIAL,
            trial_starts_at=trial_starts_at,
            trial_ends_at=trial_ends_at
        )
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        logger.info(
            f"Auto-assigned Trial subscription to tenant {self.tenant_context.tenant_id} "
            f"(expires {trial_ends_at})"
        )
        
        return subscription
    
    def _check_and_handle_trial_expiry(self, subscription: Subscription) -> Subscription:
        """
        Checks if trial has expired and auto-downgrades to Free Sandbox.
        
        Args:
            subscription: Subscription to check
            
        Returns:
            Updated subscription
        """
        if subscription.status == SubscriptionStatus.TRIAL:
            if subscription.trial_ends_at and datetime.utcnow() > subscription.trial_ends_at:
                # Trial expired - downgrade to Free Sandbox
                free_plan = self.db.query(Plan).filter(Plan.name == "Free Sandbox").first()
                if free_plan:
                    subscription.plan_id = free_plan.id
                    subscription.status = SubscriptionStatus.EXPIRED
                    subscription.trial_ends_at = None
                    self.db.commit()
                    self.db.refresh(subscription)
                    logger.info(
                        f"Trial expired for tenant {self.tenant_context.tenant_id}. "
                        f"Auto-downgraded to Free Sandbox."
                    )
        
        return subscription
    
    def get_trial_days_remaining(self, subscription: Subscription) -> Optional[int]:
        """
        Calculates remaining trial days.
        
        Args:
            subscription: Subscription to check
            
        Returns:
            Number of days remaining or None if not in trial
        """
        if subscription.status != SubscriptionStatus.TRIAL or not subscription.trial_ends_at:
            return None
        
        remaining = (subscription.trial_ends_at - datetime.utcnow()).days
        return max(0, remaining)
    
    def get_current_billing_period(self) -> str:
        """
        Gets current billing period in YYYY-MM format.
        
        Returns:
            Billing period string (e.g., "2025-01")
        """
        now = datetime.utcnow()
        return now.strftime("%Y-%m")
    
    def get_or_create_usage_counter(
        self,
        subscription: Subscription,
        billing_period: Optional[str] = None
    ) -> UsageCounter:
        """
        Gets or creates usage counter for current billing period.
        
        Args:
            subscription: Subscription instance
            billing_period: Optional billing period (defaults to current)
            
        Returns:
            UsageCounter instance
        """
        if not billing_period:
            billing_period = self.get_current_billing_period()
        
        counter = self.db.query(UsageCounter).filter(
            and_(
                UsageCounter.tenant_id == self.tenant_context.tenant_id,
                UsageCounter.billing_period == billing_period
            )
        ).first()
        
        if not counter:
            counter = UsageCounter(
                tenant_id=self.tenant_context.tenant_id,
                subscription_id=subscription.id,
                billing_period=billing_period,
                invoice_count=0,
                ai_request_count=0
            )
            self.db.add(counter)
            self.db.commit()
            self.db.refresh(counter)
            logger.debug(
                f"Created usage counter for tenant {self.tenant_context.tenant_id}, "
                f"billing_period={billing_period}"
            )
        
        return counter
    
    def get_effective_limits(self, subscription: Subscription) -> Dict[str, int]:
        """
        Gets effective limits for subscription (plan limits or custom limits).
        
        Args:
            subscription: Subscription instance
            
        Returns:
            Dictionary with invoice_limit, ai_limit, rate_limit
            Values are guaranteed to be integers (None becomes 0)
        """
        plan = subscription.plan
        
        # Start with plan defaults (handle None as 0)
        limits = {
            "invoice_limit": plan.monthly_invoice_limit if plan.monthly_invoice_limit is not None else 0,
            "ai_limit": plan.monthly_ai_limit if plan.monthly_ai_limit is not None else 0,
            "rate_limit": plan.rate_limit_per_minute if plan.rate_limit_per_minute is not None else 60
        }
        
        # Override with custom limits if present (Enterprise)
        if subscription.custom_limits:
            if "monthly_invoice_limit" in subscription.custom_limits:
                custom_invoice_limit = subscription.custom_limits["monthly_invoice_limit"]
                limits["invoice_limit"] = custom_invoice_limit if custom_invoice_limit is not None else 0
            if "monthly_ai_limit" in subscription.custom_limits:
                custom_ai_limit = subscription.custom_limits["monthly_ai_limit"]
                limits["ai_limit"] = custom_ai_limit if custom_ai_limit is not None else 0
            if "rate_limit_per_minute" in subscription.custom_limits:
                custom_rate_limit = subscription.custom_limits["rate_limit_per_minute"]
                limits["rate_limit"] = custom_rate_limit if custom_rate_limit is not None else 60
        
        return limits
    
    def check_invoice_limit(self) -> Tuple[bool, Optional[LimitExceededError]]:
        """
        Checks if tenant can create an invoice.
        
        Returns:
            Tuple of (allowed, error_if_blocked)
        """
        subscription = self.get_current_subscription()
        if not subscription:
            return False, LimitExceededError(
                limit_type="SUBSCRIPTION_MISSING",
                message="No active subscription found",
                upgrade_required=True
            )
        
        # Check trial expiry
        if subscription.status == SubscriptionStatus.TRIAL:
            if subscription.trial_ends_at and datetime.utcnow() > subscription.trial_ends_at:
                return False, LimitExceededError(
                    limit_type="TRIAL_EXPIRED",
                    message="Your trial has expired. Please upgrade to continue.",
                    upgrade_required=True,
                    plan_name=subscription.plan.name
                )
        
        # Get usage counter
        counter = self.get_or_create_usage_counter(subscription)
        limits = self.get_effective_limits(subscription)
        
        # Get limit value (handle None as 0 = unlimited)
        invoice_limit = limits.get("invoice_limit")
        if invoice_limit is None:
            invoice_limit = 0
        
        # Check limit (0 = unlimited, otherwise enforce strictly)
        # If limit is set and usage is >= limit, block the request
        if invoice_limit > 0:
            current_usage = counter.invoice_count or 0
            if current_usage >= invoice_limit:
                return False, LimitExceededError(
                    limit_type="INVOICE_COUNT",
                    message=f"Monthly invoice limit ({invoice_limit}) exceeded",
                    upgrade_required=True,
                    current_usage=current_usage,
                    limit=invoice_limit,
                    plan_name=subscription.plan.name
                )
        
        return True, None
    
    def increment_invoice_count(self) -> None:
        """
        Increments invoice count for current billing period.
        
        CRITICAL: Only call this after successful invoice creation.
        Do not count failed or rejected invoices.
        """
        subscription = self.get_current_subscription()
        if not subscription:
            logger.warning(f"No subscription found for tenant {self.tenant_context.tenant_id}")
            return
        
        counter = self.get_or_create_usage_counter(subscription)
        counter.invoice_count += 1
        self.db.commit()
        logger.debug(
            f"Incremented invoice count for tenant {self.tenant_context.tenant_id}: "
            f"{counter.invoice_count}"
        )
    
    def check_ai_limit(self) -> Tuple[bool, Optional[LimitExceededError]]:
        """
        Checks if tenant can make AI requests.
        
        Returns:
            Tuple of (allowed, error_if_blocked)
        """
        subscription = self.get_current_subscription()
        if not subscription:
            return False, LimitExceededError(
                limit_type="SUBSCRIPTION_MISSING",
                message="No active subscription found",
                upgrade_required=True
            )
        
        # Check trial expiry
        if subscription.status == SubscriptionStatus.TRIAL:
            if subscription.trial_ends_at and datetime.utcnow() > subscription.trial_ends_at:
                return False, LimitExceededError(
                    limit_type="TRIAL_EXPIRED",
                    message="Your trial has expired. Please upgrade to continue.",
                    upgrade_required=True,
                    plan_name=subscription.plan.name
                )
        
        # Get usage counter
        counter = self.get_or_create_usage_counter(subscription)
        limits = self.get_effective_limits(subscription)
        
        # Get limit value (handle None as 0 = unlimited)
        ai_limit = limits.get("ai_limit")
        if ai_limit is None:
            ai_limit = 0
        
        # Check limit (0 = unlimited, otherwise enforce strictly)
        # If limit is set and usage is >= limit, block the request
        if ai_limit > 0:
            current_usage = counter.ai_request_count or 0
            if current_usage >= ai_limit:
                return False, LimitExceededError(
                    limit_type="AI_USAGE",
                    message=f"Monthly AI usage limit ({ai_limit}) exceeded",
                    upgrade_required=True,
                    current_usage=current_usage,
                    limit=ai_limit,
                    plan_name=subscription.plan.name
                )
        
        return True, None
    
    def increment_ai_count(self) -> None:
        """
        Increments AI request count for current billing period.
        """
        subscription = self.get_current_subscription()
        if not subscription:
            logger.warning(f"No subscription found for tenant {self.tenant_context.tenant_id}")
            return
        
        counter = self.get_or_create_usage_counter(subscription)
        counter.ai_request_count += 1
        self.db.commit()
        logger.debug(
            f"Incremented AI count for tenant {self.tenant_context.tenant_id}: "
            f"{counter.ai_request_count}"
        )
    
    def get_rate_limit(self) -> int:
        """
        Gets rate limit per minute for current tenant.
        
        Returns:
            Rate limit (requests per minute)
        """
        subscription = self.get_current_subscription()
        if not subscription:
            return 60  # Default rate limit
        
        limits = self.get_effective_limits(subscription)
        return limits["rate_limit"]
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Gets current usage summary for tenant.
        
        Auto-assigns trial if no subscription exists.
        
        Returns:
            Dictionary with usage information
        """
        subscription = self.get_current_subscription()
        if not subscription:
            # Try to auto-assign trial
            subscription = self._auto_assign_trial()
            if not subscription:
                return {
                    "has_subscription": False,
                    "message": "No active subscription and Trial plan not available"
                }
        
        counter = self.get_or_create_usage_counter(subscription)
        limits = self.get_effective_limits(subscription)
        
        invoice_remaining = None
        if limits["invoice_limit"] > 0:
            invoice_remaining = max(0, limits["invoice_limit"] - counter.invoice_count)
        
        ai_remaining = None
        if limits["ai_limit"] > 0:
            ai_remaining = max(0, limits["ai_limit"] - counter.ai_request_count)
        
        return {
            "has_subscription": True,
            "plan_name": subscription.plan.name,
            "status": subscription.status.value,
            "trial_days_remaining": self.get_trial_days_remaining(subscription),
            "billing_period": counter.billing_period,
            "invoice_count": counter.invoice_count,
            "invoice_limit": limits["invoice_limit"],
            "invoice_remaining": invoice_remaining,
            "ai_request_count": counter.ai_request_count,
            "ai_limit": limits["ai_limit"],
            "ai_remaining": ai_remaining,
            "rate_limit_per_minute": limits["rate_limit"]
        }

