"""
ZATCA production environment client.

Implements ZATCA API integration for production environment.
Handles API authentication, request formatting, and response parsing with retry logic.
Does not handle sandbox environment integration.
ZATCA requires the invoice payload to be base64-encoded (not raw XML).
"""

import base64
import logging
from typing import Dict, Optional
import asyncio

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ZATCAProductionClient:
    """Client for ZATCA production API with retry logic."""
    
    def __init__(self):
        """Initializes production client with base URL, timeout, and retry configuration."""
        settings = get_settings()
        self.base_url = settings.zatca_production_base_url
        # CRITICAL: Use explicit timeout to prevent hanging
        self.timeout = httpx.Timeout(settings.zatca_timeout, connect=5.0)
        # Retry configuration
        self.max_retries = int(getattr(settings, "zatca_max_retries", 3))
        self.retry_delay = float(getattr(settings, "zatca_retry_delay", 1.0))
    
    async def submit_for_clearance(
        self,
        signed_xml: str,
        invoice_uuid: str
    ) -> Dict[str, str]:
        """
        Submits invoice to ZATCA production for clearance with retry logic.
        
        Args:
            signed_xml: Signed XML invoice
            invoice_uuid: Invoice UUID
            
        Returns:
            Dictionary with clearance status, UUID, and QR code
        """
        logger.info(
            f"Submitting invoice {invoice_uuid} to ZATCA production",
            extra={
                "invoice_uuid": invoice_uuid,
                "environment": "production",
                "max_retries": self.max_retries
            }
        )
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # ZATCA requires base64-encoded invoice in request body (not raw XML)
                invoice_b64 = base64.b64encode(signed_xml.encode("utf-8")).decode("ascii")
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/invoices/clearance",
                        json={
                            "invoice": invoice_b64,
                            "uuid": invoice_uuid
                        },
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        }
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    logger.info(
                        f"Successfully submitted invoice {invoice_uuid} to ZATCA production",
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
                # Don't retry on client errors (4xx), only on server errors (5xx)
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
        Reports invoice to ZATCA production reporting system with retry logic.
        
        Args:
            invoice_uuid: Invoice UUID to report
            clearance_status: Optional clearance status (e.g., "CLEARED") for header
            
        Returns:
            Dictionary with reporting status
        """
        logger.info(
            f"Reporting invoice {invoice_uuid} to ZATCA production",
            extra={
                "invoice_uuid": invoice_uuid,
                "environment": "production",
                "max_retries": self.max_retries,
                "clearance_status": clearance_status
            }
        )
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
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
                        f"Successfully reported invoice {invoice_uuid} to ZATCA production",
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
