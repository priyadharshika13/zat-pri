"""
Subscription database models.

Defines models for subscription plans, tenant subscriptions, and usage tracking.
Handles plan limits, trial management, and usage counters.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.models import Base


class SubscriptionStatus(str, enum.Enum):
    """Subscription status values."""
    ACTIVE = "active"
    TRIAL = "trial"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class Plan(Base):
    """
    Subscription plan model.
    
    Defines available plans with their limits and features.
    """
    
    __tablename__ = "plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    monthly_invoice_limit = Column(Integer, nullable=False, default=0)  # 0 = unlimited
    monthly_ai_limit = Column(Integer, nullable=False, default=0)  # 0 = unlimited
    rate_limit_per_minute = Column(Integer, nullable=False, default=60)
    features = Column(JSON, nullable=True)  # JSON object with feature flags
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")
    
    def __repr__(self):
        return f"<Plan(id={self.id}, name='{self.name}', invoice_limit={self.monthly_invoice_limit}, ai_limit={self.monthly_ai_limit})>"


class Subscription(Base):
    """
    Tenant subscription model.
    
    Links tenants to plans and tracks trial status.
    """
    
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    status = Column(SQLEnum(SubscriptionStatus), nullable=False, index=True)
    trial_starts_at = Column(DateTime, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    custom_limits = Column(JSON, nullable=True)  # JSON object for enterprise custom limits
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    plan = relationship("Plan", back_populates="subscriptions")
    usage_counters = relationship("UsageCounter", back_populates="subscription", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, tenant_id={self.tenant_id}, plan_id={self.plan_id}, status='{self.status.value}')>"


class UsageCounter(Base):
    """
    Usage counter model for tracking monthly usage per tenant.
    
    Tracks invoice count and AI request count per billing period.
    """
    
    __tablename__ = "usage_counters"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False, index=True)
    billing_period = Column(String(7), nullable=False, index=True)  # Format: YYYY-MM
    invoice_count = Column(Integer, default=0, nullable=False)
    ai_request_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="usage_counters")
    
    # Unique constraint: one counter per tenant per billing period
    # Note: sqlite_autoincrement removed - PostgreSQL handles autoincrement automatically
    # SQLite also handles it automatically, so this was redundant
    
    def __repr__(self):
        return f"<UsageCounter(id={self.id}, tenant_id={self.tenant_id}, billing_period='{self.billing_period}', invoice_count={self.invoice_count}, ai_count={self.ai_request_count})>"

