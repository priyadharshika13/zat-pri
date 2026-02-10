"""
ZATCA API client for Phase-2 operations.

DEPRECATED: This class is maintained for backward compatibility.
New code should use get_zatca_client() factory function directly.

This wrapper uses the factory pattern internally but maintains the old interface
that accepts environment parameter for backward compatibility.
"""

import logging
from typing import Dict

from app.integrations.zatca.factory import get_zatca_client

logger = logging.getLogger(__name__)


class ZATCAClient:
    """
    Client for ZATCA API integration (backward compatibility wrapper).
    
    NOTE: This class is a compatibility layer. The environment parameter
    is ignored - actual environment is determined by ZATCA_ENV config.
    
    For new code, use get_zatca_client() factory function directly.
    """
    
    def __init__(self):
        """Initializes ZATCA client using factory pattern."""
        # Client is created lazily on first use to respect config changes
        self._client = None
    
    def _get_client(self):
        """Gets ZATCA client instance (lazy initialization)."""
        if self._client is None:
            self._client = get_zatca_client()
        return self._client
    
    async def submit_for_clearance(
        self,
        signed_xml: str,
        invoice_uuid: str,
        environment: str = None  # Ignored - uses ZATCA_ENV from config
    ) -> Dict[str, str]:
        """
        Submits signed XML invoice to ZATCA for clearance.
        
        Args:
            signed_xml: Signed XML invoice content
            invoice_uuid: Invoice UUID
            environment: DEPRECATED - ignored. Uses ZATCA_ENV from config instead.
            
        Returns:
            Dictionary containing clearance response data
        """
        if environment is not None:
            logger.warning(
                f"Environment parameter '{environment}' is ignored. "
                f"Using ZATCA_ENV from config instead."
            )
        
        client = self._get_client()
        return await client.submit_for_clearance(
            signed_xml=signed_xml,
            invoice_uuid=invoice_uuid
        )
    
    async def report_invoice(
        self,
        invoice_uuid: str,
        environment: str = None  # Ignored - uses ZATCA_ENV from config
    ) -> Dict[str, str]:
        """
        Reports invoice to ZATCA reporting system.
        
        Args:
            invoice_uuid: Invoice UUID to report
            environment: DEPRECATED - ignored. Uses ZATCA_ENV from config instead.
            
        Returns:
            Dictionary containing reporting response
        """
        if environment is not None:
            logger.warning(
                f"Environment parameter '{environment}' is ignored. "
                f"Using ZATCA_ENV from config instead."
            )
        
        client = self._get_client()
        return await client.report_invoice(invoice_uuid=invoice_uuid)

