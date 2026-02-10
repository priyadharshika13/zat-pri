"""
Webhook management API endpoints.

Handles webhook registration, listing, updates, and deletion.
All endpoints require API key authentication and enforce tenant isolation.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, Optional, List
from sqlalchemy.orm import Session

from app.core.security import verify_api_key_and_resolve_tenant
from app.schemas.auth import TenantContext
from app.schemas.webhook import (
    WebhookCreateRequest,
    WebhookUpdateRequest,
    WebhookResponse,
    WebhookListResponse,
    WebhookLogResponse
)
from app.core.production_guards import validate_write_action
from app.services.webhook_service import WebhookService
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def get_webhook_service(
    db: Annotated[Session, Depends(get_db)],
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)]
) -> WebhookService:
    """Dependency function for webhook service with database and tenant context."""
    return WebhookService(db=db, tenant_context=tenant)


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new webhook"
)
async def create_webhook(
    request: WebhookCreateRequest,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> WebhookResponse:
    """
    Registers a new webhook for the tenant.
    
    **Requirements:**
    - Valid URL (http:// or https://)
    - At least one event type
    - Secret will be auto-generated if not provided
    
    **Process:**
    1. Validates URL format
    2. Validates event types
    3. Generates secret if not provided
    4. Creates webhook record
    
    **Security:**
    - Tenant isolation enforced
    - Secret stored securely in database
    - HMAC signatures used for verification
    
    **Returns:**
    - Created webhook configuration
    """
    # Phase 9: Validate write action permission
    validate_write_action(tenant, db, "create_webhook")
    
    try:
        service = WebhookService(db=db, tenant_context=tenant)
        webhook = service.create_webhook(request)
        
        logger.info(
            f"Webhook created: id={webhook.id}, tenant_id={tenant.tenant_id}, "
            f"url={webhook.url[:50]}..."
        )
        
        return WebhookResponse.model_validate(webhook)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Webhook creation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during webhook creation"
        )


@router.get(
    "",
    response_model=WebhookListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all webhooks for the tenant"
)
async def list_webhooks(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    service: Annotated[WebhookService, Depends(get_webhook_service)]
) -> WebhookListResponse:
    """
    Lists all webhooks for the current tenant.
    
    **CRITICAL: Only returns webhooks belonging to the authenticated tenant.**
    
    **Returns:**
    - List of webhooks with metadata
    - Total count
    - Active and inactive counts
    """
    try:
        webhooks = service.list_webhooks()
        
        # Calculate counts
        active_count = sum(1 for w in webhooks if w.is_active)
        inactive_count = len(webhooks) - active_count
        
        return WebhookListResponse(
            webhooks=[WebhookResponse.model_validate(w) for w in webhooks],
            total=len(webhooks),
            active_count=active_count,
            inactive_count=inactive_count
        )
        
    except Exception as e:
        logger.error(f"Webhook list error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during webhook retrieval"
        )


@router.get(
    "/{webhook_id}",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Get webhook by ID"
)
async def get_webhook(
    webhook_id: int,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    service: Annotated[WebhookService, Depends(get_webhook_service)]
) -> WebhookResponse:
    """
    Gets a webhook by ID.
    
    **CRITICAL: Only returns webhook belonging to the authenticated tenant.**
    
    **Returns:**
    - Webhook configuration or 404 if not found
    """
    try:
        webhook = service.get_webhook(webhook_id)
        
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )
        
        return WebhookResponse.model_validate(webhook)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook retrieval error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during webhook retrieval"
        )


@router.put(
    "/{webhook_id}",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Update webhook configuration"
)
async def update_webhook(
    webhook_id: int,
    request: WebhookUpdateRequest,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[WebhookService, Depends(get_webhook_service)]
) -> WebhookResponse:
    """
    Updates a webhook configuration.
    
    **CRITICAL:**
    - Only updates webhooks belonging to the authenticated tenant
    - All fields are optional (only provided fields are updated)
    
    **Security:**
    - Tenant isolation enforced
    - Secret can be updated if needed
    
    **Returns:**
    - Updated webhook configuration
    - 404 if webhook not found
    """
    # Phase 9: Validate write action permission
    validate_write_action(tenant, db, "update_webhook")
    
    try:
        webhook = service.update_webhook(webhook_id, request)
        
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )
        
        logger.info(
            f"Webhook updated: id={webhook_id}, tenant_id={tenant.tenant_id}"
        )
        
        return WebhookResponse.model_validate(webhook)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook update error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during webhook update"
        )


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete webhook"
)
async def delete_webhook(
    webhook_id: int,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[WebhookService, Depends(get_webhook_service)]
) -> None:
    """
    Deletes a webhook.
    
    **CRITICAL:**
    - Only deletes webhooks belonging to the authenticated tenant
    - Removes webhook configuration and all associated logs
    
    **Security:**
    - Tenant isolation enforced
    - Cannot delete webhooks belonging to other tenants
    
    **Returns:**
    - 204 No Content on success
    - 404 if webhook not found
    """
    # Phase 9: Validate write action permission
    validate_write_action(tenant, db, "delete_webhook")
    
    try:
        deleted = service.delete_webhook(webhook_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )
        
        logger.info(
            f"Webhook deleted: id={webhook_id}, tenant_id={tenant.tenant_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook deletion error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during webhook deletion"
        )


@router.get(
    "/{webhook_id}/logs",
    response_model=List[WebhookLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get webhook delivery logs"
)
async def get_webhook_logs(
    webhook_id: int,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    service: Annotated[WebhookService, Depends(get_webhook_service)],
    limit: int = 100
) -> List[WebhookLogResponse]:
    """
    Gets delivery logs for a webhook.
    
    **CRITICAL: Only returns logs for webhooks belonging to the authenticated tenant.**
    
    **Parameters:**
    - limit: Maximum number of logs to return (default: 100)
    
    **Returns:**
    - List of webhook delivery logs
    - 404 if webhook not found
    """
    try:
        # Verify webhook exists and belongs to tenant
        webhook = service.get_webhook(webhook_id)
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )
        
        logs = service.get_webhook_logs(webhook_id=webhook_id, limit=limit)
        
        return [WebhookLogResponse.model_validate(log) for log in logs]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook logs retrieval error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during webhook logs retrieval"
        )

