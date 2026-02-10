"""
Data masking utilities for sensitive invoice fields.

Provides safe masking of sensitive data before storage or logging.
"""

import json
from typing import Any, Dict, Optional


def mask_sensitive_fields(data: Dict[str, Any], fields_to_mask: Optional[list[str]] = None) -> Dict[str, Any]:
    """
    Masks sensitive fields in a dictionary.
    
    Default fields to mask:
    - seller_tax_number
    - buyer_tax_number
    - Any field containing 'password', 'secret', 'key', 'token'
    
    Args:
        data: Dictionary to mask
        fields_to_mask: Optional list of field names to mask (defaults to common sensitive fields)
        
    Returns:
        Dictionary with masked sensitive fields
    """
    if fields_to_mask is None:
        fields_to_mask = ['seller_tax_number', 'buyer_tax_number']
    
    # Also mask fields with sensitive keywords
    sensitive_keywords = ['password', 'secret', 'key', 'token', 'api_key', 'private_key']
    
    masked_data = data.copy()
    
    # Mask specified fields
    for field in fields_to_mask:
        if field in masked_data and masked_data[field]:
            masked_data[field] = mask_string(masked_data[field])
    
    # Mask fields with sensitive keywords
    for key, value in masked_data.items():
        if isinstance(key, str) and any(keyword in key.lower() for keyword in sensitive_keywords):
            if isinstance(value, str):
                masked_data[key] = mask_string(value)
            elif isinstance(value, dict):
                masked_data[key] = mask_sensitive_fields(value)
    
    # Recursively mask nested dictionaries
    for key, value in masked_data.items():
        if isinstance(value, dict):
            masked_data[key] = mask_sensitive_fields(value, fields_to_mask)
        elif isinstance(value, list):
            masked_data[key] = [
                mask_sensitive_fields(item, fields_to_mask) if isinstance(item, dict) else item
                for item in value
            ]
    
    return masked_data


def mask_string(value: str, visible_chars: int = 4) -> str:
    """
    Masks a string, showing only the last N characters.
    
    Args:
        value: String to mask
        visible_chars: Number of characters to show at the end (default: 4)
        
    Returns:
        Masked string (e.g., "****1234")
    """
    if not value or len(value) <= visible_chars:
        return "****"
    
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


def safe_json_dump(data: Any, max_size: int = 10 * 1024 * 1024) -> Optional[str]:
    """
    Safely converts data to JSON string with size limit.
    
    Args:
        data: Data to convert to JSON
        max_size: Maximum size in bytes (default: 10MB)
        
    Returns:
        JSON string or None if too large
    """
    try:
        json_str = json.dumps(data, default=str)
        if len(json_str.encode('utf-8')) > max_size:
            return None
        return json_str
    except (TypeError, ValueError) as e:
        return None


def safe_xml_storage(xml_content: str, max_size: int = 10 * 1024 * 1024) -> Optional[str]:
    """
    Safely validates XML content size before storage.
    
    Args:
        xml_content: XML content to validate
        max_size: Maximum size in bytes (default: 10MB)
        
    Returns:
        XML content or None if too large
    """
    if not xml_content:
        return None
    
    if len(xml_content.encode('utf-8')) > max_size:
        return None
    
    return xml_content

