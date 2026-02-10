"""
Clearance service for Phase-2 invoices.

Orchestrates the clearance workflow including submission and reporting.
Coordinates between XML generation, signing, and ZATCA API communication.
Does not handle XML generation or cryptographic signing directly.
"""

import logging
from typing import Dict, Optional

from app.integrations.zatca.factory import get_zatca_client, ZATCAClientProtocol

logger = logging.getLogger(__name__)


class ClearanceService:
    """Handles ZATCA clearance workflow for Phase-2 invoices."""
    
    def __init__(self, zatca_client: Optional[ZATCAClientProtocol] = None, environment: str = None):
        """
        Initializes clearance service.
        
        Args:
            zatca_client: ZATCA API client instance (uses factory if None)
            environment: Optional environment for tenant-aware client creation
        """
        # Use factory to get client - no direct imports of sandbox/production
        # If environment provided, use tenant-aware client
        if zatca_client:
            self.zatca_client = zatca_client
        elif environment:
            self.zatca_client = get_zatca_client(environment=environment)
        else:
            self.zatca_client = get_zatca_client()
    
    async def submit_clearance(
        self,
        signed_xml: str,
        invoice_uuid: str,
        environment: str = None  # DEPRECATED - ignored, uses ZATCA_ENV from config
    ) -> Dict[str, str]:
        """
        Submits invoice for ZATCA clearance.
        
        Args:
            signed_xml: Signed XML invoice
            invoice_uuid: Invoice UUID
            environment: DEPRECATED - ignored. Uses ZATCA_ENV from config instead.
            
        Returns:
            Dictionary containing clearance response
        """
        if environment is not None:
            logger.warning(
                f"Environment parameter '{environment}' is ignored. "
                f"Using ZATCA_ENV from config instead."
            )
        
        logger.info(f"Submitting invoice {invoice_uuid} for clearance")
        return await self.zatca_client.submit_for_clearance(
            signed_xml=signed_xml,
            invoice_uuid=invoice_uuid
        )
    
    async def report(
        self,
        invoice_uuid: str,
        clearance_status: Optional[str] = None,
        environment: str = None  # DEPRECATED - ignored, uses ZATCA_ENV from config
    ) -> Dict[str, str]:
        """
        Reports invoice to ZATCA reporting system.
        
        Args:
            invoice_uuid: Invoice UUID to report
            clearance_status: Optional clearance status (e.g., "CLEARED") for reporting headers
            environment: DEPRECATED - ignored. Uses ZATCA_ENV from config instead.
            
        Returns:
            Dictionary containing reporting response
        """
        if environment is not None:
            logger.warning(
                f"Environment parameter '{environment}' is ignored. "
                f"Using ZATCA_ENV from config instead."
            )
        
        logger.info(f"Reporting invoice {invoice_uuid} (clearance_status: {clearance_status})")
        return await self.zatca_client.report_invoice(
            invoice_uuid=invoice_uuid,
            clearance_status=clearance_status
        )

