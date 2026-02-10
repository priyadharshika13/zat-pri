"""
Time utility functions.

Provides time formatting and conversion utilities for invoice processing.
Handles ZATCA timestamp formats and timezone conversions.
Does not handle business logic or invoice date validation.
"""

from datetime import datetime, timezone


def format_zatca_timestamp(dt: datetime) -> str:
    """
    Formats datetime according to ZATCA timestamp format.
    
    Args:
        dt: Datetime object to format
        
    Returns:
        Formatted timestamp string (ISO 8601 with Z suffix)
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_invoice_date_to_utc(dt: datetime) -> datetime:
    """
    Normalizes invoice date/time to UTC for ZATCA IssueDate/IssueTime.
    
    ZATCA requires IssueDate and IssueTime in UTC. If the client sends
    timezone-aware datetime, convert to UTC. If naive, assume UTC (caller
    must ensure clients send UTC or document that naive = UTC).
    
    Args:
        dt: Invoice date/time (naive or aware).
        
    Returns:
        Timezone-aware datetime in UTC.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=timezone.utc)

