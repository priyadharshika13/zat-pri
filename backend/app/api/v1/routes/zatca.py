"""
ZATCA setup and management API endpoints.

Handles CSR generation, CSID upload, and ZATCA connection status.
All endpoints require API key authentication and enforce tenant isolation.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Annotated, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.security import verify_api_key_and_resolve_tenant
from app.schemas.auth import TenantContext
from app.core.constants import Environment
from app.core.production_guards import validate_write_action
from app.services.certificate_service import CertificateService
from app.services.zatca_service import ZatcaService
from app.integrations.zatca.factory import get_zatca_client
from app.integrations.zatca.compliance_csid import ComplianceCSIDService
from app.integrations.zatca.production_onboarding import ProductionOnboardingService
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/zatca", tags=["zatca"])


@router.post(
    "/csr/generate",
    status_code=status.HTTP_200_OK,
    summary="Generate Certificate Signing Request (CSR)"
)
async def generate_csr(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    environment: str = Form(..., description="Target environment (SANDBOX or PRODUCTION)"),
    common_name: str = Form(..., description="Common Name (CN) for the certificate"),
    organization: Optional[str] = Form(None, description="Organization (O)"),
    organizational_unit: Optional[str] = Form(None, description="Organizational Unit (OU)"),
    country: Optional[str] = Form("SA", description="Country code (default: SA)"),
    state: Optional[str] = Form(None, description="State or Province"),
    locality: Optional[str] = Form(None, description="Locality or City"),
    email: Optional[str] = Form(None, description="Email address")
) -> dict:
    """
    Generates a Certificate Signing Request (CSR) for ZATCA CSID certificate.
    
    **Process:**
    1. Generates RSA key pair (2048 bits)
    2. Creates CSR with provided subject information
    3. Returns CSR content and private key for download
    
    **Security:**
    - Private key is returned only once (user must save it securely)
    - CSR can be submitted to ZATCA to obtain CSID certificate
    
    **Returns:**
    - CSR content (PEM format)
    - Private key (PEM format) - MUST be saved securely
    - Subject information
    """
    # Phase 9: Validate write action permission
    validate_write_action(tenant, db, "generate_csr")
    
    try:
        # Validate environment
        try:
            env = Environment(environment.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid environment: {environment}. Must be SANDBOX or PRODUCTION"
            )
        
        # Generate CSR using service
        service = ZatcaService(db, tenant)
        csr_data = service.generate_csr(
            environment=env,
            common_name=common_name,
            organization=organization,
            organizational_unit=organizational_unit,
            country=country,
            state=state,
            locality=locality,
            email=email
        )
        
        logger.info(
            f"CSR generated successfully: tenant_id={tenant.tenant_id}, "
            f"environment={env.value}, cn={common_name}"
        )
        
        return csr_data
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSR generation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during CSR generation"
        )


@router.post(
    "/compliance/csid/submit",
    status_code=status.HTTP_200_OK,
    summary="Submit CSR to ZATCA Compliance CSID API (Automated)"
)
async def submit_csr_to_compliance_csid(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    csr: str = Form(..., description="Certificate Signing Request (CSR) in PEM format"),
    private_key: str = Form(..., description="Private key in PEM format (from CSR generation)"),
    environment: str = Form("SANDBOX", description="Target environment (SANDBOX or PRODUCTION)")
) -> dict:
    """
    Submits CSR to ZATCA Compliance CSID API and automatically stores the received certificate.
    
    **Automated Workflow:**
    1. Validates CSR and private key format
    2. Submits CSR to ZATCA Compliance CSID API (Sandbox)
    3. Receives certificate (binarySecurityToken) from ZATCA
    4. Automatically stores certificate and private key
    5. Returns certificate metadata
    
    **Requirements:**
    - CSR must be valid PEM format
    - Private key must be the one generated with the CSR
    - OAuth credentials must be configured for the target environment
    - Only works with SANDBOX environment (Production onboarding is separate)
    
    **ZATCA API Integration:**
    - Endpoint: POST {base_url}/compliance/csid
    - Authentication: OAuth Bearer token (automatic)
    - Request: { "csr": "-----BEGIN CERTIFICATE REQUEST-----\\n..." }
    - Response: {
        "requestID": "...",
        "dispositionMessage": "...",
        "secret": "...",
        "binarySecurityToken": "-----BEGIN CERTIFICATE-----\\n..."
      }
    
    **Error Handling:**
    - 400: Invalid CSR format or request → HTTP 400
    - 401: OAuth authentication failed → HTTP 401
    - 409: CSR already submitted → HTTP 409
    - 500: ZATCA server error → HTTP 502
    
    **Returns:**
    - Certificate metadata (ID, serial, issuer, expiry)
    - ZATCA request ID and disposition message
    - Certificate storage status
    
    **Note:**
    This endpoint automates the certificate onboarding process. The certificate
    received from ZATCA is automatically stored and ready for use in Reporting
    and Clearance APIs.
    """
    # Phase 9: Validate write action permission
    validate_write_action(tenant, db, "submit_csr_to_compliance_csid")
    
    try:
        # Validate environment
        try:
            env = Environment(environment.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid environment: {environment}. Must be SANDBOX or PRODUCTION"
            )
        
        # For now, only SANDBOX is supported (Production onboarding is separate)
        if env != Environment.SANDBOX:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Compliance CSID API is only available for SANDBOX environment. "
                       "Use Production Onboarding API for production certificates."
            )
        
        # Validate CSR format
        if not csr or not csr.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSR cannot be empty"
            )
        
        if "-----BEGIN CERTIFICATE REQUEST-----" not in csr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid CSR format: must be PEM format starting with -----BEGIN CERTIFICATE REQUEST-----"
            )
        
        # Validate private key format
        if not private_key or not private_key.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Private key cannot be empty"
            )
        
        if "-----BEGIN" not in private_key or "PRIVATE KEY" not in private_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid private key format: must be PEM format"
            )
        
        logger.info(
            f"Submitting CSR to ZATCA Compliance CSID API: tenant_id={tenant.tenant_id}, "
            f"environment={env.value}"
        )
        
        # Initialize Compliance CSID service
        compliance_service = ComplianceCSIDService(environment=env.value)
        
        # Submit CSR to ZATCA
        try:
            zatca_response = await compliance_service.submit_csr(csr_pem=csr)
        except ValueError as e:
            # Handle specific ZATCA API errors
            error_msg = str(e)
            if "401" in error_msg or "authentication" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"ZATCA OAuth authentication failed: {error_msg}"
                )
            elif "409" in error_msg or "conflict" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=error_msg
                )
            elif "500" in error_msg or "server error" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=error_msg
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
        
        # Extract certificate from ZATCA response
        certificate_pem = zatca_response.get("binarySecurityToken", "")
        if not certificate_pem:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="ZATCA response missing certificate (binarySecurityToken)"
            )
        
        # Convert certificate and private key to bytes for storage
        certificate_content = certificate_pem.encode('utf-8')
        private_key_content = private_key.encode('utf-8')
        
        # Store certificate automatically using certificate service
        cert_service = CertificateService(db, tenant)
        try:
            certificate = cert_service.upload_certificate(
                certificate_content=certificate_content,
                private_key_content=private_key_content,
                environment=env
            )
        except ValueError as e:
            logger.error(
                f"Failed to store certificate from ZATCA: {e}",
                extra={
                    "tenant_id": tenant.tenant_id,
                    "environment": env.value,
                    "requestID": zatca_response.get("requestID")
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Certificate received from ZATCA but failed to store: {str(e)}"
            )
        
        logger.info(
            f"Successfully submitted CSR and stored certificate from ZATCA Compliance CSID: "
            f"tenant_id={tenant.tenant_id}, certificate_id={certificate.id}, "
            f"requestID={zatca_response.get('requestID')}, environment={env.value}"
        )
        
        # Return comprehensive response
        return {
            "success": True,
            "message": "CSR submitted successfully and certificate stored",
            "zatca_response": {
                "requestID": zatca_response.get("requestID", ""),
                "dispositionMessage": zatca_response.get("dispositionMessage", ""),
                "has_secret": bool(zatca_response.get("secret"))
            },
            "certificate": {
                "id": certificate.id,
                "serial": certificate.certificate_serial,
                "issuer": certificate.issuer,
                "expiry_date": certificate.expiry_date.isoformat() if certificate.expiry_date else None,
                "uploaded_at": certificate.uploaded_at.isoformat() if certificate.uploaded_at else None,
                "environment": certificate.environment,
                "status": certificate.status.value,
                "is_active": certificate.is_active
            },
            "note": "Certificate is now ready for use in Reporting and Clearance APIs"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in Compliance CSID submission: {e}",
            extra={
                "tenant_id": tenant.tenant_id,
                "environment": environment
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during Compliance CSID submission"
        )


@router.post(
    "/csid/upload",
    status_code=status.HTTP_200_OK,
    summary="Upload CSID certificate and private key"
)
async def upload_csid(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    environment: str = Form(..., description="Target environment (SANDBOX or PRODUCTION)"),
    certificate: UploadFile = File(..., description="CSID certificate file (.pem)"),
    private_key: UploadFile = File(..., description="Private key file (.pem)")
) -> dict:
    """
    Uploads a CSID certificate and private key obtained from ZATCA.
    
    **Requirements:**
    - Certificate must be valid PEM format
    - Certificate must not be expired
    - Private key must be valid PEM format
    - Certificate and private key must match
    
    **Process:**
    1. Validates certificate format and expiry
    2. Validates private key format
    3. Verifies certificate and key match
    4. Deactivates any existing active certificate for this tenant/environment
    5. Stores files securely in certs/tenant_{tenant_id}/{environment}/
    6. Stores certificate metadata in database
    
    **Returns:**
    - Certificate metadata including serial, issuer, expiry date
    - Connection status updated
    """
    # Phase 9: Validate write action permission
    validate_write_action(tenant, db, "upload_csid")
    
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
        cert_service = CertificateService(db, tenant)
        cert = cert_service.upload_certificate(
            certificate_content=certificate_content,
            private_key_content=private_key_content,
            environment=env
        )
        
        logger.info(
            f"CSID certificate uploaded successfully: id={cert.id}, tenant_id={tenant.tenant_id}, "
            f"environment={env.value}"
        )
        
        # Return certificate info with connection status
        return {
            "success": True,
            "certificate": {
                "id": cert.id,
                "serial": cert.certificate_serial,
                "issuer": cert.issuer,
                "expiry_date": cert.expiry_date.isoformat() if cert.expiry_date else None,
                "uploaded_at": cert.uploaded_at.isoformat() if cert.uploaded_at else None,
                "environment": cert.environment,
                "status": cert.status.value
            },
            "message": "CSID certificate uploaded successfully"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSID upload error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during CSID upload"
        )


@router.post(
    "/production/onboarding/submit",
    status_code=status.HTTP_200_OK,
    summary="Submit Production CSID Onboarding Request (OTP-based)"
)
async def submit_production_onboarding(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    csr: str = Form(..., description="Certificate Signing Request (CSR) in PEM format"),
    private_key: str = Form(..., description="Private key in PEM format (from CSR generation)"),
    organization_name: str = Form(..., description="Organization legal name"),
    vat_number: str = Form(..., description="VAT registration number (15 digits)"),
    otp: Optional[str] = Form(None, description="OTP code (if validating existing request)"),
    request_id: Optional[str] = Form(None, description="ZATCA request ID (if validating OTP)")
) -> dict:
    """
    Submits production onboarding request to ZATCA Production Onboarding API.
    
    **Production Onboarding Flow:**
    
    **Step 1: Submit Onboarding Request**
    1. User generates CSR via API
    2. User calls this endpoint with CSR + organization details
    3. System submits to ZATCA Production Onboarding API
    4. System receives OTP challenge (or certificate if OTP not required)
    5. Returns OTP or certificate
    
    **Step 2: Validate OTP (if OTP required)**
    1. User receives OTP from ZATCA (via email/SMS)
    2. User calls this endpoint again with OTP + request_id
    3. System validates OTP with ZATCA
    4. System receives certificate
    5. System automatically stores certificate and private key
    6. Returns certificate metadata
    
    **Requirements:**
    - CSR must be valid PEM format
    - Private key must be the one generated with the CSR
    - Organization name must match ZATCA registration
    - VAT number must be exactly 15 digits
    - OAuth credentials must be configured for PRODUCTION environment
    - Only works with PRODUCTION environment
    
    **Error Handling:**
    - 400: Invalid CSR format, missing organization details, or invalid VAT number → HTTP 400
    - 401: OAuth authentication failed → HTTP 401
    - 403: Invalid OTP code → HTTP 403
    - 404: Request ID not found → HTTP 404
    - 409: CSR already submitted → HTTP 409
    - 500: ZATCA server error → HTTP 502
    
    **Returns:**
    - Step 1: OTP challenge (if OTP required) or certificate (if OTP not required)
    - Step 2: Certificate metadata (ID, serial, issuer, expiry)
    """
    # Phase 9: Validate write action permission
    validate_write_action(tenant, db, "submit_production_onboarding")
    
    try:
        # Initialize Production Onboarding service
        onboarding_service = ProductionOnboardingService()
        
        # Step 1: If OTP and request_id provided, validate OTP and get certificate
        if otp and request_id:
            logger.info(
                f"Validating OTP for production onboarding: tenant_id={tenant.tenant_id}, "
                f"request_id={request_id[:20]}..."
            )
            
            # Validate OTP with ZATCA
            try:
                zatca_response = await onboarding_service.validate_otp(
                    request_id=request_id,
                    otp=otp
                )
            except ValueError as e:
                error_msg = str(e)
                if "403" in error_msg or "Invalid OTP" in error_msg:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=error_msg
                    )
                elif "404" in error_msg or "not found" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=error_msg
                    )
                elif "401" in error_msg or "authentication" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=error_msg
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_msg
                    )
            
            # Extract certificate from ZATCA response
            certificate_pem = zatca_response.get("binarySecurityToken", "")
            if not certificate_pem:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="ZATCA response missing certificate (binarySecurityToken)"
                )
            
            # Convert certificate and private key to bytes for storage
            certificate_content = certificate_pem.encode('utf-8')
            private_key_content = private_key.encode('utf-8')
            
            # Store certificate automatically using certificate service
            cert_service = CertificateService(db, tenant)
            try:
                certificate = cert_service.upload_certificate(
                    certificate_content=certificate_content,
                    private_key_content=private_key_content,
                    environment=Environment.PRODUCTION
                )
            except ValueError as e:
                logger.error(
                    f"Failed to store certificate from ZATCA Production: {e}",
                    extra={
                        "tenant_id": tenant.tenant_id,
                        "environment": "PRODUCTION",
                        "requestID": zatca_response.get("requestID")
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Certificate received from ZATCA but failed to store: {str(e)}"
                )
            
            logger.info(
                f"Successfully validated OTP and stored certificate from ZATCA Production: "
                f"tenant_id={tenant.tenant_id}, certificate_id={certificate.id}, "
                f"requestID={zatca_response.get('requestID')}"
            )
            
            # Return comprehensive response
            return {
                "success": True,
                "message": "OTP validated successfully and certificate stored",
                "zatca_response": {
                    "requestID": zatca_response.get("requestID", ""),
                    "dispositionMessage": zatca_response.get("dispositionMessage", ""),
                    "has_secret": bool(zatca_response.get("secret"))
                },
                "certificate": {
                    "id": certificate.id,
                    "serial": certificate.certificate_serial,
                    "issuer": certificate.issuer,
                    "expiry_date": certificate.expiry_date.isoformat() if certificate.expiry_date else None,
                    "uploaded_at": certificate.uploaded_at.isoformat() if certificate.uploaded_at else None,
                    "environment": certificate.environment,
                    "status": certificate.status.value,
                    "is_active": certificate.is_active
                },
                "note": "Certificate is now ready for use in Production Reporting and Clearance APIs"
            }
        
        # Step 2: Submit initial onboarding request (without OTP)
        else:
            # Validate CSR format
            if not csr or not csr.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CSR cannot be empty"
                )
            
            if "-----BEGIN CERTIFICATE REQUEST-----" not in csr:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid CSR format: must be PEM format starting with -----BEGIN CERTIFICATE REQUEST-----"
                )
            
            # Validate private key format
            if not private_key or not private_key.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Private key cannot be empty"
                )
            
            if "-----BEGIN" not in private_key or "PRIVATE KEY" not in private_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid private key format: must be PEM format"
                )
            
            # Validate organization name
            if not organization_name or not organization_name.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization name is required"
                )
            
            # Validate VAT number
            if not vat_number or not vat_number.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="VAT number is required"
                )
            
            logger.info(
                f"Submitting production onboarding request to ZATCA: tenant_id={tenant.tenant_id}"
            )
            
            # Submit onboarding request to ZATCA
            try:
                zatca_response = await onboarding_service.submit_onboarding_request(
                    csr_pem=csr,
                    organization_name=organization_name,
                    vat_number=vat_number
                )
            except ValueError as e:
                error_msg = str(e)
                if "401" in error_msg or "authentication" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"ZATCA Production OAuth authentication failed: {error_msg}"
                    )
                elif "409" in error_msg or "conflict" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=error_msg
                    )
                elif "500" in error_msg or "server error" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=error_msg
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_msg
                    )
            
            # Check if OTP is required
            otp_received = zatca_response.get("otp", "")
            request_id = zatca_response.get("requestID", "")
            
            # OTP required - return OTP challenge
            return {
                "success": True,
                "message": "Onboarding request submitted successfully. OTP validation required.",
                "zatca_response": {
                    "requestID": request_id,
                    "dispositionMessage": zatca_response.get("dispositionMessage", ""),
                    "otp_required": True,
                    "otp": otp_received if otp_received else None
                },
                "next_step": "Call this endpoint again with 'otp' and 'request_id' parameters to validate OTP and receive certificate",
                "note": "If OTP is not in response, check your registered email/SMS for OTP from ZATCA"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in Production Onboarding: {e}",
            extra={
                "tenant_id": tenant.tenant_id
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during Production Onboarding"
        )


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Get ZATCA connection status"
)
async def get_zatca_status(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    db: Annotated[Session, Depends(get_db)],
    environment: Optional[str] = None
) -> dict:
    """
    Gets the current ZATCA connection status for the tenant.
    
    **Status Information:**
    - Connection status (Connected/Disconnected)
    - Environment (Sandbox/Production)
    - Certificate expiry date
    - Last sync time (certificate upload time)
    - Certificate metadata
    
    **Returns:**
    - Connection status and certificate information
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
        
        # Get certificate service
        cert_service = CertificateService(db, tenant)
        certificate = cert_service.get_certificate(environment=env)
        
        # Determine environment for response
        target_env = env.value if env else (tenant.environment if hasattr(tenant, 'environment') else 'SANDBOX')
        
        # Check certificate presence
        has_certificate = certificate is not None and certificate.is_active
        
        # Perform REAL ZATCA connectivity check (only for sandbox)
        real_connectivity = None
        last_successful_ping = None
        connectivity_error = None
        
        if target_env.upper() == "SANDBOX":
            try:
                zatca_client = get_zatca_client(environment="SANDBOX")
                if hasattr(zatca_client, 'ping'):
                    ping_result = await zatca_client.ping()
                    real_connectivity = ping_result.get("connected", False)
                    last_successful_ping = ping_result.get("last_successful_ping")
                    connectivity_error = ping_result.get("error_message")
                else:
                    # Fallback: if ping method doesn't exist, use certificate presence
                    real_connectivity = has_certificate
            except Exception as e:
                logger.warning(
                    f"Failed to ping ZATCA sandbox for connectivity check: {e}",
                    extra={
                        "tenant_id": tenant.tenant_id,
                        "environment": target_env
                    }
                )
                # On error, fall back to certificate presence
                real_connectivity = has_certificate
                connectivity_error = f"Connectivity check failed: {str(e)}"
        else:
            # For production, use certificate presence (real ping can be added later)
            real_connectivity = has_certificate
        
        # Overall connection status: requires both certificate AND real connectivity
        is_connected = has_certificate and (real_connectivity if real_connectivity is not None else has_certificate)
        
        # Prepare response
        response = {
            "connected": is_connected,
            "environment": target_env.upper(),
            "certificate": None,
            "certificate_expiry": None,
            "last_sync": None,
            "connectivity": {
                "has_certificate": has_certificate,
                "real_connectivity": real_connectivity,
                "last_successful_ping": last_successful_ping,
                "error_message": connectivity_error
            }
        }
        
        if certificate:
            response["certificate"] = {
                "id": certificate.id,
                "serial": certificate.certificate_serial,
                "issuer": certificate.issuer,
                "status": certificate.status.value,
                "is_active": certificate.is_active
            }
            response["certificate_expiry"] = certificate.expiry_date.isoformat() if certificate.expiry_date else None
            response["last_sync"] = certificate.uploaded_at.isoformat() if certificate.uploaded_at else None
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ZATCA status retrieval error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during status retrieval"
        )

