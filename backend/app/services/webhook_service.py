"""
Webhook service layer.

Provides webhook management, delivery, and logging functionality.
Handles HMAC signature generation, async delivery with retries, and failure tracking.
"""

import logging
import hmac
import hashlib
import secrets
import json
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

import httpx

from app.models.webhook import Webhook, WebhookLog
from app.schemas.webhook import WebhookCreateRequest, WebhookUpdateRequest, WebhookEvent, WebhookPayload
from app.schemas.auth import TenantContext

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Webhook service for managing webhooks and delivering events.
    
    Provides:
    - Webhook CRUD operations with tenant isolation
    - HMAC signature generation
    - Async webhook delivery with retries
    - Delivery logging and failure tracking
    """
    
    # Delivery configuration
    DELIVERY_TIMEOUT = 5.0  # seconds
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 1.0  # seconds (exponential backoff: 1s, 2s, 4s)
    
    def __init__(self, db: Session, tenant_context: TenantContext):
        """
        Initializes webhook service.
        
        Args:
            db: Database session
            tenant_context: Tenant context for isolation
        """
        self.db = db
        self.tenant_context = tenant_context
        self.http_client = httpx.AsyncClient(timeout=self.DELIVERY_TIMEOUT)
    
    async def close(self):
        """Close HTTP client. Call this when done with the service."""
        if hasattr(self, 'http_client') and self.http_client:
            try:
                await self.http_client.aclose()
            except Exception:
                pass
    
    def create_webhook(self, request: WebhookCreateRequest) -> Webhook:
        """
        Creates a new webhook for the tenant.
        
        Args:
            request: Webhook creation request
            
        Returns:
            Created webhook
            
        Raises:
            ValueError: If validation fails
        """
        # Generate secret if not provided
        secret = request.secret or self._generate_secret()
        
        # Convert events enum to strings for JSON storage
        events_list = [event.value for event in request.events]
        
        webhook = Webhook(
            tenant_id=self.tenant_context.tenant_id,
            url=request.url,
            events=events_list,
            secret=secret,
            is_active=request.is_active
        )
        
        self.db.add(webhook)
        self.db.commit()
        self.db.refresh(webhook)
        
        logger.info(
            f"Webhook created: id={webhook.id}, tenant_id={self.tenant_context.tenant_id}, "
            f"url={webhook.url[:50]}..., events={events_list}"
        )
        
        return webhook
    
    def list_webhooks(self) -> List[Webhook]:
        """
        Lists all webhooks for the tenant.
        
        Returns:
            List of webhooks
        """
        webhooks = self.db.query(Webhook).filter(
            Webhook.tenant_id == self.tenant_context.tenant_id
        ).order_by(Webhook.created_at.desc()).all()
        
        return webhooks
    
    def get_webhook(self, webhook_id: int) -> Optional[Webhook]:
        """
        Gets a webhook by ID with tenant isolation.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Webhook if found and belongs to tenant, None otherwise
        """
        webhook = self.db.query(Webhook).filter(
            and_(
                Webhook.id == webhook_id,
                Webhook.tenant_id == self.tenant_context.tenant_id
            )
        ).first()
        
        return webhook
    
    def update_webhook(self, webhook_id: int, request: WebhookUpdateRequest) -> Optional[Webhook]:
        """
        Updates a webhook with tenant isolation.
        
        Args:
            webhook_id: Webhook ID
            request: Webhook update request
            
        Returns:
            Updated webhook if found, None otherwise
            
        Raises:
            ValueError: If validation fails
        """
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return None
        
        # Update fields if provided
        if request.url is not None:
            webhook.url = request.url
        if request.events is not None:
            webhook.events = [event.value for event in request.events]
        if request.secret is not None:
            webhook.secret = request.secret
        if request.is_active is not None:
            webhook.is_active = request.is_active
        
        webhook.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(webhook)
        
        logger.info(
            f"Webhook updated: id={webhook_id}, tenant_id={self.tenant_context.tenant_id}"
        )
        
        return webhook
    
    def delete_webhook(self, webhook_id: int) -> bool:
        """
        Deletes a webhook with tenant isolation.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            True if deleted, False if not found
        """
        webhook = self.get_webhook(webhook_id)
        if not webhook:
            return False
        
        self.db.delete(webhook)
        self.db.commit()
        
        logger.info(
            f"Webhook deleted: id={webhook_id}, tenant_id={self.tenant_context.tenant_id}"
        )
        
        return True
    
    def _generate_secret(self) -> str:
        """
        Generates a secure random secret for HMAC signing.
        
        Returns:
            Random secret string (32 bytes, hex encoded = 64 chars)
        """
        return secrets.token_hex(32)
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """
        Generates HMAC-SHA256 signature for webhook payload.
        
        Args:
            payload: JSON string payload
            secret: Webhook secret
            
        Returns:
            Hex-encoded signature
        """
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def _deliver_webhook(
        self,
        webhook: Webhook,
        event: str,
        payload: Dict[str, Any]
    ) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Delivers a webhook with retries.
        
        Args:
            webhook: Webhook configuration
            event: Event type
            payload: Payload data
            
        Returns:
            Tuple of (success, response_status, error_message)
        """
        # Get bilingual event labels
        from app.core.i18n import get_webhook_event_labels
        event_labels = get_webhook_event_labels(event)
        
        # Create webhook payload with bilingual support
        webhook_payload = WebhookPayload(
            event=event,
            event_name_en=event_labels["event_name_en"],
            event_name_ar=event_labels["event_name_ar"],
            description_en=event_labels["description_en"],
            description_ar=event_labels["description_ar"],
            timestamp=datetime.utcnow().isoformat() + 'Z',
            data=payload
        )
        
        # Serialize to JSON
        payload_json = webhook_payload.model_dump_json()
        
        # Generate signature
        signature = self._generate_signature(payload_json, webhook.secret)
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-FATURAIX-Signature": signature
        }
        
        # Retry logic with exponential backoff
        last_error = None
        last_status = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                # Calculate backoff delay (except for first attempt)
                if attempt > 0:
                    delay = self.RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)
                    logger.info(
                        f"Retrying webhook delivery: webhook_id={webhook.id}, "
                        f"event={event}, attempt={attempt + 1}/{self.MAX_RETRIES}"
                    )
                
                # Make HTTP request
                response = await self.http_client.post(
                    webhook.url,
                    content=payload_json,
                    headers=headers
                )
                
                # Check if successful (2xx status codes)
                if 200 <= response.status_code < 300:
                    logger.info(
                        f"Webhook delivered successfully: webhook_id={webhook.id}, "
                        f"event={event}, status={response.status_code}"
                    )
                    return True, response.status_code, None
                else:
                    last_status = response.status_code
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(
                        f"Webhook delivery failed: webhook_id={webhook.id}, "
                        f"event={event}, status={response.status_code}, attempt={attempt + 1}"
                    )
                    
            except httpx.TimeoutException:
                last_error = "Request timeout"
                logger.warning(
                    f"Webhook delivery timeout: webhook_id={webhook.id}, "
                    f"event={event}, attempt={attempt + 1}"
                )
            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"Webhook delivery error: webhook_id={webhook.id}, "
                    f"event={event}, error={str(e)}, attempt={attempt + 1}",
                    exc_info=True
                )
        
        # All retries failed
        logger.error(
            f"Webhook delivery failed after {self.MAX_RETRIES} attempts: "
            f"webhook_id={webhook.id}, event={event}, error={last_error}"
        )
        
        return False, last_status, last_error
    
    async def trigger_webhook(
        self,
        event: WebhookEvent,
        payload: Dict[str, Any]
    ) -> None:
        """
        Triggers webhooks for a given event.
        
        This method:
        1. Finds all active webhooks subscribed to the event
        2. Delivers webhooks asynchronously
        3. Logs delivery attempts
        4. Updates webhook metrics
        
        Args:
            event: Event type
            payload: Event payload data
        """
        event_str = event.value
        
        # Find all active webhooks subscribed to this event
        webhooks = self.db.query(Webhook).filter(
            and_(
                Webhook.tenant_id == self.tenant_context.tenant_id,
                Webhook.is_active == True
            )
        ).all()
        
        # Filter webhooks that subscribe to this event
        subscribed_webhooks = [
            w for w in webhooks
            if event_str in w.events
        ]
        
        if not subscribed_webhooks:
            logger.debug(
                f"No webhooks subscribed to event: event={event_str}, "
                f"tenant_id={self.tenant_context.tenant_id}"
            )
            return
        
        logger.info(
            f"Triggering webhooks: event={event_str}, "
            f"tenant_id={self.tenant_context.tenant_id}, "
            f"count={len(subscribed_webhooks)}"
        )
        
        # Deliver to each webhook
        for webhook in subscribed_webhooks:
            try:
                # Deliver webhook
                success, response_status, error_message = await self._deliver_webhook(
                    webhook, event_str, payload
                )
                
                # Log delivery attempt
                self._log_webhook_delivery(
                    webhook.id,
                    event_str,
                    payload,
                    response_status,
                    error_message
                )
                
                # Update webhook metrics
                webhook.last_triggered_at = datetime.utcnow()
                if success:
                    webhook.failure_count = 0
                else:
                    webhook.failure_count += 1
                
                self.db.commit()
                
            except Exception as e:
                logger.error(
                    f"Error triggering webhook: webhook_id={webhook.id}, "
                    f"event={event_str}, error={str(e)}",
                    exc_info=True
                )
                # Log the error
                self._log_webhook_delivery(
                    webhook.id,
                    event_str,
                    payload,
                    None,
                    f"Internal error: {str(e)}"
                )
    
    def _log_webhook_delivery(
        self,
        webhook_id: int,
        event: str,
        payload: Dict[str, Any],
        response_status: Optional[int],
        error_message: Optional[str]
    ) -> None:
        """
        Logs a webhook delivery attempt.
        
        Args:
            webhook_id: Webhook ID
            event: Event type
            payload: Payload sent
            response_status: HTTP response status
            error_message: Error message if failed
        """
        log_entry = WebhookLog(
            webhook_id=webhook_id,
            event=event,
            payload=payload,
            response_status=response_status,
            error_message=error_message
        )
        
        self.db.add(log_entry)
        self.db.commit()
    
    def get_webhook_logs(
        self,
        webhook_id: Optional[int] = None,
        event: Optional[str] = None,
        limit: int = 100
    ) -> List[WebhookLog]:
        """
        Gets webhook delivery logs with tenant isolation.
        
        Args:
            webhook_id: Optional webhook ID filter
            event: Optional event type filter
            limit: Maximum number of logs to return
            
        Returns:
            List of webhook logs
        """
        # Build query with tenant isolation
        query = self.db.query(WebhookLog).join(Webhook).filter(
            Webhook.tenant_id == self.tenant_context.tenant_id
        )
        
        if webhook_id:
            query = query.filter(WebhookLog.webhook_id == webhook_id)
        if event:
            query = query.filter(WebhookLog.event == event)
        
        logs = query.order_by(WebhookLog.created_at.desc()).limit(limit).all()
        
        return logs

