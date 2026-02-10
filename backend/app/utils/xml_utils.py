"""
XML utility functions.

Provides helper functions for XML processing and manipulation.
Handles XML escaping, formatting, and basic transformations.
Does not handle XML generation, signing, or validation.
"""


def escape_xml(text: str) -> str:
    """
    Escapes XML special characters.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped XML string
    """
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))

