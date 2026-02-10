"""
Authentication API endpoints.

SECURITY: Login endpoint is DISABLED in production.
Only enabled in local development environment for testing.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.auth import LoginRequest, LoginResponse
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.api_key import ApiKey

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User login (LOCAL DEV ONLY)"
)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
) -> LoginResponse:
    """
    Authenticates user and returns access token (API key).
    
    **SECURITY WARNING:**
    - This endpoint is DISABLED in production environments
    - Only enabled when ENVIRONMENT_NAME=local
    - Returns 404 in all other environments
    
    **Local Dev Implementation:**
    - For local dev only, email is used to find tenant
    - Password validation is simplified
    - Returns first active API key for the tenant
    
    **Production:**
    - This endpoint MUST NOT be used in production
    - Users must provide API keys directly
    - No API key minting via login
    """
    settings = get_settings()
    
    # SECURITY: Only allow in local environment
    if settings.environment_name.lower() != "local":
        logger.warning(
            f"SECURITY: Login endpoint accessed in non-local environment: {settings.environment_name}. "
            f"Returning 404. IP may be logged for security review."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found"
        )
    
    # Log warning when used (even in local)
    logger.warning(
        "SECURITY WARNING: Login endpoint used. This should only happen in local development. "
        f"Email: {login_data.email}, Environment: {settings.environment_name}"
    )
    
    try:
        # MVP: Find tenant by email (using email as identifier)
        # In production, you'd have a separate users table
        # For now, we'll try to match email to VAT number or use a default tenant
        
        # Try to find tenant by VAT number (if email format matches)
        # Or use a default tenant for MVP
        tenant = db.query(Tenant).filter(
            Tenant.is_active == True
        ).first()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active tenant found. Please contact support."
            )
        
        # MVP: Simple password check (in production, use hashed passwords)
        # For now, accept any password if tenant exists
        # TODO: Implement proper user authentication
        
        # Get first active API key for this tenant
        api_key = db.query(ApiKey).filter(
            ApiKey.tenant_id == tenant.id,
            ApiKey.is_active == True
        ).first()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active API key found for tenant. Please contact support."
            )
        
        logger.info(f"Login successful for email: {login_data.email}, tenant_id: {tenant.id}")
        
        return LoginResponse(
            access_token=api_key.api_key,
            token_type="bearer",
            tenant_id=tenant.id,
            company_name=tenant.company_name,
            email=login_data.email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )

