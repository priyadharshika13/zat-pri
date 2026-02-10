"""
QR code generation service for Phase-1 invoices.

Generates QR codes containing invoice summary data according to ZATCA Phase-1 specifications.
Uses TLV (Tag-Length-Value) encoding format for QR data.
Handles encoding and Base64 conversion of QR code images.
Does not handle QR code scanning, validation, or Phase-2 QR code generation.
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
    Image = None


class QRService:
    """Generates QR codes for ZATCA Phase-1 invoices using TLV encoding."""
    
    TAG_SELLER_NAME = 1
    TAG_SELLER_VAT = 2
    TAG_INVOICE_TIMESTAMP = 3
    TAG_INVOICE_TOTAL = 4
    TAG_VAT_AMOUNT = 5
    
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
        invoice_tax_amount: float
    ) -> Dict[str, str]:
        """
        Generates QR code data for Phase-1 invoice using TLV encoding.
        
        Args:
            seller_name: Seller legal name
            seller_tax_number: Seller VAT registration number (15 digits)
            invoice_date: Invoice date and time
            invoice_total: Total invoice amount
            invoice_tax_amount: Total tax amount
            
        Returns:
            Dictionary containing QR code data and Base64-encoded image
            
        Raises:
            RuntimeError: If qrcode library is not installed
        """
        if qrcode is None:
            raise RuntimeError("qrcode library is not installed")
        
        tlv_data = self._build_tlv_encoded_data(
            seller_name=seller_name,
            seller_tax_number=seller_tax_number,
            invoice_date=invoice_date,
            invoice_total=invoice_total,
            invoice_tax_amount=invoice_tax_amount
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
        invoice_tax_amount: float
    ) -> str:
        """
        Builds TLV-encoded QR code string according to ZATCA Phase-1 format.
        
        TLV format: Tag (1 byte) + Length (1 byte) + Value (variable)
        Fields encoded in order:
        1. Seller name
        2. Seller VAT number
        3. Invoice timestamp (ISO 8601)
        4. Invoice total amount
        5. VAT amount
        
        Args:
            seller_name: Seller legal name
            seller_tax_number: Seller VAT registration number
            invoice_date: Invoice date and time
            invoice_total: Total invoice amount
            invoice_tax_amount: Total tax amount
            
        Returns:
            TLV-encoded string for QR code
        """
        timestamp = invoice_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        invoice_total_str = f"{invoice_total:.2f}"
        vat_amount_str = f"{invoice_tax_amount:.2f}"
        
        tlv_parts = []
        
        tlv_parts.append(self._encode_tlv(self.TAG_SELLER_NAME, seller_name))
        tlv_parts.append(self._encode_tlv(self.TAG_SELLER_VAT, seller_tax_number))
        tlv_parts.append(self._encode_tlv(self.TAG_INVOICE_TIMESTAMP, timestamp))
        tlv_parts.append(self._encode_tlv(self.TAG_INVOICE_TOTAL, invoice_total_str))
        tlv_parts.append(self._encode_tlv(self.TAG_VAT_AMOUNT, vat_amount_str))
        
        return "".join(tlv_parts)
    
    def _encode_tlv(self, tag: int, value: str) -> str:
        """
        Encodes a single TLV field.
        
        Format: Tag (1 byte hex) + Length (1 byte hex) + Value (UTF-8)
        Tag and length are encoded as 2-digit hexadecimal strings.
        
        Args:
            tag: TLV tag identifier
            value: Field value to encode
            
        Returns:
            TLV-encoded string
        """
        value_bytes = value.encode("utf-8")
        length = len(value_bytes)
        
        if length > 255:
            raise ValueError(f"Value length {length} exceeds maximum TLV length of 255")
        
        tag_hex = f"{tag:02X}"
        length_hex = f"{length:02X}"
        
        return f"{tag_hex}{length_hex}{value}"
