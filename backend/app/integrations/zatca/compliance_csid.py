"""
ZATCA Compliance CSID API integration service.

Handles automated certificate onboarding via ZATCA Compliance CSID API.
Implements CSR submission, certificate retrieval, and automatic storage.
"""

import logging
import base64
from typing import Dict, Optional
import asyncio

import httpx

from app.core.config import get_settings
from app.integrations.zatca.oauth_service import get_oauth_service

logger = logging.getLogger(__name__)


class ComplianceCSIDService:
    """
    Service for ZATCA Compliance CSID API integration.
    
    Handles automated CSR submission to ZATCA and certificate retrieval.
    """
    
    def __init__(self, environment: str = "SANDBOX"):
        """
        Initializes Compliance CSID service.
        
        Args:
            environment: ZATCA environment ("SANDBOX" or "PRODUCTION")
        """
        self.environment = environment.upper()
        if self.environment not in ("SANDBOX", "PRODUCTION"):
            raise ValueError(f"Invalid environment: {environment}. Must be SANDBOX or PRODUCTION")
        
        settings = get_settings()
        
        # Get environment-specific base URL
        if self.environment == "SANDBOX":
            self.base_url = settings.zatca_sandbox_base_url
        else:
            self.base_url = settings.zatca_production_base_url
        
        # Compliance CSID endpoint (relative to base URL)
        self.compliance_csid_endpoint = "/compliance/csid"
        
        # Timeout configuration
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        
        # OAuth service for authentication
        self.oauth_service = get_oauth_service(environment=self.environment)
    
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
            logger.error(f"Failed to get OAuth token for Compliance CSID: {e}")
            raise ValueError(
                f"ZATCA OAuth authentication failed for {self.environment}. "
                f"Please verify OAuth credentials are configured correctly. "
                f"Error: {str(e)}"
            ) from e
    
    def _prepare_csr_for_submission(self, csr_pem: str) -> str:
        """
        Prepares CSR for ZATCA API submission.
        
        According to ZATCA Developer Portal Manual:
        - CSR should be in PEM format
        - May need base64 encoding or direct PEM string
        - Remove extra whitespace/newlines
        
        Args:
            csr_pem: CSR in PEM format
            
        Returns:
            Prepared CSR string (cleaned, may be base64 encoded if required)
        """
        # Clean CSR: remove extra whitespace, ensure proper format
        csr_cleaned = csr_pem.strip()
        
        # ZATCA typically expects the CSR as-is in PEM format within JSON
        # Some implementations may require base64, but standard is direct PEM
        # We'll use direct PEM format as per ZATCA Developer Portal Manual
        
        return csr_cleaned
    
    async def submit_csr(
        self,
        csr_pem: str,
        retry_on_401: bool = True
    ) -> Dict[str, str]:
        """
        Submits CSR to ZATCA Compliance CSID API.
        
        **ZATCA API Specification:**
        - Endpoint: POST {base_url}/compliance/csid
        - Headers: Authorization Bearer token, Content-Type: application/json
        - Body: { "csr": "-----BEGIN CERTIFICATE REQUEST-----\\n..." }
        - Response: {
            "requestID": "...",
            "dispositionMessage": "...",
            "secret": "...",
            "binarySecurityToken": "-----BEGIN CERTIFICATE-----\\n..."
          }
        
        **Error Handling:**
        - 400: Invalid CSR format or request
        - 401: OAuth authentication failed (auto-retry once)
        - 409: CSR already submitted or duplicate request
        - 500: ZATCA server error
        
        Args:
            csr_pem: Certificate Signing Request in PEM format
            retry_on_401: If True, retry once on 401 after token refresh
            
        Returns:
            Dictionary containing:
            - requestID: ZATCA request identifier
            - dispositionMessage: Status message from ZATCA
            - secret: Certificate secret (for revocation/management)
            - binarySecurityToken: Certificate in PEM format
            
        Raises:
            ValueError: If CSR is invalid, OAuth fails, or request fails
            httpx.HTTPStatusError: For HTTP errors (400, 409, 500)
        """
        if not csr_pem or not csr_pem.strip():
            raise ValueError("CSR cannot be empty")
        
        # Validate CSR format (basic check)
        if "-----BEGIN CERTIFICATE REQUEST-----" not in csr_pem:
            raise ValueError("Invalid CSR format: must be PEM format starting with -----BEGIN CERTIFICATE REQUEST-----")
        
        # Prepare CSR for submission
        csr_prepared = self._prepare_csr_for_submission(csr_pem)
        
        # Build request URL
        request_url = f"{self.base_url}{self.compliance_csid_endpoint}"
        
        logger.info(
            f"Submitting CSR to ZATCA Compliance CSID API ({self.environment})",
            extra={
                "environment": self.environment,
                "endpoint": request_url,
                "csr_length": len(csr_prepared)
            }
        )
        
        # Prepare request payload
        payload = {
            "csr": csr_prepared
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
                            "environment": self.environment,
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
                        f"ZATCA Compliance CSID API returned 400 Bad Request: {error_message}",
                        extra={
                            "environment": self.environment,
                            "status_code": 400,
                            "error": error_message
                        }
                    )
                    raise ValueError(
                        f"Invalid CSR or request format. ZATCA error: {error_message}"
                    )
                
                if response.status_code == 409:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_message = error_data.get("message", error_data.get("error", "CSR already submitted or duplicate request"))
                    logger.warning(
                        f"ZATCA Compliance CSID API returned 409 Conflict: {error_message}",
                        extra={
                            "environment": self.environment,
                            "status_code": 409,
                            "error": error_message
                        }
                    )
                    raise ValueError(
                        f"CSR submission conflict. This CSR may have already been submitted. ZATCA error: {error_message}"
                    )
                
                if response.status_code == 500:
                    error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    error_message = error_data.get("message", error_data.get("error", "ZATCA server error"))
                    logger.error(
                        f"ZATCA Compliance CSID API returned 500 Internal Server Error: {error_message}",
                        extra={
                            "environment": self.environment,
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
                        f"Invalid ZATCA Compliance CSID response: missing fields {missing_fields}",
                        extra={
                            "environment": self.environment,
                            "response_keys": list(data.keys()),
                            "missing_fields": missing_fields
                        }
                    )
                    raise ValueError(
                        f"Invalid response from ZATCA Compliance CSID API: missing required fields {missing_fields}"
                    )
                
                # Extract certificate (binarySecurityToken)
                certificate_pem = data.get("binarySecurityToken", "")
                if not certificate_pem or "-----BEGIN CERTIFICATE-----" not in certificate_pem:
                    logger.error(
                        f"Invalid certificate format in ZATCA response",
                        extra={
                            "environment": self.environment,
                            "certificate_preview": certificate_pem[:100] if certificate_pem else "empty"
                        }
                    )
                    raise ValueError("Invalid certificate format received from ZATCA")
                
                logger.info(
                    f"Successfully received certificate from ZATCA Compliance CSID API",
                    extra={
                        "environment": self.environment,
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
                f"Timeout submitting CSR to ZATCA Compliance CSID API",
                extra={
                    "environment": self.environment,
                    "timeout": self.timeout
                }
            )
            raise ValueError(
                f"Request to ZATCA Compliance CSID API timed out. "
                f"Please check network connectivity and try again."
            ) from e
        
        except httpx.HTTPStatusError as e:
            # Already handled above, but catch any other status errors
            logger.error(
                f"HTTP error submitting CSR to ZATCA Compliance CSID API: {e.response.status_code}",
                extra={
                    "environment": self.environment,
                    "status_code": e.response.status_code,
                    "error": e.response.text[:200]
                }
            )
            raise ValueError(
                f"ZATCA Compliance CSID API returned error {e.response.status_code}: {e.response.text[:200]}"
            ) from e
        
        except ValueError:
            # Re-raise ValueError as-is (already formatted)
            raise
        
        except Exception as e:
            logger.error(
                f"Unexpected error submitting CSR to ZATCA Compliance CSID API: {e}",
                extra={
                    "environment": self.environment,
                    "error": str(e)
                },
                exc_info=True
            )
            raise ValueError(f"Failed to submit CSR to ZATCA Compliance CSID API: {str(e)}") from e

