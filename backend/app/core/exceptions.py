"""
Application-specific exceptions for clear error handling and HTTP mapping.

Used to distinguish signing/clearance failures (503) from validation (422)
and permission (403) errors.
"""


class SigningNotConfiguredError(Exception):
    """
    Raised when Phase-2 signing cannot be performed: missing or invalid
    key/certificate, or signing failure. API layer should map to HTTP 503.

    ZATCA audit requirement: no placeholder or unsigned XML may reach clearance.
    """
    pass
