"""
Application-wide constants and enumerations.

Centralizes constant values used across the application.
Does not contain configuration or environment-specific values.
"""

from enum import Enum


class InvoiceMode(str, Enum):
    """Invoice processing mode."""
    PHASE_1 = "PHASE_1"
    PHASE_2 = "PHASE_2"


class Environment(str, Enum):
    """Target environment for processing."""
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"


class TaxCategory(str, Enum):
    """ZATCA tax categories."""
    STANDARD = "S"
    ZERO_RATED = "Z"
    EXEMPT = "E"


class ClearanceStatus(str, Enum):
    """ZATCA clearance status values."""
    CLEARED = "CLEARED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"


class ReportingStatus(str, Enum):
    """ZATCA reporting status values."""
    REPORTED = "REPORTED"
    FAILED = "FAILED"
    PENDING = "PENDING"

