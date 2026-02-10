"""
Webhook trigger utility.

Provides helper functions to trigger webhooks asynchronously after database commits.
Ensures webhooks are delivered after transactions are committed, without blocking the main flow.
"""

import logging
import asyncio
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.schemas.webhook import WebhookEvent
from app.schemas.auth import TenantContext
from app.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)


async def trigger_webhook_async(
    tenant_context: TenantContext,
    event: WebhookEvent,
    payload: Dict[str, Any]
) -> None:
    """
    Triggers webhooks asynchronously for a given event.
    
    This function should be called AFTER database commit to ensure
    webhook delivery happens after transaction completion.
    
    Creates a new database session for webhook service to avoid
    using the same session that was just committed.
    
    Args:
        tenant_context: Tenant context
        event: Webhook event type
        payload: Event payload data
    """
    try:
        # Create a new database session for webhook service
        # (to avoid using the same session that was just committed)
        from app.db.session import get_session_local
        SessionLocal = get_session_local()
        webhook_db = SessionLocal()
        
        try:
            service = WebhookService(db=webhook_db, tenant_context=tenant_context)
            await service.trigger_webhook(event, payload)
        finally:
            webhook_db.close()
            
    except Exception as e:
        # Log error but don't raise - webhook failures should not break invoice flow
        logger.error(
            f"Error triggering webhook: event={event.value}, "
            f"tenant_id={tenant_context.tenant_id}, error={str(e)}",
            exc_info=True
        )


def schedule_webhook_trigger(
    tenant_context: TenantContext,
    event: WebhookEvent,
    payload: Dict[str, Any]
) -> None:
    """
    Schedules webhook trigger as a background task (fire-and-forget).
    
    This is a synchronous wrapper that schedules the async webhook trigger.
    Use this after database commits to trigger webhooks without blocking.
    
    Args:
        tenant_context: Tenant context
        event: Webhook event type
        payload: Event payload data
    """
    try:
        # Try to get the current event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, create a task
            asyncio.create_task(trigger_webhook_async(tenant_context, event, payload))
        except RuntimeError:
            # No running event loop, create a new one in a thread
            import threading
            def run_in_thread():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(trigger_webhook_async(tenant_context, event, payload))
                    loop.close()
                except Exception as e:
                    logger.error(
                        f"Failed to trigger webhook in thread: event={event.value}, error={str(e)}",
                        exc_info=True
                    )
            
            thread = threading.Thread(target=run_in_thread, daemon=True)
            thread.start()
            
    except Exception as e:
        # Log error but don't raise - webhook failures should not break invoice flow
        logger.error(
            f"Error scheduling webhook trigger: event={event.value}, error={str(e)}",
            exc_info=True
        )

