"""
Phase-1 validation prompts.

Defines prompt templates for AI-based Phase-1 invoice validation.
Handles prompt construction and formatting.
Does not execute validation or make API calls.
"""


def get_phase1_validation_prompt(invoice_data: dict) -> str:
    """
    Generates validation prompt for Phase-1 invoice.
    
    Args:
        invoice_data: Invoice data dictionary
        
    Returns:
        Formatted validation prompt
    """
    return f"""
    Validate the following Phase-1 invoice data according to ZATCA requirements:
    
    Invoice Number: {invoice_data.get('invoice_number')}
    Seller Tax Number: {invoice_data.get('seller_tax_number')}
    Total Amount: {invoice_data.get('total_amount')}
    Tax Amount: {invoice_data.get('total_tax_amount')}
    
    Check for:
    - Valid tax number format (15 digits)
    - Correct total calculations
    - Required fields presence
    - ZATCA Phase-1 compliance
    """

