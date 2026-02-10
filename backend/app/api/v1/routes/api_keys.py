"""
API key management endpoints.

Handles API key creation and management.
All endpoints require API key authentication.
"""

import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy.orm import Session

from app.core.security import verify_api_key_and_resolve_tenant
from app.core.production_guards import validate_write_action
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyUpdate
from app.schemas.auth import TenantContext
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.tenant import Tenant

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get(
    "",
    response_model=list[ApiKeyResponse],
    status_code=status.HTTP_200_OK,
    summary="List API keys for the current tenant"
)
async def list_api_keys(
    current_tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> list[ApiKeyResponse]:
    """
    Lists all API keys for the tenant associated with the current API key.
    CRITICAL: Only returns keys for the authenticated tenant.
    The full key value is returned only when created; list may mask keys for display.
    """
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.tenant_id == current_tenant.tenant_id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.post(
    "/tenants/{tenant_id}",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key for a tenant"
)
async def create_api_key(
    tenant_id: int,
    api_key_data: ApiKeyCreate,
    db: Annotated[Session, Depends(get_db)],
    current_tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)]
) -> ApiKeyResponse:
    """
    Creates a new API key for a tenant.
    
    CRITICAL: Caller can only create keys for their own tenant (tenant_id must match
    current_tenant.tenant_id). Cross-tenant key creation is not allowed.
    """
    # Phase 9: Validate write action permission
    validate_write_action(current_tenant, db, "create_api_key")
    
    # Only allow creating keys for the current tenant
    if tenant_id != current_tenant.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create API keys for your own tenant"
        )
    
    # Verify tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found"
        )
    
    # Generate API key if not provided
    api_key_value = api_key_data.api_key
    if not api_key_value:
        api_key_value = secrets.token_urlsafe(32)
    
    # Check if API key already exists
    existing = db.query(ApiKey).filter(ApiKey.api_key == api_key_value).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key already exists"
        )
    
    # Create API key
    api_key = ApiKey(
        api_key=api_key_value,
        tenant_id=tenant_id,
        is_active=api_key_data.is_active
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return ApiKeyResponse.model_validate(api_key)


@router.patch(
    "/{key_id}",
    response_model=ApiKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update API key (e.g. activate/deactivate)"
)
async def update_api_key(
    key_id: int,
    data: ApiKeyUpdate,
    current_tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> ApiKeyResponse:
    """Update an API key. Only keys belonging to the current tenant can be updated."""
    validate_write_action(current_tenant, db, "update_api_key")
    key = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.tenant_id == current_tenant.tenant_id)
        .first()
    )
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    if data.is_active is not None:
        key.is_active = data.is_active
    db.commit()
    db.refresh(key)
    return ApiKeyResponse.model_validate(key)


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete (revoke) an API key"
)
async def delete_api_key(
    key_id: int,
    current_tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> None:
    """Delete an API key. Only keys belonging to the current tenant can be deleted."""
    validate_write_action(current_tenant, db, "delete_api_key")
    key = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.tenant_id == current_tenant.tenant_id)
        .first()
    )
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    db.delete(key)
    db.commit()

