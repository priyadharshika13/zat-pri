"""
ZATCA Production CSID Onboarding integration service.

Handles production certificate onboarding via ZATCA Production Onboarding API.
Implements OTP-based onboarding flow with CSR submission, OTP validation, and certificate retrieval.

CRITICAL: This is separate from sandbox Compliance CSID API.
Production onboarding requires OTP validation and organization details.
"""

import logging
import base64
from typing import Dict, Optional
from datetime import datetime

import httpx

from app.core.config import get_settings
from app.integrations.zatca.oauth_service import get_oauth_service

logger = logging.getLogger(__name__)


class ProductionOnboardingService:
    """
    Service for ZATCA Production CSID Onboarding API integration.
    
    Handles OTP-based production certificate onboarding flow:
    1. Submit CSR with organization details
    2. Receive OTP challenge
    3. Validate OTP
    4. Receive certificate
    5. Store certificate securely
    """
    
    def __init__(self):
        """Initializes Production Onboarding service."""
        settings = get_settings()
        
        # Production base URL (CRITICAL: Must use production endpoint)
        self.base_url = settings.zatca_production_base_url
        
        # Production onboarding endpoint (per ZATCA Developer Portal)
        self.onboarding_endpoint = "/onboarding/csid"
        
        # Timeout configuration (production may be slower)
        self.timeout = httpx.Timeout(60.0, connect=15.0)
        
        # OAuth service for production authentication
        self.oauth_service = get_oauth_service(environment="PRODUCTION")
    
    async def _get_auth_headers(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        Gets HTTP headers with OAuth authentication.
        
        Args:
            force_refresh: If True, force token refresh
            
        Returns:
            Dictionary with Content-Type, Accept, and Authorization headers
            
        Raises:
            ValueError: If OAuth token cannot be obtained
        """
        try:
            token = await self.oauth_service.get_access_token(force_refresh=force_refresh)
            return {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"{token.token_type} {token.access_token}"
            }
        except ValueError as e:
            logger.error(f"Failed to get OAuth token for Production Onboarding: {e}")
            raise ValueError(
                f"ZATCA Production OAuth authentication failed. "
                f"Please verify OAuth credentials are configured correctly. "
                f"Error: {str(e)}"
            ) from e
    
    def _prepare_csr_for_submission(self, csr_pem: str) -> str:
        """
        Prepares CSR for ZATCA Production API submission.
        
        Args:
            csr_pem: CSR in PEM format
            
        Returns:
            Prepared CSR string (cleaned)
        """
        return csr_pem.strip()
    
    async def submit_onboarding_request(
        self,
        csr_pem: str,
        organization_name: str,
        vat_number: str,
        retry_on_401: bool = True
    ) -> Dict[str, str]:
        """
        Submits production onboarding request with CSR and organization details.
        
        **ZATCA Production API Specification:**
        - Endpoint: POST {production_base_url}/onboarding/csid
        - Headers: Authorization Bearer token, Content-Type: application/json
        - Body: {
            "csr": "-----BEGIN CERTIFICATE REQUEST-----\\n...",
            "organizationName": "...",
            "vatNumber": "..."
          }
        - Response: {
            "requestID": "...",
            "dispositionMessage": "...",
            "otp": "..." (if OTP required)
          }
        
        **Error Handling:**
        - 400: Invalid CSR format, missing organization details, or invalid VAT number
        - 401: OAuth authentication failed (auto-retry once)
        - 409: CSR already submitted or duplicate request
        - 500: ZATCA server error
        
        Args:
            csr_pem: Certificate Signing Request in PEM format
            organization_name: Organization legal name
            vat_number: VAT registration number (15 digits)
            retry_on_401: If True, retry once on 401 after token refresh
            
        Returns:
            Dictionary containing:
            - requestID: ZATCA request identifier
            - dispositionMessage: Status message from ZATCA
            - otp: OTP code (if OTP validation required)
            
        Raises:
            ValueError: If CSR is invalid, OAuth fails, or request fails
            httpx.HTTPStatusError: For HTTP errors (400, 409, 500)
        """
        if not csr_pem or not csr_pem.strip():
            raise ValueError("CSR cannot be empty")
        
        if not organization_name or not organization_name.strip():
            raise ValueError("Organization name is required")
        
        if not vat_number or not vat_number.strip():
            raise ValueError("VAT number is required")
        
        # Validate VAT number format (15 digits)
        vat_cleaned = vat_number.strip().replace("-", "").replace(" ", "")
        if not vat_cleaned.isdigit() or len(vat_cleaned) != 15:
            raise ValueError(
                f"Invalid VAT number format: {vat_number}. "
                f"VAT number must be exactly 15 digits."
            )
        
        # Validate CSR format
        if "-----BEGIN CERTIFICATE REQUEST-----" not in csr_pem:
            raise ValueError(
                "Invalid CSR format: must be PEM format starting with "
                "-----BEGIN CERTIFICATE REQUEST-----"
            )
        
        # Prepare CSR for submission
        csr_prepared = self._prepare_csr_for_submission(csr_pem)
        
        # Build request URL
        request_url = f"{self.base_url}{self.onboarding_endpoint}"
        
        logger.info(
            f"Submitting production onboarding request to ZATCA",
            extra={
                "environment": "PRODUCTION",
                "endpoint": request_url,
                "organization_name": organization_name,
                "vat_number": vat_cleaned[:3] + "***" + vat_cleaned[-3:]  # Masked for logging
            }
        )
        
        # Prepare request payload
        payload = {
            "csr": csr_prepared,
            "organizationName": organization_name.strip(),
            "vatNumber": vat_cleaned
        }
        
        token_refreshed = False
        last_exception = None
        
        try:
            # Get OAuth token and headers
            headers = await self._get_auth_headers(force_refresh=False)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    request_url,
                    json=payload,
                    headers=headers
                )
                
                # Handle 401 Unauthorized - refresh token and retry once
                if response.status_code == 401 and retry_on_401 and not token_refreshed:
                    logger.warning(
                        f"Received 401 Unauthorized, refreshing OAuth token and retrying",
                        extra={
                            "environment": "PRODUCTION",
                            "status_code": 401
                        }
                    )
                    token_refreshed = True
                    headers = await self._get_auth_headers(force_refresh=True)
                    
                    # Retry request with refreshed token
                    response = await client.post(
                        request_url,
                        json=payload,
                        headers=headers
                    )
                
                # Check for errors
                if response.status_code == 400:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_message = error_data.get("message", error_data.get("error", response.text[:200]))
                    logger.error(
                        f"ZATCA Production Onboarding API returned 400 Bad Request: {error_message}",
                        extra={
                            "environment": "PRODUCTION",
                            "status_code": 400,
                            "error": error_message
                        }
                    )
                    raise ValueError(
                        f"Invalid request format. ZATCA error: {error_message}"
                    )
                
                if response.status_code == 409:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_message = error_data.get("message", error_data.get("error", "CSR already submitted or duplicate request"))
                    logger.warning(
                        f"ZATCA Production Onboarding API returned 409 Conflict: {error_message}",
                        extra={
                            "environment": "PRODUCTION",
                            "status_code": 409,
                            "error": error_message
                        }
                    )
                    raise ValueError(
                        f"Onboarding request conflict. This CSR may have already been submitted. "
                        f"ZATCA error: {error_message}"
                    )
                
                if response.status_code == 500:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_message = error_data.get("message", error_data.get("error", "ZATCA server error"))
                    logger.error(
                        f"ZATCA Production Onboarding API returned 500 Internal Server Error: {error_message}",
                        extra={
                            "environment": "PRODUCTION",
                            "status_code": 500,
                            "error": error_message
                        }
                    )
                    raise ValueError(
                        f"ZATCA server error. Please try again later. Error: {error_message}"
                    )
                
                # Raise for other HTTP errors
                response.raise_for_status()
                
                # Parse successful response
                data = response.json()
                
                # Validate response structure
                if "requestID" not in data:
                    logger.error(
                        f"Invalid ZATCA Production Onboarding response: missing requestID",
                        extra={
                            "environment": "PRODUCTION",
                            "response_keys": list(data.keys())
                        }
                    )
                    raise ValueError(
                        "Invalid response from ZATCA Production Onboarding API: missing requestID"
                    )
                
                logger.info(
                    f"Successfully submitted production onboarding request to ZATCA",
                    extra={
                        "environment": "PRODUCTION",
                        "requestID": data.get("requestID"),
                        "dispositionMessage": data.get("dispositionMessage", ""),
                        "has_otp": "otp" in data
                    }
                )
                
                return {
                    "requestID": data.get("requestID", ""),
                    "dispositionMessage": data.get("dispositionMessage", ""),
                    "otp": data.get("otp", "")  # OTP may be in response or sent separately
                }
        
        except httpx.TimeoutException as e:
            logger.error(
                f"Timeout submitting production onboarding request to ZATCA",
                extra={
                    "environment": "PRODUCTION",
                    "timeout": self.timeout
                }
            )
            raise ValueError(
                f"Request to ZATCA Production Onboarding API timed out. "
                f"Please check network connectivity and try again."
            ) from e
        
        except httpx.HTTPStatusError as e:
            # Already handled above, but catch any other status errors
            logger.error(
                f"HTTP error submitting production onboarding request: {e.response.status_code}",
                extra={
                    "environment": "PRODUCTION",
                    "status_code": e.response.status_code,
                    "error": e.response.text[:200]
                }
            )
            raise ValueError(
                f"ZATCA Production Onboarding API returned error {e.response.status_code}: "
                f"{e.response.text[:200]}"
            ) from e
        
        except ValueError:
            # Re-raise ValueError as-is (already formatted)
            raise
        
        except Exception as e:
            logger.error(
                f"Unexpected error submitting production onboarding request: {e}",
                extra={
                    "environment": "PRODUCTION",
                    "error": str(e)
                },
                exc_info=True
            )
            raise ValueError(
                f"Failed to submit production onboarding request: {str(e)}"
            ) from e
    
    async def validate_otp(
        self,
        request_id: str,
        otp: str,
        retry_on_401: bool = True
    ) -> Dict[str, str]:
        """
        Validates OTP and retrieves production certificate.
        
        **ZATCA Production API Specification:**
        - Endpoint: POST {production_base_url}/onboarding/csid/validate-otp
        - Headers: Authorization Bearer token, Content-Type: application/json
        - Body: {
            "requestID": "...",
            "otp": "..."
          }
        - Response: {
            "requestID": "...",
            "dispositionMessage": "...",
            "secret": "...",
            "binarySecurityToken": "-----BEGIN CERTIFICATE-----\\n..."
          }
        
        **Error Handling:**
        - 400: Invalid OTP format
        - 401: OAuth authentication failed (auto-retry once)
        - 403: Invalid OTP code
        - 404: Request ID not found
        - 500: ZATCA server error
        
        Args:
            request_id: ZATCA request ID from onboarding submission
            otp: OTP code received from ZATCA
            retry_on_401: If True, retry once on 401 after token refresh
            
        Returns:
            Dictionary containing:
            - requestID: ZATCA request identifier
            - dispositionMessage: Status message from ZATCA
            - secret: Certificate secret (for revocation/management)
            - binarySecurityToken: Certificate in PEM format
            
        Raises:
            ValueError: If OTP is invalid, OAuth fails, or request fails
            httpx.HTTPStatusError: For HTTP errors (400, 403, 404, 500)
        """
        if not request_id or not request_id.strip():
            raise ValueError("Request ID cannot be empty")
        
        if not otp or not otp.strip():
            raise ValueError("OTP cannot be empty")
        
        # Build request URL
        request_url = f"{self.base_url}{self.onboarding_endpoint}/validate-otp"
        
        logger.info(
            f"Validating OTP for production onboarding",
            extra={
                "environment": "PRODUCTION",
                "endpoint": request_url,
                "requestID": request_id
            }
        )
        
        # Prepare request payload
        payload = {
            "requestID": request_id.strip(),
            "otp": otp.strip()
        }
        
        token_refreshed = False
        
        try:
            # Get OAuth token and headers
            headers = await self._get_auth_headers(force_refresh=False)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    request_url,
                    json=payload,
                    headers=headers
                )
                
                # Handle 401 Unauthorized - refresh token and retry once
                if response.status_code == 401 and retry_on_401 and not token_refreshed:
                    logger.warning(
                        f"Received 401 Unauthorized, refreshing OAuth token and retrying",
                        extra={
                            "environment": "PRODUCTION",
                            "status_code": 401
                        }
                    )
                    token_refreshed = True
                    headers = await self._get_auth_headers(force_refresh=True)
                    
                    # Retry request with refreshed token
                    response = await client.post(
                        request_url,
                        json=payload,
                        headers=headers
                    )
                
                # Check for errors
                if response.status_code == 400:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_message = error_data.get("message", error_data.get("error", response.text[:200]))
                    logger.error(
                        f"ZATCA Production OTP validation returned 400 Bad Request: {error_message}",
                        extra={
                            "environment": "PRODUCTION",
                            "status_code": 400,
                            "error": error_message
                        }
                    )
                    raise ValueError(
                        f"Invalid OTP format. ZATCA error: {error_message}"
                    )
                
                if response.status_code == 403:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_message = error_data.get("message", error_data.get("error", "Invalid OTP code"))
                    logger.error(
                        f"ZATCA Production OTP validation returned 403 Forbidden: {error_message}",
                        extra={
                            "environment": "PRODUCTION",
                            "status_code": 403,
                            "error": error_message
                        }
                    )
                    raise ValueError(
                        f"Invalid OTP code. Please verify the OTP and try again. "
                        f"ZATCA error: {error_message}"
                    )
                
                if response.status_code == 404:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_message = error_data.get("message", error_data.get("error", "Request ID not found"))
                    logger.error(
                        f"ZATCA Production OTP validation returned 404 Not Found: {error_message}",
                        extra={
                            "environment": "PRODUCTION",
                            "status_code": 404,
                            "error": error_message
                        }
                    )
                    raise ValueError(
                        f"Request ID not found. The onboarding request may have expired. "
                        f"ZATCA error: {error_message}"
                    )
                
                if response.status_code == 500:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_message = error_data.get("message", error_data.get("error", "ZATCA server error"))
                    logger.error(
                        f"ZATCA Production OTP validation returned 500 Internal Server Error: {error_message}",
                        extra={
                            "environment": "PRODUCTION",
                            "status_code": 500,
                            "error": error_message
                        }
                    )
                    raise ValueError(
                        f"ZATCA server error. Please try again later. Error: {error_message}"
                    )
                
                # Raise for other HTTP errors
                response.raise_for_status()
                
                # Parse successful response
                data = response.json()
                
                # Validate response structure
                required_fields = ["requestID", "binarySecurityToken"]
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    logger.error(
                        f"Invalid ZATCA Production OTP validation response: missing fields {missing_fields}",
                        extra={
                            "environment": "PRODUCTION",
                            "response_keys": list(data.keys()),
                            "missing_fields": missing_fields
                        }
                    )
                    raise ValueError(
                        f"Invalid response from ZATCA Production OTP validation: "
                        f"missing required fields {missing_fields}"
                    )
                
                # Extract certificate (binarySecurityToken)
                certificate_pem = data.get("binarySecurityToken", "")
                if not certificate_pem or "-----BEGIN CERTIFICATE-----" not in certificate_pem:
                    logger.error(
                        f"Invalid certificate format in ZATCA Production response",
                        extra={
                            "environment": "PRODUCTION",
                            "certificate_preview": certificate_pem[:100] if certificate_pem else "empty"
                        }
                    )
                    raise ValueError("Invalid certificate format received from ZATCA")
                
                logger.info(
                    f"Successfully validated OTP and received certificate from ZATCA Production",
                    extra={
                        "environment": "PRODUCTION",
                        "requestID": data.get("requestID"),
                        "dispositionMessage": data.get("dispositionMessage", ""),
                        "certificate_length": len(certificate_pem)
                    }
                )
                
                return {
                    "requestID": data.get("requestID", ""),
                    "dispositionMessage": data.get("dispositionMessage", ""),
                    "secret": data.get("secret", ""),  # May be empty in some responses
                    "binarySecurityToken": certificate_pem
                }
        
        except httpx.TimeoutException as e:
            logger.error(
                f"Timeout validating OTP with ZATCA Production",
                extra={
                    "environment": "PRODUCTION",
                    "timeout": self.timeout
                }
            )
            raise ValueError(
                f"Request to ZATCA Production OTP validation timed out. "
                f"Please check network connectivity and try again."
            ) from e
        
        except httpx.HTTPStatusError as e:
            # Already handled above, but catch any other status errors
            logger.error(
                f"HTTP error validating OTP: {e.response.status_code}",
                extra={
                    "environment": "PRODUCTION",
                    "status_code": e.response.status_code,
                    "error": e.response.text[:200]
                }
            )
            raise ValueError(
                f"ZATCA Production OTP validation returned error {e.response.status_code}: "
                f"{e.response.text[:200]}"
            ) from e
        
        except ValueError:
            # Re-raise ValueError as-is (already formatted)
            raise
        
        except Exception as e:
            logger.error(
                f"Unexpected error validating OTP: {e}",
                extra={
                    "environment": "PRODUCTION",
                    "error": str(e)
                },
                exc_info=True
            )
            raise ValueError(f"Failed to validate OTP: {str(e)}") from e

