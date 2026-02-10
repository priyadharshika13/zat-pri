"""
ZATCA integration package.

Provides environment-based client factory, common interfaces, and error intelligence.
"""

from app.integrations.zatca.factory import get_zatca_client, ZATCAClientProtocol
from app.integrations.zatca.error_catalog import (
    get_error_info,
    get_error_explanation,
    get_error_technical_reason,
    get_error_corrective_action,
    enrich_error_response,
    extract_error_code_from_message,
    get_all_error_codes,
    ZATCA_ERROR_CATALOG
)

__all__ = [
    "get_zatca_client",
    "ZATCAClientProtocol",
    "get_error_info",
    "get_error_explanation",
    "get_error_technical_reason",
    "get_error_corrective_action",
    "enrich_error_response",
    "extract_error_code_from_message",
    "get_all_error_codes",
    "ZATCA_ERROR_CATALOG"
]
