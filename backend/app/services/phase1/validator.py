"""
Phase-1 invoice validator.

Validates invoices for ZATCA Phase-1 compliance before processing.
Checks mandatory fields, VAT calculations, QR code eligibility, and total consistency.
Does not handle Phase-2 validation, HTTP objects, or external API calls.
"""

import logging
from typing import List

from app.schemas.invoice import InvoiceRequest
from app.schemas.validation import ValidationResponse, ValidationIssue

logger = logging.getLogger(__name__)


class Phase1Validator:
    """Validates invoices for Phase-1 compliance."""
    
    REQUIRED_VAT_RATE = 15.0
    REQUIRED_TAX_NUMBER_LENGTH = 15
    
    async def validate(self, request: InvoiceRequest) -> ValidationResponse:
        """
        Validates invoice according to ZATCA Phase-1 rules.
        
        Args:
            request: Invoice request to validate
            
        Returns:
            Validation response with status, issues, and suggestions
        """
        logger.debug(f"Validating Phase-1 invoice: {request.invoice_number}")
        
        issues: List[ValidationIssue] = []
        
        issues.extend(self._validate_mandatory_fields(request))
        issues.extend(self._validate_vat_calculations(request))
        issues.extend(self._validate_qr_eligibility(request))
        issues.extend(self._validate_totals_consistency(request))
        
        status = "PASS" if not any(issue.severity == "error" for issue in issues) else "FAIL"
        suggestions = [issue.suggestion for issue in issues if issue.suggestion]
        
        return ValidationResponse(
            status=status,
            issues=issues,
            suggestions=suggestions
        )
    
    def _validate_mandatory_fields(self, request: InvoiceRequest) -> List[ValidationIssue]:
        """Validates presence of all mandatory invoice fields."""
        issues: List[ValidationIssue] = []
        
        if not request.invoice_number or not request.invoice_number.strip():
            issues.append(ValidationIssue(
                field="invoice_number",
                severity="error",
                message="Invoice number is mandatory",
                suggestion="Provide a unique invoice number"
            ))
        
        if not request.invoice_date:
            issues.append(ValidationIssue(
                field="invoice_date",
                severity="error",
                message="Invoice date is mandatory",
                suggestion="Provide a valid invoice date"
            ))
        
        if not request.seller_name or not request.seller_name.strip():
            issues.append(ValidationIssue(
                field="seller_name",
                severity="error",
                message="Seller name is mandatory",
                suggestion="Provide the seller's legal name"
            ))
        
        if not request.seller_tax_number:
            issues.append(ValidationIssue(
                field="seller_tax_number",
                severity="error",
                message="Seller VAT registration number is mandatory",
                suggestion="Provide a 15-digit Saudi VAT registration number"
            ))
        elif len(request.seller_tax_number) != self.REQUIRED_TAX_NUMBER_LENGTH:
            issues.append(ValidationIssue(
                field="seller_tax_number",
                severity="error",
                message=f"Seller VAT number must be exactly {self.REQUIRED_TAX_NUMBER_LENGTH} digits",
                suggestion=f"Ensure the VAT number is exactly {self.REQUIRED_TAX_NUMBER_LENGTH} digits"
            ))
        elif not request.seller_tax_number.isdigit():
            issues.append(ValidationIssue(
                field="seller_tax_number",
                severity="error",
                message="Seller VAT number must contain only digits",
                suggestion="Remove any non-numeric characters from the VAT number"
            ))
        
        if not request.line_items or len(request.line_items) == 0:
            issues.append(ValidationIssue(
                field="line_items",
                severity="error",
                message="At least one line item is mandatory",
                suggestion="Add at least one invoice line item"
            ))
        
        return issues
    
    def _validate_vat_calculations(self, request: InvoiceRequest) -> List[ValidationIssue]:
        """Validates VAT calculations are correct (15%)."""
        issues: List[ValidationIssue] = []
        
        if not request.line_items:
            return issues
        
        for idx, item in enumerate(request.line_items, start=1):
            if item.tax_rate != self.REQUIRED_VAT_RATE:
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].tax_rate",
                    severity="error",
                    message=f"VAT rate must be {self.REQUIRED_VAT_RATE}% for ZATCA Phase-1",
                    suggestion=f"Set tax rate to {self.REQUIRED_VAT_RATE}% for all taxable items"
                ))
            
            expected_tax = item.subtotal * (self.REQUIRED_VAT_RATE / 100.0)
            tolerance = 0.01
            
            if abs(item.tax_amount - expected_tax) > tolerance:
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].tax_amount",
                    severity="error",
                    message=f"Tax amount calculation incorrect. Expected {expected_tax:.2f}, got {item.tax_amount:.2f}",
                    suggestion=f"Recalculate tax as: subtotal × {self.REQUIRED_VAT_RATE}% = {expected_tax:.2f} SAR"
                ))
        
        total_expected_tax = sum(item.taxable_amount * (self.REQUIRED_VAT_RATE / 100.0) for item in request.line_items)
        tolerance = 0.01
        
        if abs(request.total_tax_amount - total_expected_tax) > tolerance:
            issues.append(ValidationIssue(
                field="total_tax_amount",
                severity="error",
                message=f"Total tax amount mismatch. Expected {total_expected_tax:.2f}, got {request.total_tax_amount:.2f}",
                suggestion=f"Recalculate total tax as sum of all line item taxes: {total_expected_tax:.2f} SAR"
            ))
        
        return issues
    
    def _validate_qr_eligibility(self, request: InvoiceRequest) -> List[ValidationIssue]:
        """Validates invoice eligibility for QR code generation."""
        issues: List[ValidationIssue] = []
        
        if not request.seller_tax_number or len(request.seller_tax_number) != self.REQUIRED_TAX_NUMBER_LENGTH:
            issues.append(ValidationIssue(
                field="seller_tax_number",
                severity="error",
                message="Invalid seller VAT number prevents QR code generation",
                suggestion="Provide a valid 15-digit Saudi VAT registration number"
            ))
        
        if not request.invoice_date:
            issues.append(ValidationIssue(
                field="invoice_date",
                severity="error",
                message="Invoice date is required for QR code generation",
                suggestion="Provide a valid invoice date"
            ))
        
        if request.total_amount <= 0:
            issues.append(ValidationIssue(
                field="total_amount",
                severity="error",
                message="Invoice total must be greater than zero for QR code generation",
                suggestion="Ensure invoice total is a positive value"
            ))
        
        if request.total_tax_amount < 0:
            issues.append(ValidationIssue(
                field="total_tax_amount",
                severity="warning",
                message="Negative tax amount may cause QR code issues",
                suggestion="Verify tax calculations are correct"
            ))
        
        return issues
    
    def _validate_totals_consistency(self, request: InvoiceRequest) -> List[ValidationIssue]:
        """Validates consistency between totals and line items."""
        issues: List[ValidationIssue] = []
        
        if not request.line_items:
            return issues
        
        # Use canonical taxable amount (qty × price − discount)
        calculated_subtotal = sum(item.taxable_amount for item in request.line_items)
        calculated_tax = sum(item.tax_amount for item in request.line_items)
        calculated_total = sum(item.total for item in request.line_items)
        
        tolerance = 0.01
        
        # Do NOT subtract request.total_discount here; line discounts are already included in taxable_amount
        if abs(calculated_subtotal - request.total_tax_exclusive) > tolerance:
            issues.append(ValidationIssue(
                field="total_tax_exclusive",
                severity="error",
                message=f"Tax-exclusive total mismatch. Calculated: {calculated_subtotal:.2f}, provided: {request.total_tax_exclusive:.2f}",
                suggestion=f"Set total_tax_exclusive to {calculated_subtotal:.2f} SAR (sum of line taxable amounts)"
            ))
        
        if abs(calculated_tax - request.total_tax_amount) > tolerance:
            issues.append(ValidationIssue(
                field="total_tax_amount",
                severity="error",
                message=f"Total tax mismatch. Calculated: {calculated_tax:.2f}, provided: {request.total_tax_amount:.2f}",
                suggestion=f"Set total_tax_amount to {calculated_tax:.2f} SAR (sum of all line item taxes)"
            ))
        
        expected_total = request.total_tax_exclusive + request.total_tax_amount
        if abs(expected_total - request.total_amount) > tolerance:
            issues.append(ValidationIssue(
                field="total_amount",
                severity="error",
                message=f"Total amount mismatch. Calculated: {expected_total:.2f}, provided: {request.total_amount:.2f}",
                suggestion=f"Set total_amount to {expected_total:.2f} SAR (tax_exclusive + tax_amount)"
            ))
        
        for idx, item in enumerate(request.line_items, start=1):
            if item.quantity <= 0:
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].quantity",
                    severity="error",
                    message="Line item quantity must be greater than zero",
                    suggestion="Ensure quantity is a positive number"
                ))
            
            if item.unit_price < 0:
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].unit_price",
                    severity="error",
                    message="Line item unit price cannot be negative",
                    suggestion="Ensure unit price is zero or positive"
                ))
            
            # Discount must not exceed gross (qty × unit_price)
            if item.discount and item.discount > (item.quantity * item.unit_price):
                issues.append(ValidationIssue(
                    field=f"line_items[{idx}].discount",
                    severity="error",
                    message="Line item discount cannot exceed subtotal",
                    suggestion=f"Reduce discount to maximum {(item.quantity * item.unit_price):.2f} SAR"
                ))
        
        return issues
