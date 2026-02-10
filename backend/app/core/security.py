"""
API authentication and authorization.

Handles API key validation and tenant context resolution for incoming requests.
Resolves tenant context from API keys and attaches it to request state.
Does not manage user sessions, OAuth tokens, or role-based access control.
"""

from fastapi import HTTPException, status, Request
from typing import Annotated
# from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.tenant import Tenant
from app.schemas.auth import TenantContext


async def verify_api_key_and_resolve_tenant(
    request: Request
) -> TenantContext:
    """
    Validates API key and resolves tenant context.
    
    CRITICAL: This function:
    1. Validates the API key exists and is active
    2. Resolves the associated tenant (must be active)
    3. Attaches tenant context to request.state.tenant
    4. Returns TenantContext for use in endpoints
    
    Args:
        request: FastAPI request object (injected automatically)
        
    Returns:
        TenantContext with tenant_id, company_name, vat_number, environment
        
    Raises:
        HTTPException: If API key is missing, invalid, or tenant is inactive
    """
    # Extract API key from header
    x_api_key = request.headers.get("X-API-Key")
    
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required"
        )
    
    # Get database session
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        # Look up API key in database
        api_key_obj = db.query(ApiKey).filter(
            ApiKey.api_key == x_api_key,
            ApiKey.is_active == True
        ).first()
        
        if not api_key_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or inactive API key"
            )
        
        # Join with tenant and verify tenant is active
        tenant = db.query(Tenant).filter(
            Tenant.id == api_key_obj.tenant_id,
            Tenant.is_active == True
        ).first()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant associated with API key is inactive"
            )
        
        # Update last_used_at
        from datetime import datetime
        api_key_obj.last_used_at = datetime.utcnow()
        db.commit()
        
        # Create tenant context
        tenant_context = TenantContext(
            tenant_id=tenant.id,
            company_name=tenant.company_name,
            vat_number=tenant.vat_number,
            environment=tenant.environment
        )
        
        # Attach to request state for easy access across services
        request.state.tenant = tenant_context
        
        return tenant_context
    finally:
        db.close()


# Backward compatibility: Keep old function for gradual migration
async def verify_api_key(
    request: Request
) -> str:
    """
    Legacy API key validation (backward compatibility).
    
    DEPRECATED: Use verify_api_key_and_resolve_tenant instead.
    This function is kept for backward compatibility during migration.
    
    Args:
        request: FastAPI request object (injected automatically)
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Extract API key from header
    x_api_key = request.headers.get("X-API-Key")
    
    settings = get_settings()
    
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required"
        )
    
    # Try database first (new multi-tenant approach)
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        api_key_obj = db.query(ApiKey).filter(
            ApiKey.api_key == x_api_key,
            ApiKey.is_active == True
        ).first()
        
        if api_key_obj:
            return x_api_key  # Valid database API key
    finally:
        db.close()
    
    # Fallback to config-based validation (legacy)
    if x_api_key in settings.valid_api_keys:
        return x_api_key
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )

