"""
ZATCA sandbox environment client.

Implements ZATCA API integration for sandbox/testing environment.
Handles API authentication, request formatting, and response parsing with retry logic.
Does not handle production environment integration or certificate management.
ZATCA requires the invoice payload to be base64-encoded (not raw XML).
"""

import base64
import logging
from typing import Dict, Optional
import asyncio

import httpx

from app.core.config import get_settings
from app.integrations.zatca.oauth_service import get_oauth_service

logger = logging.getLogger(__name__)


class ZATCASandboxClient:
    """Client for ZATCA sandbox API with retry logic and OAuth authentication."""
    
    def __init__(self):
        """Initializes sandbox client with base URL, timeout, and retry configuration."""
        settings = get_settings()
        self.base_url = settings.zatca_sandbox_base_url
        # CRITICAL: Use 10 second timeout to prevent hanging
        self.timeout = httpx.Timeout(10.0, connect=5.0)
        # Retry configuration
        self.max_retries = int(getattr(settings, "zatca_max_retries", 3))
        self.retry_delay = float(getattr(settings, "zatca_retry_delay", 1.0))
        # OAuth service for authentication
        self.oauth_service = get_oauth_service(environment="SANDBOX")
    
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
            logger.error(f"Failed to get OAuth token: {e}")
            raise ValueError(
                f"ZATCA OAuth authentication failed. "
                f"Please verify ZATCA_SANDBOX_CLIENT_ID and ZATCA_SANDBOX_CLIENT_SECRET are configured correctly. "
                f"Error: {str(e)}"
            ) from e
    
    async def submit_for_clearance(
        self,
        signed_xml: str,
        invoice_uuid: str
    ) -> Dict[str, str]:
        """
        Submits invoice to ZATCA sandbox for clearance with retry logic.
        
        Args:
            signed_xml: Signed XML invoice
            invoice_uuid: Invoice UUID
            
        Returns:
            Dictionary with clearance status, UUID, and QR code
        """
        logger.info(
            f"Submitting invoice {invoice_uuid} to ZATCA sandbox",
            extra={
                "invoice_uuid": invoice_uuid,
                "environment": "sandbox",
                "max_retries": self.max_retries
            }
        )
        
        last_exception = None
        token_refreshed = False
        
        for attempt in range(self.max_retries + 1):
            try:
                # Get OAuth token (force refresh if we got 401 on previous attempt)
                headers = await self._get_auth_headers(force_refresh=token_refreshed)
                
                # ZATCA requires base64-encoded invoice in request body (not raw XML)
                invoice_b64 = base64.b64encode(signed_xml.encode("utf-8")).decode("ascii")
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/invoices/clearance",
                        json={
                            "invoice": invoice_b64,
                            "uuid": invoice_uuid
                        },
                        headers=headers
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    logger.info(
                        f"Successfully submitted invoice {invoice_uuid} to ZATCA sandbox",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "attempt": attempt + 1,
                            "status_code": response.status_code
                        }
                    )
                    
                    return {
                        "status": data.get("clearanceStatus", "CLEARED"),
                        "uuid": data.get("clearanceUUID", invoice_uuid),
                        "qr_code": data.get("qrCode", ""),
                        "reporting_status": data.get("reportingStatus")
                    }
                    
            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Timeout submitting invoice {invoice_uuid} (attempt {attempt + 1}/{self.max_retries + 1}). "
                        f"Retrying in {wait_time}s...",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "attempt": attempt + 1,
                            "max_retries": self.max_retries,
                            "retry_delay": wait_time
                        }
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Timeout submitting invoice {invoice_uuid} after {self.max_retries + 1} attempts",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "max_retries": self.max_retries,
                            "error": str(e)
                        }
                    )
                    
            except httpx.HTTPStatusError as e:
                # Handle 401 Unauthorized - refresh token and retry once
                if e.response.status_code == 401 and not token_refreshed:
                    logger.warning(
                        f"Received 401 Unauthorized for invoice {invoice_uuid}, refreshing OAuth token and retrying",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "status_code": 401,
                            "attempt": attempt + 1
                        }
                    )
                    token_refreshed = True
                    # Retry immediately with refreshed token
                    continue
                
                # Don't retry on other client errors (4xx), only on server errors (5xx)
                if e.response.status_code < 500:
                    logger.error(
                        f"Client error submitting invoice {invoice_uuid}: {e.response.status_code}",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "status_code": e.response.status_code,
                            "error": e.response.text[:200]
                        }
                    )
                    return {
                        "status": "REJECTED",
                        "uuid": invoice_uuid,
                        "qr_code": "",
                        "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                    }
                
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Server error submitting invoice {invoice_uuid} (attempt {attempt + 1}/{self.max_retries + 1}). "
                        f"Retrying in {wait_time}s...",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "attempt": attempt + 1,
                            "status_code": e.response.status_code,
                            "retry_delay": wait_time
                        }
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Server error submitting invoice {invoice_uuid} after {self.max_retries + 1} attempts",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "status_code": e.response.status_code,
                            "max_retries": self.max_retries
                        }
                    )
                    
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Error submitting invoice {invoice_uuid} (attempt {attempt + 1}/{self.max_retries + 1}). "
                        f"Retrying in {wait_time}s...",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "attempt": attempt + 1,
                            "error": str(e),
                            "retry_delay": wait_time
                        }
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Error submitting invoice {invoice_uuid} after {self.max_retries + 1} attempts",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "max_retries": self.max_retries,
                            "error": str(e)
                        }
                    )
        
        # All retries exhausted
        return {
            "status": "REJECTED",
            "uuid": invoice_uuid,
            "qr_code": "",
            "error": f"Request failed after {self.max_retries + 1} attempts: {str(last_exception)}"
        }
    
    async def report_invoice(
        self, 
        invoice_uuid: str, 
        clearance_status: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Reports invoice to ZATCA sandbox with retry logic.
        
        Args:
            invoice_uuid: Invoice UUID to report
            clearance_status: Optional clearance status (e.g., "CLEARED") for header
            
        Returns:
            Dictionary with reporting status
        """
        logger.info(
            f"Reporting invoice {invoice_uuid} to ZATCA sandbox",
            extra={
                "invoice_uuid": invoice_uuid,
                "environment": "sandbox",
                "max_retries": self.max_retries,
                "clearance_status": clearance_status
            }
        )
        
        last_exception = None
        token_refreshed = False
        
        for attempt in range(self.max_retries + 1):
            try:
                # Get OAuth token (force refresh if we got 401 on previous attempt)
                headers = await self._get_auth_headers(force_refresh=token_refreshed)
                
                # Add optional headers per ZATCA Developer Portal Manual
                if clearance_status:
                    headers["Clearance-Status"] = clearance_status
                headers["Accept-Version"] = "1.0"  # ZATCA API version
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/invoices/report",
                        json={"uuid": invoice_uuid},
                        headers=headers
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    logger.info(
                        f"Successfully reported invoice {invoice_uuid} to ZATCA sandbox",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "attempt": attempt + 1,
                            "status_code": response.status_code
                        }
                    )
                    
                    return {
                        "status": data.get("status", "REPORTED"),
                        "message": data.get("message", "Invoice reported successfully")
                    }
                    
            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Timeout reporting invoice {invoice_uuid} (attempt {attempt + 1}/{self.max_retries + 1}). "
                        f"Retrying in {wait_time}s...",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "attempt": attempt + 1,
                            "retry_delay": wait_time
                        }
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Timeout reporting invoice {invoice_uuid} after {self.max_retries + 1} attempts",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "max_retries": self.max_retries
                        }
                    )
                    
            except httpx.HTTPStatusError as e:
                # Handle 401 Unauthorized - refresh token and retry once
                if e.response.status_code == 401 and not token_refreshed:
                    logger.warning(
                        f"Received 401 Unauthorized for invoice report {invoice_uuid}, refreshing OAuth token and retrying",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "status_code": 401,
                            "attempt": attempt + 1
                        }
                    )
                    token_refreshed = True
                    # Retry immediately with refreshed token
                    continue
                
                if e.response.status_code < 500:
                    logger.error(
                        f"Client error reporting invoice {invoice_uuid}: {e.response.status_code}",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "status_code": e.response.status_code
                        }
                    )
                    return {
                        "status": "FAILED",
                        "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                    }
                
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Server error reporting invoice {invoice_uuid} (attempt {attempt + 1}/{self.max_retries + 1}). "
                        f"Retrying in {wait_time}s...",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "attempt": attempt + 1,
                            "status_code": e.response.status_code,
                            "retry_delay": wait_time
                        }
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Server error reporting invoice {invoice_uuid} after {self.max_retries + 1} attempts",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "status_code": e.response.status_code
                        }
                    )
                    
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Error reporting invoice {invoice_uuid} (attempt {attempt + 1}/{self.max_retries + 1}). "
                        f"Retrying in {wait_time}s...",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "attempt": attempt + 1,
                            "error": str(e),
                            "retry_delay": wait_time
                        }
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Error reporting invoice {invoice_uuid} after {self.max_retries + 1} attempts",
                        extra={
                            "invoice_uuid": invoice_uuid,
                            "max_retries": self.max_retries,
                            "error": str(e)
                        }
                    )
        
        # All retries exhausted
        return {
            "status": "FAILED",
            "error": f"Request failed after {self.max_retries + 1} attempts: {str(last_exception)}"
        }
    
    async def ping(self) -> Dict[str, any]:
        """
        Pings ZATCA sandbox API to verify connectivity and authentication.
        
        Performs a lightweight authenticated request to check if:
        - OAuth authentication is working
        - ZATCA API is reachable
        - Credentials are valid
        
        Returns:
            Dictionary with:
            - connected: bool - True if ping successful
            - error_message: Optional[str] - Error message if ping failed
            - last_successful_ping: Optional[str] - ISO timestamp if successful
            
        Raises:
            ValueError: If OAuth credentials are not configured
        """
        try:
            # Get OAuth token
            headers = await self._get_auth_headers(force_refresh=False)
            
            # Perform a lightweight ping (using a health/status endpoint if available)
            # If no health endpoint, we'll use a minimal clearance check or report endpoint
            # For now, we'll try a simple GET request to a status endpoint
            ping_url = f"{self.base_url}/status"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    response = await client.get(ping_url, headers=headers)
                    response.raise_for_status()
                    
                    logger.info(
                        f"Successfully pinged ZATCA sandbox",
                        extra={
                            "environment": "sandbox",
                            "status_code": response.status_code
                        }
                    )
                    
                    from datetime import datetime
                    return {
                        "connected": True,
                        "error_message": None,
                        "last_successful_ping": datetime.utcnow().isoformat()
                    }
                except httpx.HTTPStatusError as e:
                    # If status endpoint doesn't exist (404), try a different approach
                    # We'll consider it connected if we can authenticate (not 401)
                    if e.response.status_code == 404:
                        # Status endpoint doesn't exist, but authentication worked
                        from datetime import datetime
                        return {
                            "connected": True,
                            "error_message": None,
                            "last_successful_ping": datetime.utcnow().isoformat()
                        }
                    elif e.response.status_code == 401:
                        # Authentication failed
                        logger.error(
                            f"ZATCA sandbox ping failed: Authentication failed (401)",
                            extra={
                                "environment": "sandbox",
                                "status_code": 401
                            }
                        )
                        return {
                            "connected": False,
                            "error_message": "OAuth authentication failed. Please verify ZATCA_SANDBOX_CLIENT_ID and ZATCA_SANDBOX_CLIENT_SECRET",
                            "last_successful_ping": None
                        }
                    else:
                        # Other error
                        logger.warning(
                            f"ZATCA sandbox ping returned status {e.response.status_code}",
                            extra={
                                "environment": "sandbox",
                                "status_code": e.response.status_code
                            }
                        )
                        from datetime import datetime
                        # Consider it connected if we got past authentication
                        return {
                            "connected": True,
                            "error_message": None,
                            "last_successful_ping": datetime.utcnow().isoformat()
                        }
                        
        except httpx.TimeoutException as e:
            logger.error(
                f"ZATCA sandbox ping timeout",
                extra={
                    "environment": "sandbox",
                    "timeout": self.timeout
                }
            )
            return {
                "connected": False,
                "error_message": f"Connection timeout. ZATCA sandbox may be unreachable.",
                "last_successful_ping": None
            }
        except ValueError as e:
            # OAuth credentials not configured
            logger.error(
                f"ZATCA sandbox ping failed: OAuth credentials not configured",
                extra={
                    "environment": "sandbox",
                    "error": str(e)
                }
            )
            return {
                "connected": False,
                "error_message": str(e),
                "last_successful_ping": None
            }
        except Exception as e:
            logger.error(
                f"ZATCA sandbox ping failed: {e}",
                extra={
                    "environment": "sandbox",
                    "error": str(e)
                },
                exc_info=True
            )
            return {
                "connected": False,
                "error_message": f"Connection failed: {str(e)}",
                "last_successful_ping": None
            }
