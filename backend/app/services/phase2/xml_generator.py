"""
XML invoice generation service for Phase-2.

Generates Fatoora-compliant XML invoices according to ZATCA specifications.
Handles XML structure, namespaces, and required elements.
Does not handle XML signing, validation, or ZATCA API submission.
"""

import logging
import re

from app.core.config import get_settings
from app.schemas.invoice import InvoiceRequest
from app.utils.time_utils import normalize_invoice_date_to_utc
from app.utils.xml_utils import escape_xml

logger = logging.getLogger(__name__)


class XMLGenerator:
    """Generates ZATCA-compliant XML invoices."""
    
    def __init__(self):
        """Initializes XML generator with ZATCA namespace definitions."""
        self.namespaces = {
            "xmlns": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
            "xmlns:cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "xmlns:cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
        }
    
    def generate(self, request: InvoiceRequest) -> str:
        """
        Generates XML invoice from request data.
        
        Args:
            request: Invoice request data
            
        Returns:
            XML invoice string
        """
        xml_parts = []
        xml_parts.append('<?xml version="1.0" encoding="UTF-8"?>')
        xml_parts.append('<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"')
        xml_parts.append('         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"')
        xml_parts.append('         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">')
        
        xml_parts.extend(self._generate_invoice_header(request))
        xml_parts.extend(self._generate_pih_reference(request))
        xml_parts.extend(self._generate_seller_party(request))
        xml_parts.extend(self._generate_buyer_party(request))
        xml_parts.extend(self._generate_line_items(request))
        xml_parts.extend(self._generate_totals(request))
        
        xml_parts.append('</Invoice>')
        
        xml_content = "\n".join(xml_parts)
        
        # CRITICAL: Validate XML has no unrendered template variables
        self._validate_xml_rendered(xml_content)
        
        # TEMPORARY: Verification log for Phase-2 flow validation
        if get_settings().debug:
            logger.info(f"[PHASE2_VERIFY] XML generated successfully, length: {len(xml_content)} bytes")
        
        return xml_content
    
    def _validate_xml_rendered(self, xml_content: str) -> None:
        """
        Validates that XML has no unrendered template variables.
        
        Raises:
            ValueError: If unrendered template variables are found
        """
        if "{" in xml_content or "}" in xml_content:
            # Check if braces are part of actual XML content (like namespaces) or unrendered templates
            lines = xml_content.split("\n")
            for line_num, line in enumerate(lines, start=1):
                # Skip XML namespace declarations and valid XML structures
                if "xmlns" in line or "urn:oasis" in line:
                    continue
                # Check for unrendered Python f-string patterns
                if "{" in line and "}" in line:
                    # Check if it looks like an unrendered template (contains Python format specifiers)
                    unrendered_pattern = re.compile(r'\{[^}]*(?:\.\d+f|\.\d+d|item\.|request\.)[^}]*\}')
                    if unrendered_pattern.search(line):
                        raise ValueError(
                            f"Unrendered template variable found in XML at line {line_num}: {line.strip()[:100]}"
                        )
    
    def _generate_invoice_header(self, request: InvoiceRequest) -> list[str]:
        """Generates invoice header elements. IssueDate/IssueTime are always UTC."""
        elements = []
        dt_utc = normalize_invoice_date_to_utc(request.invoice_date)
        elements.append(f'  <cbc:ID>{escape_xml(request.invoice_number)}</cbc:ID>')
        elements.append(f'  <cbc:IssueDate>{dt_utc.strftime("%Y-%m-%d")}</cbc:IssueDate>')
        elements.append(f'  <cbc:IssueTime>{dt_utc.strftime("%H:%M:%S")}</cbc:IssueTime>')
        elements.append(f'  <cbc:InvoiceTypeCode>{request.invoice_type}</cbc:InvoiceTypeCode>')
        if request.uuid:
            elements.append(f'  <cbc:UUID>{escape_xml(request.uuid)}</cbc:UUID>')
        return elements

    def _generate_pih_reference(self, request: InvoiceRequest) -> list[str]:
        """
        Generates PIH (Previous Invoice Hash) AdditionalDocumentReference when present.
        ZATCA: omit for first invoice; include for all subsequent invoices in the chain.
        """
        pih = (request.previous_invoice_hash or "").strip().lower()
        if not pih:
            return []
        elements = []
        elements.append('  <cac:AdditionalDocumentReference>')
        elements.append('    <cbc:ID>PIH</cbc:ID>')
        elements.append('    <cac:Attachment>')
        elements.append(f'      <cbc:EmbeddedDocumentBinaryObject mimeCode="text/plain" encodingCode="UTF-8">{escape_xml(pih)}</cbc:EmbeddedDocumentBinaryObject>')
        elements.append('    </cac:Attachment>')
        elements.append('  </cac:AdditionalDocumentReference>')
        return elements
    
    def _generate_seller_party(self, request: InvoiceRequest) -> list[str]:
        """Generates seller party information."""
        elements = []
        elements.append('  <cac:AccountingSupplierParty>')
        elements.append('    <cac:Party>')
        elements.append('      <cac:PartyName>')
        elements.append(f'        <cbc:Name>{escape_xml(request.seller_name)}</cbc:Name>')
        elements.append('      </cac:PartyName>')
        elements.append('      <cac:PartyTaxScheme>')
        elements.append(f'        <cbc:CompanyID>{escape_xml(request.seller_tax_number)}</cbc:CompanyID>')
        elements.append('      </cac:PartyTaxScheme>')
        if request.seller_address:
            elements.append('      <cac:PostalAddress>')
            elements.append(f'        <cbc:StreetName>{escape_xml(request.seller_address)}</cbc:StreetName>')
            elements.append('      </cac:PostalAddress>')
        elements.append('    </cac:Party>')
        elements.append('  </cac:AccountingSupplierParty>')
        return elements
    
    def _generate_buyer_party(self, request: InvoiceRequest) -> list[str]:
        """Generates buyer party information."""
        elements = []
        elements.append('  <cac:AccountingCustomerParty>')
        elements.append('    <cac:Party>')
        if request.buyer_name:
            elements.append('      <cac:PartyName>')
            elements.append(f'        <cbc:Name>{escape_xml(request.buyer_name)}</cbc:Name>')
            elements.append('      </cac:PartyName>')
        if request.buyer_tax_number:
            elements.append('      <cac:PartyTaxScheme>')
            elements.append(f'        <cbc:CompanyID>{escape_xml(request.buyer_tax_number)}</cbc:CompanyID>')
            elements.append('      </cac:PartyTaxScheme>')
        elements.append('    </cac:Party>')
        elements.append('  </cac:AccountingCustomerParty>')
        return elements
    
    def _generate_line_items(self, request: InvoiceRequest) -> list[str]:
        """
        Generates invoice line items with ZATCA-compliant discount handling.
        
        For lines with discount:
        - Unit price remains original (not reduced)
        - Discount represented using <cac:AllowanceCharge> with ChargeIndicator=false
        - TaxableAmount = (qty × unit_price) - discount
        """
        elements = []
        for idx, item in enumerate(request.line_items, start=1):
            elements.append('  <cac:InvoiceLine>')
            elements.append(f'    <cbc:ID>{idx}</cbc:ID>')
            elements.append(f'    <cbc:InvoicedQuantity unitCode="C62">{item.quantity}</cbc:InvoicedQuantity>')
            elements.append('    <cac:Item>')
            elements.append(f'      <cbc:Name>{escape_xml(item.name)}</cbc:Name>')
            elements.append('    </cac:Item>')
            
            # Price: Always use original unit price (NOT reduced by discount)
            elements.append('    <cac:Price>')
            elements.append(f'      <cbc:PriceAmount currencyID="SAR">{item.unit_price:.2f}</cbc:PriceAmount>')
            elements.append('    </cac:Price>')
            
            # AllowanceCharge: Add only if discount > 0
            discount_amount = item.discount or 0.0
            if discount_amount > 0:
                elements.append('    <cac:AllowanceCharge>')
                elements.append('      <cbc:ChargeIndicator>false</cbc:ChargeIndicator>')
                elements.append(f'      <cbc:Amount currencyID="SAR">{discount_amount:.2f}</cbc:Amount>')
                elements.append('    </cac:AllowanceCharge>')
            
            # TaxTotal: TaxableAmount = (qty × unit_price) - discount
            # This matches item.subtotal calculation
            line_taxable = item.taxable_amount
            
            elements.append('    <cac:TaxTotal>')
            elements.append(f'      <cbc:TaxAmount currencyID="SAR">{item.tax_amount:.2f}</cbc:TaxAmount>')
            elements.append('      <cac:TaxSubtotal>')
            # CRITICAL: TaxableAmount = gross - discount (matches ZATCA requirement)
            elements.append(f'        <cbc:TaxableAmount currencyID="SAR">{line_taxable:.2f}</cbc:TaxableAmount>')
            elements.append(f'        <cbc:TaxAmount currencyID="SAR">{item.tax_amount:.2f}</cbc:TaxAmount>')
            elements.append('        <cac:TaxCategory>')
            elements.append(f'          <cbc:ID>{item.tax_category.value}</cbc:ID>')
            elements.append(f'          <cbc:Percent>{item.tax_rate:.2f}</cbc:Percent>')
            elements.append('        </cac:TaxCategory>')
            elements.append('      </cac:TaxSubtotal>')
            elements.append('    </cac:TaxTotal>')
            elements.append('  </cac:InvoiceLine>')
        return elements
    
    def _generate_totals(self, request: InvoiceRequest) -> list[str]:
        """
        Generates invoice totals with ZATCA-compliant structure.
        
        CRITICAL: Totals MUST be computed from line values:
        - TaxExclusiveAmount = SUM(all line_taxable) where line_taxable = (qty × price) - discount
        - TaxTotal = SUM(all line_vat) where line_vat = line_taxable × 0.15
        - TaxInclusiveAmount = TaxExclusiveAmount + TaxTotal
        - PayableAmount = TaxInclusiveAmount
        
        NO hardcoding. NO recomputing VAT percent from totals.
        """
        elements = []
        elements.append('  <cac:LegalMonetaryTotal>')
        # CRITICAL: These values are system-calculated from line items (overridden before validation)
        # Payload totals are NON-AUTHORITATIVE - system is source of truth
        elements.append(f'    <cbc:TaxExclusiveAmount currencyID="SAR">{request.total_tax_exclusive:.2f}</cbc:TaxExclusiveAmount>')
        elements.append(f'    <cbc:TaxInclusiveAmount currencyID="SAR">{request.total_amount:.2f}</cbc:TaxInclusiveAmount>')
        elements.append(f'    <cbc:PayableAmount currencyID="SAR">{request.total_amount:.2f}</cbc:PayableAmount>')
        elements.append('  </cac:LegalMonetaryTotal>')
        elements.append('  <cac:TaxTotal>')
        # CRITICAL: TaxTotal is system-calculated (SUM of all line VAT amounts)
        elements.append(f'    <cbc:TaxAmount currencyID="SAR">{request.total_tax_amount:.2f}</cbc:TaxAmount>')
        # Add TaxSubtotal for ZATCA compliance
        if request.total_tax_amount > 0:
            # CRITICAL: Use the SAME tax rate from line items, never recompute from totals
            # Find the tax rate from standard rate line items (should be 15.00)
            standard_tax_rate = None
            for item in request.line_items:
                if item.tax_category.value == "S" and item.tax_rate > 0:
                    standard_tax_rate = item.tax_rate
                    break
            
            # Fallback to 15.00 if no standard rate found (should not happen in valid invoices)
            if standard_tax_rate is None:
                standard_tax_rate = 15.00
                logger.warning("No standard tax rate found in line items, using default 15.00%")
            
            elements.append('    <cac:TaxSubtotal>')
            elements.append(f'      <cbc:TaxableAmount currencyID="SAR">{request.total_tax_exclusive:.2f}</cbc:TaxableAmount>')
            elements.append(f'      <cbc:TaxAmount currencyID="SAR">{request.total_tax_amount:.2f}</cbc:TaxAmount>')
            elements.append('      <cac:TaxCategory>')
            # Use standard VAT category (S) for main tax
            elements.append('        <cbc:ID>S</cbc:ID>')
            # CRITICAL: Use the SAME tax rate from line items (15.00), never recompute
            elements.append(f'        <cbc:Percent>{standard_tax_rate:.2f}</cbc:Percent>')
            elements.append('      </cac:TaxCategory>')
            elements.append('    </cac:TaxSubtotal>')
        elements.append('  </cac:TaxTotal>')
        return elements

