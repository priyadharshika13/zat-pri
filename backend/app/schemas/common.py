"""
Common schema definitions.

Shared types used across multiple request/response schemas.
Re-exports constants for convenience.
Does not contain invoice-specific business logic or validation rules.
"""

from app.core.constants import InvoiceMode, Environment, TaxCategory

__all__ = ["InvoiceMode", "Environment", "TaxCategory"]
