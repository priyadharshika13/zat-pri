"""
Phase-2 invoice validator.

Validates invoices for ZATCA Phase-2 integration readiness before processing.
Checks XML readiness, mandatory ZATCA fields, high-risk patterns, and data consistency.
Does not handle Phase-1 validation, HTTP objects, or external API calls.
"""

import logging
import re
from typing import List
from datetime import datetime

from app.schemas.invoice import InvoiceRequest
from app.schemas.validation import ValidationResponse, ValidationIssue

logger = logging.getLogger(__name__)


class Phase2Validator:
    """Validates invoices for ZATCA Phase-2 compliance."""
    
    REQUIRED_VAT_RATE = 15.0
    REQUIRED_TAX_NUMBER_LENGTH = 15
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    HASH_PATTERN = re.compile(r'^[a-f0-9]{64}$', re.IGNORECASE)
    
    async def validate(self, request: InvoiceRequest) -> ValidationResponse:
        """
        Validates invoice for ZATCA Phase-2 integration readiness.
        
        Args:
            request: Invoice request to validate
            
        Returns:
            Validation response with status, issues, and suggestions
        """
        logger.debug(f"Validating Phase-2 invoice: {request.invoice_number}")
        
        issues: List[ValidationIssue] = []
        
        issues.extend(self._validate_mandatory_zatca_fields(request))
        issues.extend(self._validate_xml_readiness(request))
        issues.extend(self._validate_high_risk_patterns(request))
        issues.extend(self._validate_data_consistency(request))
        issues.extend(self._validate_vat_breakdown(request))
        
        status = "PASS" if not any(issue.severity == "error" for issue in issues) else "FAIL"
        suggestions = [issue.suggestion for issue in issues if issue.suggestion]
        
        return ValidationResponse(
            status=status,
            issues=issues,
            suggestions=suggestions
        )
    
    def _validate_mandatory_zatca_fields(self, request: InvoiceRequest) -> List[ValidationIssue]:
        """Validates presence of mandatory ZATCA Phase-2 fields."""
        issues: List[ValidationIssue] = []
        
        if not request.uuid:
            issues.append(ValidationIssue(
                field="uuid",
                severity="error",
                message="UUID is mandatory for Phase-2 invoices",
                suggestion="Generate a unique UUID (RFC 4122 format) for this invoice"
            ))
        elif not self.UUID_PATTERN.match(request.uuid):
            issues.append(ValidationIssue(
                field="uuid",
                severity="error",
                message="UUID must be in RFC 4122 format (e.g., 550e8400-e29b-41d4-a716-446655440000)",
                suggestion="Use a valid UUID format: 8-4-4-4-12 hexadecimal digits separated by hyphens"
            ))
        
        # PIH optional for first invoice; when provided must be 64 hex
        if request.previous_invoice_hash and not self.HASH_PATTERN.match(request.previous_invoice_hash):
            issues.append(ValidationIssue(
                field="previous_invoice_hash",
                severity="error",
                message="Previous Invoice Hash must be a 64-character hexadecimal string",
                suggestion="Ensure PIH is a valid SHA-256 hash (64 hex characters, lowercase recommended)"
            ))
        
        if not request.seller_tax_number or len(request.seller_tax_number) != self.REQUIRED_TAX_NUMBER_LENGTH:
            issues.append(ValidationIssue(
                field="seller_tax_number",
                severity="error",
                message=f"Seller VAT number must be exactly {self.REQUIRED_TAX_NUMBER_LENGTH} digits for Phase-2",
                suggestion=f"Provide a valid {self.REQUIRED_TAX_NUMBER_LENGTH}-digit Saudi VAT registration number"
            ))
        
        if not request.invoice_date:
            issues.append(ValidationIssue(
                field="invoice_date",
                severity="error",
                message="Invoice date is mandatory for Phase-2",
                suggestion="Provide a valid invoice date and time"
            ))
        elif request.invoice_date > datetime.now():
            issues.append(ValidationIssue(
                field="invoice_date",
                severity="error",
                message="Invoice date cannot be in the future",
                suggestion="Set invoice date to current or past date/time"
            ))
        
        if not request.line_items or len(request.line_items) == 0:
            issues.append(ValidationIssue(
                field="line_items",
                severity="error",
                message="At least one line item is mandatory for Phase-2",
                suggestion="Add at least one invoice line item with complete details"
            ))
        
        return issues
    
    def _validate_xml_readiness(self, request: InvoiceRequest) -> List[ValidationIssue]:
        """Validates XML structural completeness and readiness."""
        issues: List[ValidationIssue] = []
        
        if not request.seller_name or not request.seller_name.strip():
            issues.append(ValidationIssue(
                field="seller_name",
                severity="error",
                message="Seller name is required for XML generation",
                suggestion="Provide the seller's legal name (will be used in XML)"
            ))
        
        if len(request.seller_name) > 100:
            issues.append(ValidationIssue(
                field="seller_name",
                severity="warning",
                message="Seller name exceeds 100 characters, may be truncated in XML",
                suggestion="Consider shortening seller name to 100 characters or less"
            ))
        
        if request.seller_address and len(request.seller_address) > 200:
            issues.append(ValidationIssue(
                field="seller_address",
                severity="warning",
                message="Seller address exceeds 200 characters, may be truncated in XML",
                suggestion="Consider shortening address to 200 characters or less"
            ))
        
        for idx, item in enumerate(request.line_items, start=1):
            if not item.name or not item.name.strip():
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].name",
                    severity="error",
                    message="Line item name is required for XML generation",
                    suggestion="Provide a descriptive name for the line item"
                ))
            
            if len(item.name) > 200:
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].name",
                    severity="warning",
                    message="Line item name exceeds 200 characters, may be truncated in XML",
                    suggestion="Consider shortening item name to 200 characters or less"
                ))
        
        if not request.invoice_type or request.invoice_type not in ["388", "383", "381"]:
            issues.append(ValidationIssue(
                field="invoice_type",
                severity="warning",
                message="Invoice type should be 388 (Standard), 383 (Simplified), or 381 (Debit Note)",
                suggestion="Verify invoice type code matches ZATCA requirements"
            ))
        
        return issues
    
    def _validate_high_risk_patterns(self, request: InvoiceRequest) -> List[ValidationIssue]:
        """Validates high-risk patterns commonly leading to ZATCA rejection."""
        issues: List[ValidationIssue] = []
        
        if request.total_amount <= 0:
            issues.append(ValidationIssue(
                field="total_amount",
                severity="error",
                message="Invoice total must be greater than zero",
                suggestion="Ensure invoice total is a positive value"
            ))
        
        if request.total_tax_amount < 0:
            issues.append(ValidationIssue(
                field="total_tax_amount",
                severity="error",
                message="Negative tax amount will cause ZATCA rejection",
                suggestion="Verify tax calculations and ensure tax amount is zero or positive"
            ))
        
        if request.total_tax_exclusive < 0:
            issues.append(ValidationIssue(
                field="total_tax_exclusive",
                severity="error",
                message="Negative tax-exclusive amount will cause ZATCA rejection",
                suggestion="Ensure tax-exclusive amount is zero or positive"
            ))
        
        calculated_total = request.total_tax_exclusive + request.total_tax_amount
        expected_total = calculated_total
        
        tolerance = 0.01
        if abs(expected_total - request.total_amount) > tolerance:
            issues.append(ValidationIssue(
                field="total_amount",
                severity="error",
                message="Total amount calculation mismatch - high risk for ZATCA rejection",
                suggestion=f"Recalculate: total_amount = total_tax_exclusive + total_tax_amount = {expected_total:.2f} SAR"
            ))
        
        if request.total_tax_amount > 0 and request.total_tax_exclusive == 0:
            issues.append(ValidationIssue(
                field="total_tax_exclusive",
                severity="error",
                message="Tax amount exists but tax-exclusive amount is zero - invalid for ZATCA",
                suggestion="Ensure tax-exclusive amount is greater than zero when tax is applied"
            ))
        
        for idx, item in enumerate(request.line_items, start=1):
            if item.tax_rate > 0 and item.subtotal == 0:
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}]",
                    severity="error",
                    message="Line item has tax rate but zero subtotal - will cause ZATCA rejection",
                    suggestion="Either set tax rate to 0% or ensure subtotal is greater than zero"
                ))
            
            if item.tax_amount < 0:
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].tax_amount",
                    severity="error",
                    message="Negative line item tax amount will cause ZATCA rejection",
                    suggestion="Recalculate tax amount: subtotal × tax_rate / 100"
                ))
            
            if item.discount and item.discount >= item.subtotal:
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].discount",
                    severity="error",
                    message="Discount equals or exceeds subtotal - invalid for ZATCA",
                    suggestion=f"Reduce discount to less than subtotal ({item.subtotal:.2f} SAR)"
                ))
        
        if not request.seller_tax_number or not request.seller_tax_number.isdigit():
            issues.append(ValidationIssue(
                field="seller_tax_number",
                severity="error",
                message="Seller VAT number must contain only digits - non-numeric will cause rejection",
                suggestion="Remove any non-numeric characters from VAT number"
            ))
        
        if request.buyer_tax_number and len(request.buyer_tax_number) != self.REQUIRED_TAX_NUMBER_LENGTH:
            issues.append(ValidationIssue(
                field="buyer_tax_number",
                severity="warning",
                message="Buyer VAT number should be 15 digits if provided",
                suggestion="Either provide a valid 15-digit VAT number or omit buyer_tax_number"
            ))
        
        return issues
    
    def _validate_data_consistency(self, request: InvoiceRequest) -> List[ValidationIssue]:
        """
        Validates internal data consistency (NOT payload vs calculated).
        
        CRITICAL: Payload totals are NON-AUTHORITATIVE and are overridden before validation.
        This method only checks internal consistency of line items and their relationships.
        """
        issues: List[ValidationIssue] = []
        
        if not request.line_items:
            return issues
        
        # CRITICAL: TaxExclusiveAmount must be SUM(line_taxable) where line_taxable = (qty × price) − discount
        calculated_taxable = sum(item.taxable_amount for item in request.line_items)
        calculated_tax = sum(item.tax_amount for item in request.line_items)
        calculated_total = calculated_taxable + calculated_tax
        
        tolerance = 0.01
        
        # Validate internal consistency: request totals should match calculated (they were overridden)
        # This is a sanity check to ensure the override worked correctly
        if abs(calculated_taxable - request.total_tax_exclusive) > tolerance:
            issues.append(ValidationIssue(
                field="total_tax_exclusive",
                severity="error",
                message=f"Internal consistency error: Calculated tax-exclusive ({calculated_taxable:.2f}) != request total_tax_exclusive ({request.total_tax_exclusive:.2f}). This should not happen after totals override.",
                suggestion="System should have overridden total_tax_exclusive with calculated value. This indicates a bug."
            ))
        
        if abs(calculated_tax - request.total_tax_amount) > tolerance:
            issues.append(ValidationIssue(
                field="total_tax_amount",
                severity="error",
                message=f"Internal consistency error: Calculated tax ({calculated_tax:.2f}) != request total_tax_amount ({request.total_tax_amount:.2f}). This should not happen after totals override.",
                suggestion="System should have overridden total_tax_amount with calculated value. This indicates a bug."
            ))
        
        if abs(calculated_total - request.total_amount) > tolerance:
            issues.append(ValidationIssue(
                field="total_amount",
                severity="error",
                message=f"Internal consistency error: Calculated total ({calculated_total:.2f}) != request total_amount ({request.total_amount:.2f}). This should not happen after totals override.",
                suggestion="System should have overridden total_amount with calculated value. This indicates a bug."
            ))
        
        for idx, item in enumerate(request.line_items, start=1):
            expected_tax = item.taxable_amount * (item.tax_rate / 100.0)
            if abs(item.tax_amount - expected_tax) > tolerance:
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].tax_amount",
                    severity="error",
                    message=f"Inconsistent tax calculation. Expected: {expected_tax:.2f}, provided: {item.tax_amount:.2f}",
                    suggestion=f"Recalculate: taxable_amount ({item.taxable_amount:.2f}) × tax_rate ({item.tax_rate}%) = {expected_tax:.2f} SAR"
                ))
        
        return issues
    
    def _validate_vat_breakdown(self, request: InvoiceRequest) -> List[ValidationIssue]:
        """Validates VAT breakdown and categorization."""
        issues: List[ValidationIssue] = []
        
        if not request.line_items:
            return issues
        
        standard_rate_items = [item for item in request.line_items if item.tax_category.value == "S"]
        zero_rated_items = [item for item in request.line_items if item.tax_category.value == "Z"]
        exempt_items = [item for item in request.line_items if item.tax_category.value == "E"]
        
        for idx, item in enumerate(request.line_items, start=1):
            if item.tax_category.value == "S" and item.tax_rate != self.REQUIRED_VAT_RATE:
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].tax_rate",
                    severity="error",
                    message=f"Standard rate items must use {self.REQUIRED_VAT_RATE}% VAT rate",
                    suggestion=f"Set tax_rate to {self.REQUIRED_VAT_RATE}% for standard rate items"
                ))
            
            if item.tax_category.value == "Z" and item.tax_rate != 0:
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].tax_rate",
                    severity="error",
                    message="Zero-rated items must have 0% tax rate",
                    suggestion="Set tax_rate to 0% for zero-rated items"
                ))
            
            if item.tax_category.value == "E" and item.tax_rate != 0:
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].tax_rate",
                    severity="error",
                    message="Exempt items must have 0% tax rate",
                    suggestion="Set tax_rate to 0% for exempt items"
                ))
        
        total_standard_tax = sum(item.tax_amount for item in standard_rate_items)
        if abs(total_standard_tax - request.total_tax_amount) > 0.01:
            if zero_rated_items or exempt_items:
                issues.append(ValidationIssue(
                    field="total_tax_amount",
                    severity="warning",
                    message="Total tax should only include standard rate items",
                    suggestion="Verify total_tax_amount matches sum of standard rate item taxes only"
                ))
        
        if len(standard_rate_items) == 0 and request.total_tax_amount > 0:
            issues.append(ValidationIssue(
                field="total_tax_amount",
                severity="error",
                message="No standard rate items but tax amount is greater than zero",
                suggestion="Either add standard rate items or set total_tax_amount to zero"
            ))
        
        return issues

