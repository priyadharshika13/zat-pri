"""
ZATCA Error Intelligence Catalog.

Provides mapping of ZATCA error codes to human-readable explanations,
technical reasons, and suggested corrective actions.

This is a pure Python dictionary-based catalog with no AI dependencies.
Designed for reuse in API responses and error handling.
"""

from typing import Dict, Optional


# ZATCA Error Code Catalog
# Structure: error_code -> {
#     "explanation": Human-readable explanation,
#     "technical_reason": Technical root cause,
#     "corrective_action": Suggested fix
# }

ZATCA_ERROR_CATALOG: Dict[str, Dict[str, str]] = {
    # XML Validation Errors (1000-1999)
    "ZATCA-1001": {
        "explanation": "XML structure does not conform to UBL 2.1 schema",
        "technical_reason": "Invoice XML fails schema validation against UBL 2.1 specification",
        "corrective_action": "Verify XML structure matches UBL 2.1 schema. Check namespace declarations, element hierarchy, and required elements."
    },
    "ZATCA-1002": {
        "explanation": "Missing required XML element",
        "technical_reason": "Mandatory UBL element is missing from invoice XML",
        "corrective_action": "Review ZATCA requirements and ensure all mandatory elements (Invoice, ID, IssueDate, AccountingSupplierParty, etc.) are present."
    },
    "ZATCA-1003": {
        "explanation": "Invalid XML namespace declaration",
        "technical_reason": "XML namespace URIs do not match UBL 2.1 specification",
        "corrective_action": "Verify namespace declarations: xmlns='urn:oasis:names:specification:ubl:schema:xsd:Invoice-2' and related UBL namespaces."
    },
    "ZATCA-1004": {
        "explanation": "XML encoding mismatch",
        "technical_reason": "XML encoding declaration does not match actual content encoding",
        "corrective_action": "Ensure XML declaration specifies UTF-8 and file is saved/transmitted as UTF-8: <?xml version='1.0' encoding='UTF-8'?>"
    },
    
    # Tax Calculation Errors (2000-2999)
    "ZATCA-2001": {
        "explanation": "Tax percent inconsistency detected",
        "technical_reason": "Tax percent values differ between InvoiceLine TaxCategory and document-level TaxTotal",
        "corrective_action": "Ensure ALL cbc:Percent values are identical (15.00 for standard VAT). Use the same tax rate from line items in document-level TaxTotal."
    },
    "ZATCA-2002": {
        "explanation": "Invalid VAT rate - must be 15.00%",
        "technical_reason": "Tax rate is not 15.00% for standard rate items",
        "corrective_action": "Set tax_rate to 15.00 for all standard rate (S) line items. ZATCA requires exactly 15.00% for standard VAT."
    },
    "ZATCA-2003": {
        "explanation": "Tax calculation mismatch",
        "technical_reason": "Calculated tax amount does not match provided tax amount",
        "corrective_action": "Recalculate: line_taxable × 0.15 = line_vat. Ensure TaxExclusiveAmount = SUM(line_taxable) and TaxTotal = SUM(line_vat)."
    },
    "ZATCA-2004": {
        "explanation": "Taxable amount calculation error",
        "technical_reason": "TaxableAmount does not equal (quantity × unit_price) - discount",
        "corrective_action": "Calculate taxable amount as: line_gross = qty × price, line_taxable = line_gross - discount. Use AllowanceCharge for discounts."
    },
    "ZATCA-2005": {
        "explanation": "Document totals do not match line item totals",
        "technical_reason": "TaxExclusiveAmount or TaxTotal does not equal sum of line item values",
        "corrective_action": "Compute totals from line items: TaxExclusiveAmount = SUM(line_taxable), TaxTotal = SUM(line_vat). Do not hardcode totals."
    },
    
    # Cryptographic Errors (3000-3999)
    "ZATCA-3001": {
        "explanation": "Digital signature validation failed",
        "technical_reason": "XMLDSig signature does not validate against invoice content",
        "corrective_action": "Verify private key and certificate are correct. Ensure XML is canonicalized (C14N) before signing. Check signature algorithm is RSA-SHA256."
    },
    "ZATCA-3002": {
        "explanation": "Missing or empty digital signature",
        "technical_reason": "Digital signature element is missing or contains empty value",
        "corrective_action": "Ensure digital_signature field is populated with Base64-encoded signature value. Phase-2 requires non-empty signature."
    },
    "ZATCA-3003": {
        "explanation": "Invalid signature algorithm",
        "technical_reason": "Digital signature uses unsupported algorithm (must be RSA-SHA256)",
        "corrective_action": "Use RSA-SHA256 algorithm: http://www.w3.org/2001/04/xmldsig-more#rsa-sha256 in SignatureMethod element."
    },
    "ZATCA-3004": {
        "explanation": "XML hash mismatch",
        "technical_reason": "Computed XML hash does not match provided hash value",
        "corrective_action": "Recalculate SHA-256 hash of canonicalized XML. Ensure hash is computed before signing and matches the hash in clearance request."
    },
    "ZATCA-3005": {
        "explanation": "Invalid certificate or certificate chain",
        "technical_reason": "X.509 certificate in signature is invalid, expired, or not trusted",
        "corrective_action": "Verify certificate is valid, not expired, and issued by trusted CA. Ensure certificate is properly embedded in KeyInfo/X509Data."
    },
    "ZATCA-3006": {
        "explanation": "XML canonicalization error",
        "technical_reason": "XML canonicalization (C14N) failed or produced invalid output",
        "corrective_action": "Ensure XML is properly formatted before canonicalization. Use C14N algorithm: http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
    },
    
    # UUID and Hash Chain Errors (4000-4999)
    "ZATCA-4001": {
        "explanation": "Invalid invoice UUID format",
        "technical_reason": "Invoice UUID does not conform to RFC 4122 format",
        "corrective_action": "Generate UUID in RFC 4122 format (e.g., 550e8400-e29b-41d4-a716-446655440000). Use standard UUID library."
    },
    "ZATCA-4002": {
        "explanation": "Duplicate invoice UUID",
        "technical_reason": "Invoice UUID has already been used in a previous submission",
        "corrective_action": "Generate a new unique UUID for each invoice. Ensure UUID uniqueness across all invoice submissions."
    },
    "ZATCA-4003": {
        "explanation": "Previous Invoice Hash (PIH) mismatch",
        "technical_reason": "Previous invoice hash does not match the hash of the most recently cleared invoice",
        "corrective_action": "Verify PIH matches the XML hash of the previous invoice in the chain. Ensure invoices are submitted in correct sequence."
    },
    "ZATCA-4004": {
        "explanation": "Missing Previous Invoice Hash",
        "technical_reason": "Previous Invoice Hash is required but not provided",
        "corrective_action": "For Phase-2 invoices (except first invoice), provide previous_invoice_hash from the most recently cleared invoice."
    },
    "ZATCA-4005": {
        "explanation": "Invalid hash chain - hash sequence broken",
        "technical_reason": "Invoice hash chain is broken - PIH does not link to previous invoice",
        "corrective_action": "Verify hash chain integrity. Each invoice's PIH must match the previous invoice's XML hash. Check invoice submission order."
    },
    
    # QR Code Errors (5000-5999)
    "ZATCA-5001": {
        "explanation": "Invalid QR code format",
        "technical_reason": "QR code data does not conform to ZATCA TLV encoding specification",
        "corrective_action": "Verify QR code uses correct TLV encoding format. Check tag values, length fields, and data encoding match ZATCA specification."
    },
    "ZATCA-5002": {
        "explanation": "QR code data mismatch",
        "technical_reason": "QR code contains data that does not match invoice values",
        "corrective_action": "Ensure QR code data (seller name, VAT number, invoice total, tax amount, XML hash, signature) matches invoice data exactly."
    },
    "ZATCA-5003": {
        "explanation": "Missing QR code in clearance response",
        "technical_reason": "ZATCA clearance response does not include QR code",
        "corrective_action": "Use QR code from ZATCA clearance response if provided. If clearance QR is available, do not use locally generated QR."
    },
    
    # Clearance Submission Errors (6000-6999)
    "ZATCA-6001": {
        "explanation": "Clearance request rejected - invoice data invalid",
        "technical_reason": "ZATCA rejected clearance due to invalid invoice data or structure",
        "corrective_action": "Review ZATCA rejection details. Verify XML structure, tax calculations, signatures, and all required fields. Check ZATCA error response for specific issues."
    },
    "ZATCA-6002": {
        "explanation": "Clearance request timeout",
        "technical_reason": "ZATCA API did not respond within timeout period",
        "corrective_action": "Retry clearance submission. If persistent, check network connectivity and ZATCA API status. Verify API endpoint and authentication."
    },
    "ZATCA-6003": {
        "explanation": "Authentication failure",
        "technical_reason": "ZATCA API authentication credentials are invalid or expired",
        "corrective_action": "Verify API credentials (certificate, private key, authentication tokens) are valid and not expired. Check certificate validity period."
    },
    "ZATCA-6004": {
        "explanation": "Clearance API unavailable",
        "technical_reason": "ZATCA clearance API is temporarily unavailable or returning server errors",
        "corrective_action": "Retry after a delay. Check ZATCA system status. If persistent, contact ZATCA support for API availability."
    },
    "ZATCA-6005": {
        "explanation": "Invalid clearance request format",
        "technical_reason": "Clearance request payload does not match ZATCA API specification",
        "corrective_action": "Verify request format: JSON with 'invoice' (signed XML) and 'uuid' fields. Check Content-Type header is application/json."
    },
    
    # AllowanceCharge/Discount Errors (7000-7999)
    "ZATCA-7001": {
        "explanation": "Missing AllowanceCharge element for discounted line",
        "technical_reason": "Invoice line has discount but missing required AllowanceCharge element",
        "corrective_action": "For lines with discount > 0, add <cac:AllowanceCharge> with ChargeIndicator=false and Amount=discount. Do not reduce unit price directly."
    },
    "ZATCA-7002": {
        "explanation": "Invalid AllowanceCharge ChargeIndicator",
        "technical_reason": "AllowanceCharge ChargeIndicator must be 'false' for discounts",
        "corrective_action": "Set ChargeIndicator to 'false' for discount AllowanceCharge elements. Use 'true' only for charges (not discounts)."
    },
    "ZATCA-7003": {
        "explanation": "Discount exceeds line subtotal",
        "technical_reason": "Discount amount is greater than line item subtotal (quantity × unit_price)",
        "corrective_action": "Ensure discount amount does not exceed line gross amount. Discount must be <= (quantity × unit_price)."
    },
    
    # Seller/Buyer Information Errors (8000-8999)
    "ZATCA-8001": {
        "explanation": "Invalid seller VAT registration number",
        "technical_reason": "Seller VAT number does not match required format (15 digits)",
        "corrective_action": "Verify seller_tax_number is exactly 15 digits. Remove any non-numeric characters. Ensure it matches ZATCA registered VAT number."
    },
    "ZATCA-8002": {
        "explanation": "Seller information missing or invalid",
        "technical_reason": "Required seller information (name, VAT number) is missing or invalid",
        "corrective_action": "Ensure seller_name and seller_tax_number are provided and valid. Seller information is mandatory for all invoices."
    },
    "ZATCA-8003": {
        "explanation": "Invalid buyer VAT registration number format",
        "technical_reason": "Buyer VAT number format is invalid (if provided, must be 15 digits)",
        "corrective_action": "If buyer_tax_number is provided, ensure it is exactly 15 digits. Buyer VAT number is optional but must be valid if provided."
    },
    
    # Invoice Metadata Errors (9000-9999)
    "ZATCA-9001": {
        "explanation": "Invalid invoice date",
        "technical_reason": "Invoice date is in the future or invalid format",
        "corrective_action": "Ensure invoice_date is not in the future. Use ISO 8601 format: YYYY-MM-DDTHH:MM:SS. Verify timezone handling."
    },
    "ZATCA-9002": {
        "explanation": "Missing or invalid invoice number",
        "technical_reason": "Invoice number is missing, empty, or exceeds maximum length",
        "corrective_action": "Provide valid invoice_number (1-50 characters, non-empty). Ensure it is unique and follows your internal numbering scheme."
    },
    "ZATCA-9003": {
        "explanation": "Invalid invoice type code",
        "technical_reason": "Invoice type code does not match ZATCA allowed values",
        "corrective_action": "Use valid invoice type code (e.g., '388' for standard invoice). Verify code matches ZATCA invoice type specification."
    },
    
    # System/Network Errors (10000-10999)
    "ZATCA-10001": {
        "explanation": "Network connection error",
        "technical_reason": "Failed to establish connection to ZATCA API",
        "corrective_action": "Check network connectivity, firewall rules, and DNS resolution. Verify ZATCA API endpoint is accessible."
    },
    "ZATCA-10002": {
        "explanation": "SSL/TLS certificate validation failed",
        "technical_reason": "ZATCA API SSL certificate validation failed",
        "corrective_action": "Verify ZATCA API SSL certificate is valid and trusted. Update CA certificates if needed. Check certificate chain."
    },
    "ZATCA-10003": {
        "explanation": "Request payload too large",
        "technical_reason": "Invoice XML exceeds maximum allowed size",
        "corrective_action": "Optimize XML size. Remove unnecessary whitespace. Ensure XML is properly formatted but not excessively verbose."
    },
    
    # Generic/Unknown Errors
    "ZATCA-UNKNOWN": {
        "explanation": "Unknown ZATCA error",
        "technical_reason": "ZATCA returned an error that is not in the catalog",
        "corrective_action": "Review ZATCA error response for details. Check ZATCA documentation for error code meaning. Contact ZATCA support if error persists."
    }
}


