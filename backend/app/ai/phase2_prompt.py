"""
Phase-2 validation prompts.

Defines prompt templates for AI-based Phase-2 invoice validation.
Handles prompt construction and formatting.
Does not execute validation or make API calls.
"""


def get_phase2_validation_prompt(invoice_data: dict) -> str:
    """
    Generates validation prompt for Phase-2 invoice.
    
    Args:
        invoice_data: Invoice data dictionary
        
    Returns:
        Formatted validation prompt
    """
    return f"""
    Validate the following Phase-2 invoice data according to ZATCA requirements:
    
    Invoice UUID: {invoice_data.get('uuid')}
    Invoice Number: {invoice_data.get('invoice_number')}
    Seller Tax Number: {invoice_data.get('seller_tax_number')}
    Previous Invoice Hash: {invoice_data.get('previous_invoice_hash')}
    
    Check for:
    - Valid UUID format
    - Invoice hash chain integrity
    - XML structure compliance
    - Cryptographic signature validity
    - ZATCA Phase-2 compliance
    """

