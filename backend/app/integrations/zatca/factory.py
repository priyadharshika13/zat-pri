"""
ZATCA client factory for environment-based routing.

Provides factory function to get appropriate ZATCA client based on environment.
Single source of truth for client selection - no code duplication.
"""

import logging
from typing import Protocol, Optional

from app.core.config import get_settings
from app.integrations.zatca.sandbox import ZATCASandboxClient
from app.integrations.zatca.production import ZATCAProductionClient

logger = logging.getLogger(__name__)


class ZATCAClientProtocol(Protocol):
    """
    Common interface for all ZATCA clients.
    
    Both sandbox and production clients must implement these methods.
    This allows seamless switching between environments.
    """
    
    async def submit_for_clearance(
        self,
        signed_xml: str,
        invoice_uuid: str
    ) -> dict[str, str]:
        """
        Submits invoice to ZATCA for clearance.
        
        Args:
            signed_xml: Signed XML invoice content
            invoice_uuid: Invoice UUID
            
        Returns:
            Dictionary with clearance status, UUID, and QR code
        """
        ...
    
    async def report_invoice(
        self, 
        invoice_uuid: str,
        clearance_status: Optional[str] = None
    ) -> dict[str, str]:
        """
        Reports invoice to ZATCA reporting system.
        
        Args:
            invoice_uuid: Invoice UUID to report
            clearance_status: Optional clearance status (e.g., "CLEARED") for reporting headers
            
        Returns:
            Dictionary with reporting status
        """
        ...


def get_zatca_client(environment: str = None) -> ZATCAClientProtocol:
    """
    Factory function to get appropriate ZATCA client based on environment.
    
    CRITICAL: This is the single source of truth for client selection.
    If environment is provided (tenant-aware), uses that. Otherwise falls back to config.
    
    Args:
        environment: Optional environment (SANDBOX or PRODUCTION). 
                     If None, uses ZATCA_ENV from config.
    
    Returns:
        ZATCA client instance (Sandbox or Production)
        
    Raises:
        ValueError: If environment is invalid
    """
    if environment:
        zatca_env = environment.upper()
    else:
        settings = get_settings()
        zatca_env = settings.zatca_environment  # This validates and returns SANDBOX or PRODUCTION
    
    if zatca_env == "SANDBOX":
        logger.debug("Creating ZATCA Sandbox client")
        return ZATCASandboxClient()
    elif zatca_env == "PRODUCTION":
        logger.debug("Creating ZATCA Production client")
        return ZATCAProductionClient()
    else:
        # This should never happen due to config validation, but fail fast if it does
        raise ValueError(
            f"Invalid ZATCA environment: {zatca_env}. "
            f"Must be 'SANDBOX' or 'PRODUCTION'."
        )

