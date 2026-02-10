"""
Certificate management API endpoints.

Handles certificate upload, retrieval, and deletion.
All endpoints require API key authentication and enforce tenant isolation.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Annotated, Optional
from sqlalchemy.orm import Session

from app.core.security import verify_api_key_and_resolve_tenant
from app.schemas.auth import TenantContext
from app.schemas.certificate import CertificateResponse, CertificateListResponse
from app.core.constants import Environment
from app.core.production_guards import validate_write_action
from app.services.certificate_service import CertificateService
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.post(
    "/upload",
    response_model=CertificateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload certificate and private key"
)
async def upload_certificate(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    environment: str = Form(..., description="Target environment (SANDBOX or PRODUCTION)"),
    certificate: UploadFile = File(..., description="Certificate file (.pem)"),
    private_key: UploadFile = File(..., description="Private key file (.pem)")
) -> CertificateResponse:
    """
    Uploads a certificate and private key for Phase-2 invoice signing.
    
    **Requirements:**
    - Certificate must be valid PEM format
    - Certificate must not be expired
    - Private key must be valid PEM format
    - Only one active certificate per tenant per environment
    
    **Process:**
    1. Validates certificate format and expiry
    2. Validates private key format
    3. Deactivates any existing active certificate for this tenant/environment
    4. Stores files securely in certs/tenant_{tenant_id}/{environment}/
    5. Stores certificate metadata in database
    
    **Security:**
    - Files are stored with secure permissions (600: owner read/write only)
    - Tenant isolation enforced (tenant A cannot access tenant B's certificates)
    - Certificate metadata stored in DB (not raw keys)
    
    **Returns:**
    - Certificate metadata including serial, issuer, expiry date
    """
    # Phase 9: Validate write action permission
    validate_write_action(tenant, db, "upload_certificate")
    
    try:
        # Validate environment
        try:
            env = Environment(environment.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid environment: {environment}. Must be SANDBOX or PRODUCTION"
            )
        
        # Validate file types
        if not certificate.filename or not certificate.filename.endswith(('.pem', '.crt', '.cer')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Certificate file must be .pem, .crt, or .cer format"
            )
        
        if not private_key.filename or not private_key.filename.endswith(('.pem', '.key')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Private key file must be .pem or .key format"
            )
        
        # Read file contents
        certificate_content = await certificate.read()
        private_key_content = await private_key.read()
        
        if not certificate_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Certificate file is empty"
            )
        
        if not private_key_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Private key file is empty"
            )
        
        # Upload certificate using service
        service = CertificateService(db, tenant)
        cert = service.upload_certificate(
            certificate_content=certificate_content,
            private_key_content=private_key_content,
            environment=env
        )
        
        logger.info(
            f"Certificate uploaded successfully: id={cert.id}, tenant_id={tenant.tenant_id}, "
            f"environment={env.value}"
        )
        
        return CertificateResponse.model_validate(cert)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Certificate upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during certificate upload"
        )


@router.get(
    "",
    response_model=CertificateListResponse,
    status_code=status.HTTP_200_OK,
    summary="List certificates for current tenant"
)
async def list_certificates(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    environment: Optional[str] = None
) -> CertificateListResponse:
    """
    Lists all certificates for the current tenant.
    
    **CRITICAL: Only returns certificates belonging to the authenticated tenant.**
    
    **Optional Filters:**
    - environment: Filter by environment (SANDBOX or PRODUCTION)
    
    **Returns:**
    - List of certificates with metadata
    - Total count
    - Active and expired counts
    """
    try:
        # Validate environment if provided
        env = None
        if environment:
            try:
                env = Environment(environment.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid environment: {environment}. Must be SANDBOX or PRODUCTION"
                )
        
        service = CertificateService(db, tenant)
        certificates = service.list_certificates(environment=env)
        
        # Calculate counts
        active_count = sum(1 for c in certificates if c.is_active)
        expired_count = sum(1 for c in certificates if c.status.value == "EXPIRED")
        
        return CertificateListResponse(
            certificates=[CertificateResponse.model_validate(c) for c in certificates],
            total=len(certificates),
            active_count=active_count,
            expired_count=expired_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Certificate list error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during certificate retrieval"
        )


@router.get(
    "/current",
    response_model=CertificateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current active certificate"
)
async def get_current_certificate(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    environment: Optional[str] = None
) -> CertificateResponse:
    """
    Gets the current active certificate for the tenant.
    
    **CRITICAL: Only returns certificate belonging to the authenticated tenant.**
    
    **Optional Parameters:**
    - environment: Filter by environment (defaults to tenant's environment)
    
    **Returns:**
    - Active certificate metadata or 404 if not found
    """
    try:
        # Validate environment if provided
        env = None
        if environment:
            try:
                env = Environment(environment.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid environment: {environment}. Must be SANDBOX or PRODUCTION"
                )
        
        service = CertificateService(db, tenant)
        certificate = service.get_certificate(environment=env)
        
        if not certificate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active certificate found for this tenant"
            )
        
        return CertificateResponse.model_validate(certificate)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Certificate retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during certificate retrieval"
        )


@router.delete(
    "/{certificate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete certificate"
)
async def delete_certificate(
    certificate_id: int,
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)]
) -> None:
    # Phase 9: Validate write action permission
    validate_write_action(tenant, db, "delete_certificate")
    """
    Deletes a certificate and its associated files.
    
    **CRITICAL:**
    - Only deletes certificates belonging to the authenticated tenant
    - Securely removes certificate and private key files from filesystem
    - Removes database record
    
    **Security:**
    - Tenant isolation enforced
    - Files are permanently deleted
    - Cannot delete certificates belonging to other tenants
    
    **Returns:**
    - 204 No Content on success
    - 404 if certificate not found
    """
    try:
        service = CertificateService(db, tenant)
        deleted = service.delete_certificate(certificate_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certificate {certificate_id} not found"
            )
        
        logger.info(
            f"Certificate deleted: id={certificate_id}, tenant_id={tenant.tenant_id}"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Certificate deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during certificate deletion"
        )

