"""
Hash utility functions.

Provides cryptographic hashing functions for invoice processing.
Handles SHA-256 hashing for XML content and invoice chains.
Does not handle digital signatures or certificate operations.
"""

import hashlib


def compute_sha256(content: str) -> str:
    """
    Computes SHA-256 hash of content.
    
    Args:
        content: String content to hash
        
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

