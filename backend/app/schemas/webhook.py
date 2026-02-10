"""
Webhook Pydantic schemas.

Defines request/response schemas for webhook management.
Handles validation of webhook configuration and event subscriptions.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, field_validator
import enum


class WebhookEvent(str, enum.Enum):
    """Supported webhook event types."""
    INVOICE_CLEARED = "invoice.cleared"
    INVOICE_REJECTED = "invoice.rejected"
    INVOICE_FAILED = "invoice.failed"
    INVOICE_RETRY_STARTED = "invoice.retry_started"
    INVOICE_RETRY_COMPLETED = "invoice.retry_completed"


class WebhookCreateRequest(BaseModel):
    """Schema for webhook creation request."""
    url: str = Field(..., description="Webhook URL endpoint", max_length=500)
    events: List[WebhookEvent] = Field(..., description="List of event types to subscribe to", min_length=1)
    secret: Optional[str] = Field(None, description="HMAC secret for signature verification (auto-generated if not provided)", max_length=255)
    is_active: bool = Field(True, description="Whether the webhook is active")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        if len(v) > 500:
            raise ValueError("URL must be 500 characters or less")
        return v
    
    @field_validator('events')
    @classmethod
    def validate_events(cls, v: List[WebhookEvent]) -> List[WebhookEvent]:
        """Validate events list."""
        if not v or len(v) == 0:
            raise ValueError("At least one event type must be specified")
        return v


class WebhookUpdateRequest(BaseModel):
    """Schema for webhook update request."""
    url: Optional[str] = Field(None, description="Webhook URL endpoint", max_length=500)
    events: Optional[List[WebhookEvent]] = Field(None, description="List of event types to subscribe to", min_length=1)
    secret: Optional[str] = Field(None, description="HMAC secret for signature verification", max_length=255)
    is_active: Optional[bool] = Field(None, description="Whether the webhook is active")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format."""
        if v is not None:
            if not v.startswith(('http://', 'https://')):
                raise ValueError("URL must start with http:// or https://")
            if len(v) > 500:
                raise ValueError("URL must be 500 characters or less")
        return v
    
    @field_validator('events')
    @classmethod
    def validate_events(cls, v: Optional[List[WebhookEvent]]) -> Optional[List[WebhookEvent]]:
        """Validate events list."""
        if v is not None and len(v) == 0:
            raise ValueError("At least one event type must be specified")
        return v


class WebhookResponse(BaseModel):
    """Schema for webhook response."""
    id: int
    tenant_id: int
    url: str
    events: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_triggered_at: Optional[datetime] = None
    failure_count: int
    
    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    """Schema for webhook list response with metadata."""
    webhooks: List[WebhookResponse]
    total: int
    active_count: int
    inactive_count: int


class WebhookPayload(BaseModel):
    """Schema for webhook payload structure with bilingual support."""
    event: str = Field(..., description="Event type (e.g., 'invoice.cleared')")
    event_name_en: str = Field(..., description="Event name in English")
    event_name_ar: str = Field(..., description="Event name in Arabic")
    description_en: str = Field(..., description="Event description in English")
    description_ar: str = Field(..., description="Event description in Arabic")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    data: dict = Field(..., description="Event-specific data")


class WebhookLogResponse(BaseModel):
    """Schema for webhook log response."""
    id: int
    webhook_id: int
    event: str
    payload: dict
    response_status: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