def get_error_info(error_code: str) -> Optional[Dict[str, str]]:
    """
    Retrieves error information for a given ZATCA error code.
    
    Args:
        error_code: ZATCA error code (e.g., "ZATCA-2001")
        
    Returns:
        Dictionary with explanation, technical_reason, and corrective_action,
        or None if error code not found
    """
    return ZATCA_ERROR_CATALOG.get(error_code.upper())


def get_error_explanation(error_code: str) -> Optional[str]:
    """
    Gets human-readable explanation for error code.
    
    Args:
        error_code: ZATCA error code
        
    Returns:
        Human-readable explanation or None if not found
    """
    error_info = get_error_info(error_code)
    return error_info.get("explanation") if error_info else None


def get_error_technical_reason(error_code: str) -> Optional[str]:
    """
    Gets technical reason for error code.
    
    Args:
        error_code: ZATCA error code
        
    Returns:
        Technical reason or None if not found
    """
    error_info = get_error_info(error_code)
    return error_info.get("technical_reason") if error_info else None


def get_error_corrective_action(error_code: str) -> Optional[str]:
    """
    Gets suggested corrective action for error code.
    
    Args:
        error_code: ZATCA error code
        
    Returns:
        Corrective action or None if not found
    """
    error_info = get_error_info(error_code)
    return error_info.get("corrective_action") if error_info else None


