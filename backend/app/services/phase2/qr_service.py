"""
QR code generation service for Phase-2 invoices.

Generates QR codes containing invoice summary data, XML hash, and digital signature
according to ZATCA Phase-2 specifications.
Uses TLV (Tag-Length-Value) encoding format for QR data.
Handles encoding and Base64 conversion of QR code images.
Does not handle QR code scanning, validation, or Phase-1 QR code generation.
"""

import base64
import io
from typing import Dict
from datetime import datetime

try:
    import qrcode
    from PIL import Image
except ImportError:
    qrcode = None


class Phase2QRService:
    """Generates QR codes for ZATCA Phase-2 invoices using TLV encoding."""
    
    TAG_SELLER_NAME = 1
    TAG_SELLER_VAT = 2
    TAG_INVOICE_TIMESTAMP = 3
    TAG_INVOICE_TOTAL = 4
    TAG_VAT_AMOUNT = 5
    TAG_XML_HASH = 6
    TAG_DIGITAL_SIGNATURE = 7
    
    def __init__(self, error_correction: str = "M", box_size: int = 10, border: int = 4):
        """
        Initializes QR code service.
        
        Args:
            error_correction: Error correction level (L, M, Q, H)
            box_size: Size of each box in pixels
            border: Border thickness in boxes
        """
        self.error_correction = error_correction
        self.box_size = box_size
        self.border = border
    
    def generate(
        self,
        seller_name: str,
        seller_tax_number: str,
        invoice_date: datetime,
        invoice_total: float,
        invoice_tax_amount: float,
        xml_hash: str,
        digital_signature: str = ""
    ) -> Dict[str, str]:
        """
        Generates QR code data for Phase-2 invoice using TLV encoding.
        
        Args:
            seller_name: Seller legal name
            seller_tax_number: Seller VAT registration number (15 digits)
            invoice_date: Invoice date and time
            invoice_total: Total invoice amount (with VAT)
            invoice_tax_amount: Total tax amount
            xml_hash: SHA-256 hash of XML invoice (64 hex chars)
            digital_signature: Digital signature value (optional for sandbox)
            
        Returns:
            Dictionary containing QR code data and Base64-encoded image
            Returns empty QR code if qrcode library is not available
        """
        if qrcode is None:
            # Return empty QR code - will use clearance QR from ZATCA if available
            return {
                "qr_data": "",
                "qr_code_base64": ""
            }
        
        tlv_data = self._build_tlv_encoded_data(
            seller_name=seller_name,
            seller_tax_number=seller_tax_number,
            invoice_date=invoice_date,
            invoice_total=invoice_total,
            invoice_tax_amount=invoice_tax_amount,
            xml_hash=xml_hash,
            digital_signature=digital_signature
        )
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=getattr(qrcode.constants, f"ERROR_CORRECT_{self.error_correction}"),
            box_size=self.box_size,
            border=self.border
        )
        
        qr.add_data(tlv_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        return {
            "qr_data": tlv_data,
            "qr_code_base64": qr_code_base64
        }
    
    def _build_tlv_encoded_data(
        self,
        seller_name: str,
        seller_tax_number: str,
        invoice_date: datetime,
        invoice_total: float,
        invoice_tax_amount: float,
        xml_hash: str,
        digital_signature: str
    ) -> str:
        """
        Builds TLV-encoded data string for Phase-2 QR code.
        
        Format: Tag (1 byte) + Length (1 byte) + Value (variable)
        """
        tlv_parts = []
        
        # Tag 1: Seller Name
        seller_name_bytes = seller_name.encode("utf-8")
        tlv_parts.append(bytes([self.TAG_SELLER_NAME, len(seller_name_bytes)]) + seller_name_bytes)
        
        # Tag 2: Seller VAT Number
        vat_bytes = seller_tax_number.encode("utf-8")
        tlv_parts.append(bytes([self.TAG_SELLER_VAT, len(vat_bytes)]) + vat_bytes)
        
        # Tag 3: Invoice Timestamp (ISO-8601 format)
        timestamp_str = invoice_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        timestamp_bytes = timestamp_str.encode("utf-8")
        tlv_parts.append(bytes([self.TAG_INVOICE_TIMESTAMP, len(timestamp_bytes)]) + timestamp_bytes)
        
        # Tag 4: Invoice Total (with VAT)
        total_str = f"{invoice_total:.2f}"
        total_bytes = total_str.encode("utf-8")
        tlv_parts.append(bytes([self.TAG_INVOICE_TOTAL, len(total_bytes)]) + total_bytes)
        
        # Tag 5: VAT Amount
        tax_str = f"{invoice_tax_amount:.2f}"
        tax_bytes = tax_str.encode("utf-8")
        tlv_parts.append(bytes([self.TAG_VAT_AMOUNT, len(tax_bytes)]) + tax_bytes)
        
        # Tag 6: XML Hash (64 hex characters)
        hash_bytes = xml_hash.encode("utf-8")
        tlv_parts.append(bytes([self.TAG_XML_HASH, len(hash_bytes)]) + hash_bytes)
        
        # Tag 7: Digital Signature (if provided)
        if digital_signature:
            sig_bytes = digital_signature.encode("utf-8")
            tlv_parts.append(bytes([self.TAG_DIGITAL_SIGNATURE, len(sig_bytes)]) + sig_bytes)
        
        # Combine all TLV parts
        tlv_data = b"".join(tlv_parts)
        
        # Return as Base64-encoded string for QR code
        return base64.b64encode(tlv_data).decode("utf-8")

