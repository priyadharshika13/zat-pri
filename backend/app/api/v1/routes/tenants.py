"""
Tenant management API endpoints.

Handles tenant creation and retrieval.
All endpoints require API key authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy.orm import Session

from app.core.security import verify_api_key_and_resolve_tenant
from app.schemas.tenant import TenantCreate, TenantResponse, TenantContext
from app.db.session import get_db
from app.models.tenant import Tenant

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant"
)
async def create_tenant(
    tenant_data: TenantCreate,
    db: Annotated[Session, Depends(get_db)],
    current_tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)]
) -> TenantResponse:
    """
    Creates a new tenant.
    
    Requires API key authentication.
    In production, this should be restricted to admin users only.
    """
    # Check if tenant with same VAT number already exists
    existing = db.query(Tenant).filter(Tenant.vat_number == tenant_data.vat_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with VAT number {tenant_data.vat_number} already exists"
        )
    
    # Create new tenant
    tenant = Tenant(
        company_name=tenant_data.company_name,
        vat_number=tenant_data.vat_number,
        environment=tenant_data.environment.value,
        is_active=tenant_data.is_active
    )
    
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    
    return TenantResponse.model_validate(tenant)


@router.get(
    "/me",
    response_model=TenantResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current tenant information"
)
async def get_current_tenant(
    current_tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> TenantResponse:
    """
    Returns the current tenant information based on the API key.
    
    CRITICAL: Only returns the tenant associated with the API key used.
    No cross-tenant access is possible.
    """
    tenant = db.query(Tenant).filter(Tenant.id == current_tenant.tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return TenantResponse.model_validate(tenant)

