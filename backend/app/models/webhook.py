"""
Webhook database models.

Defines webhook configuration and webhook log entities for tenant-scoped webhook management.
Each webhook is tied to a specific tenant and cannot be accessed by other tenants.
"""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, JSON, Boolean, Index
from datetime import datetime
from typing import Optional

from app.db.models import Base


class Webhook(Base):
    """
    Webhook configuration database model.
    
    Stores webhook configuration for tenant-scoped event notifications.
    Each webhook belongs to exactly one tenant.
    """
    
    __tablename__ = "webhooks"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    url = Column(String(500), nullable=False, comment="Webhook URL endpoint")
    events = Column(JSON, nullable=False, comment="Array of event types to subscribe to")
    secret = Column(String(255), nullable=False, comment="HMAC secret for signature verification")
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Optional tracking fields
    last_triggered_at = Column(DateTime, nullable=True, comment="Last time this webhook was triggered")
    failure_count = Column(Integer, default=0, nullable=False, comment="Number of consecutive failures")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_webhooks_tenant_active', 'tenant_id', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Webhook(id={self.id}, tenant_id={self.tenant_id}, url='{self.url[:50]}...', is_active={self.is_active})>"


class WebhookLog(Base):
    """
    Webhook delivery log database model.
    
    Tracks webhook delivery attempts with tenant isolation.
    Each log entry belongs to exactly one webhook and tenant.
    """
    
    __tablename__ = "webhook_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id"), nullable=False, index=True)
    event = Column(String(100), nullable=False, index=True, comment="Event type that triggered the webhook")
    payload = Column(JSON, nullable=False, comment="Webhook payload sent")
    response_status = Column(Integer, nullable=True, comment="HTTP response status code")
    error_message = Column(Text, nullable=True, comment="Error message if delivery failed")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_webhook_logs_webhook_created', 'webhook_id', 'created_at'),
        Index('ix_webhook_logs_event_created', 'event', 'created_at'),
    )
    
    def __repr__(self):
        return f"<WebhookLog(id={self.id}, webhook_id={self.webhook_id}, event='{self.event}', response_status={self.response_status})>"