def enrich_error_response(
    error_code: str,
    original_error: Optional[str] = None
) -> Dict[str, str]:
    """
    Enriches error response with catalog information.
    
    Args:
        error_code: ZATCA error code
        original_error: Original error message (optional)
        
    Returns:
        Dictionary with enriched error information:
        {
            "error_code": error_code,
            "explanation": human-readable explanation,
            "technical_reason": technical root cause,
            "corrective_action": suggested fix,
            "original_error": original error message (if provided)
        }
    """
    error_info = get_error_info(error_code) or get_error_info("ZATCA-UNKNOWN")
    
    response = {
        "error_code": error_code.upper(),
        "explanation": error_info.get("explanation", "Unknown error"),
        "technical_reason": error_info.get("technical_reason", "Error details not available"),
        "corrective_action": error_info.get("corrective_action", "Review error and consult ZATCA documentation")
    }
    
    if original_error:
        response["original_error"] = original_error
    
    return response


def extract_error_code_from_message(error_message: str) -> Optional[str]:
    """
    Attempts to extract ZATCA error code from error message.
    
    Looks for patterns like "ZATCA-XXXX" in the error message.
    
    Args:
        error_message: Error message that may contain error code
        
    Returns:
        Extracted error code or None if not found
    """
    import re
    
    # Pattern: ZATCA- followed by digits
    pattern = r'ZATCA-(\d{4,5})'
    match = re.search(pattern, error_message.upper())
    
    if match:
        return f"ZATCA-{match.group(1)}"
    
    return None


def get_all_error_codes() -> list[str]:
    """
    Returns list of all error codes in the catalog.
    
    Returns:
        List of error code strings
    """
    return list(ZATCA_ERROR_CATALOG.keys())

