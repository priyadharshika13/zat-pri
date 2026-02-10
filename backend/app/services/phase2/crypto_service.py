"""
Cryptographic service for Phase-2 invoices.

Handles XML canonicalization, hashing, and digital signature generation.
Implements SHA-256 hashing and RSA-SHA256 XMLDSig signing for ZATCA compliance.
Does not handle certificate management, key generation, or certificate validation.
"""

import base64
import hashlib
import logging
import re
import uuid
from datetime import datetime
from typing import Tuple, Optional
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

try:
    from lxml import etree as lxml_etree
    LXML_AVAILABLE = True
except ImportError:
    lxml_etree = None
    LXML_AVAILABLE = False

from app.core.config import get_settings
from app.core.exceptions import SigningNotConfiguredError

logger = logging.getLogger(__name__)


class CryptoService:
    """
    Cryptographic operations for Phase-2 invoices.
    
    Provides XML canonicalization, SHA-256 hashing, and placeholder ECDSA signing.
    Signing implementation is replaceable with production libraries (xmlsec, HSM).
    """
    
    def __init__(
        self,
        private_key_path: Optional[str] = None,
        certificate_path: Optional[str] = None
    ):
        """
        Initializes cryptographic service.
        
        Args:
            private_key_path: Path to private key file (optional for placeholder)
            certificate_path: Path to X.509 certificate file (optional for placeholder)
        """
        settings = get_settings()
        self.private_key_path = private_key_path or settings.signing_key_path
        self.certificate_path = certificate_path or settings.signing_certificate_path
    
    def compute_xml_hash(self, xml_content: str) -> str:
        """
        Computes SHA-256 hash of canonicalized XML content.
        
        Args:
            xml_content: XML invoice content
            
        Returns:
            64-character hexadecimal hash string (lowercase)
        """
        # CRITICAL: Validate XML has no unrendered templates before hashing
        if "{" in xml_content or "}" in xml_content:
            unrendered_pattern = re.compile(r'\{[^}]*(?:\.\d+f|\.\d+d|item\.|request\.)[^}]*\}')
            if unrendered_pattern.search(xml_content):
                raise ValueError("Cannot hash XML with unrendered template variables")
        
        canonical_xml = self._canonicalize_xml(xml_content)
        hash_bytes = hashlib.sha256(canonical_xml.encode("utf-8")).digest()
        xml_hash = hash_bytes.hex().lower()  # ZATCA requires lowercase hex
        
        # TEMPORARY: Verification log for Phase-2 flow validation
        if get_settings().debug:
            logger.info(f"[PHASE2_VERIFY] XML hash computed: {xml_hash[:16]}...{xml_hash[-8:]}")
        
        return xml_hash
    
    def _canonicalize_xml(self, xml_content: str) -> str:
        """
        Canonicalizes XML content for deterministic hashing.
        
        Performs basic canonicalization:
        - Removes XML declaration
        - Normalizes whitespace
        - Removes empty lines
        - Ensures consistent encoding
        
        Args:
            xml_content: Raw XML content
            
        Returns:
            Canonicalized XML string
        """
        lines = xml_content.split("\n")
        canonical_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("<?xml"):
                canonical_lines.append(stripped)
        
        return "\n".join(canonical_lines)
    
    async def sign(
        self,
        xml_content: str,
        environment: str = "SANDBOX",
        allow_placeholder: bool = True
    ) -> Tuple[str, str]:
        """
        Signs XML invoice content using XMLDSig (XML Digital Signature) with RSA-SHA256.

        When allow_placeholder=True (default): SANDBOX or missing keys may use placeholder
        (for preview/validation flows that never call clearance).
        When allow_placeholder=False (Phase-2 clearance path): REAL signing only;
        raises SigningNotConfiguredError if signing cannot be performed. No placeholder
        may be returned — ZATCA audit requirement.

        Args:
            xml_content: XML invoice to sign
            environment: Target environment (SANDBOX or PRODUCTION)
            allow_placeholder: If False, never use placeholder; fail with SigningNotConfiguredError

        Returns:
            Tuple of (signed_xml, digital_signature_base64)

        Raises:
            ValueError: If XML contains unrendered templates
            SigningNotConfiguredError: If allow_placeholder=False and real signing not possible
        """
        # CRITICAL: Validate XML is fully rendered before signing
        if "{" in xml_content or "}" in xml_content:
            unrendered_pattern = re.compile(r'\{[^}]*(?:\.\d+f|\.\d+d|item\.|request\.)[^}]*\}')
            if unrendered_pattern.search(xml_content):
                raise ValueError("Cannot sign XML with unrendered template variables")

        # Phase-2 clearance path: real signing only, no placeholder
        if not allow_placeholder:
            return await self._sign_real_only(xml_content, environment)

        # Legacy / preview path: allow placeholder for SANDBOX or when keys missing
        if environment.upper() == "SANDBOX":
            logger.debug("Using sandbox-safe placeholder signature (non-blocking)")
            signed_xml = self._apply_fast_placeholder_signature(xml_content)
            signature = self._extract_signature_from_xml(signed_xml)
            return signed_xml, signature

        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("cryptography library not available, using placeholder signature")
            signed_xml = self._apply_fast_placeholder_signature(xml_content)
            signature = self._extract_signature_from_xml(signed_xml)
            return signed_xml, signature

        if not self.private_key_path or not self.certificate_path:
            logger.warning("Signing keys not configured, using placeholder signature")
            signed_xml = self._apply_fast_placeholder_signature(xml_content)
            signature = self._extract_signature_from_xml(signed_xml)
            return signed_xml, signature

        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                signed_xml, signature_b64 = await loop.run_in_executor(
                    executor,
                    self._sign_xml_sync,
                    xml_content
                )
            if get_settings().debug:
                logger.info(f"[PHASE2_VERIFY] XML signed successfully, signature length: {len(signature_b64)}")
            return signed_xml, signature_b64
        except Exception as e:
            logger.error(f"Error in XML signing: {e}")
            signed_xml = self._apply_fast_placeholder_signature(xml_content)
            signature = self._extract_signature_from_xml(signed_xml)
            return signed_xml, signature

    async def _sign_real_only(self, xml_content: str, environment: str) -> Tuple[str, str]:
        """
        Real cryptographic signing only. Used when allow_placeholder=False (Phase-2 clearance).
        Raises SigningNotConfiguredError if signing cannot be performed; no placeholder.
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise SigningNotConfiguredError(
                "Cryptography library not available. Phase-2 requires real signing; "
                "install the cryptography package."
            )
        if not self.private_key_path or not self.certificate_path:
            raise SigningNotConfiguredError(
                "Signing keys not configured. Phase-2 requires per-tenant certificate and "
                "private key; upload certs or set paths."
            )
        key_path = Path(self.private_key_path)
        cert_path = Path(self.certificate_path)
        if not key_path.exists():
            raise SigningNotConfiguredError(f"Private key file not found: {self.private_key_path}")
        if not cert_path.exists():
            raise SigningNotConfiguredError(f"Certificate file not found: {self.certificate_path}")

        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                signed_xml, signature_b64 = await loop.run_in_executor(
                    executor,
                    self._sign_xml_sync,
                    xml_content
                )
        except SigningNotConfiguredError:
            raise
        except FileNotFoundError as e:
            raise SigningNotConfiguredError(str(e)) from e
        except Exception as e:
            logger.error(f"Phase-2 signing failed: {e}", exc_info=True)
            raise SigningNotConfiguredError(f"Signing failed: {e}") from e

        if get_settings().debug:
            logger.info(f"[PHASE2_VERIFY] XML signed successfully (real), signature length: {len(signature_b64)}")
        return signed_xml, signature_b64
    
    def _sign_xml_sync(self, xml_content: str) -> Tuple[str, str]:
        """
        Synchronous XML signing for production (runs in thread pool).
        
        This method contains blocking operations and should only be called
        from a thread pool executor.
        
        Args:
            xml_content: XML invoice to sign
            
        Returns:
            Tuple of (signed_xml, digital_signature_base64)
        """
        # Check if files exist (blocking but fast)
        if not Path(self.private_key_path).exists():
            raise FileNotFoundError(f"Private key file not found: {self.private_key_path}")
        
        if not Path(self.certificate_path).exists():
            raise FileNotFoundError(f"Certificate file not found: {self.certificate_path}")
        
        # Load private key and certificate (BLOCKING operations)
        with open(self.private_key_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        
        with open(self.certificate_path, 'rb') as f:
            certificate = x509.load_pem_x509_certificate(
                f.read(),
                default_backend()
            )
        
        # Parse XML (blocking but fast)
        root = ET.fromstring(xml_content)
        
        # Canonicalize XML for signing (C14N)
        canonical_xml = self._canonicalize_xml_for_signing(xml_content)
        
        # Compute SHA-256 hash of canonicalized XML
        hash_bytes = hashlib.sha256(canonical_xml.encode("utf-8")).digest()
        hash_b64 = base64.b64encode(hash_bytes).decode("utf-8")
        
        # Sign the hash with RSA-SHA256 (BLOCKING crypto operation)
        signature_bytes = private_key.sign(
            hash_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        signature_b64 = base64.b64encode(signature_bytes).decode("utf-8")
        
        # Get certificate in Base64
        cert_b64 = base64.b64encode(
            certificate.public_bytes(serialization.Encoding.DER)
        ).decode("utf-8")
        
        # Generate signature ID
        sig_id = f"Signature-{uuid.uuid4().hex[:8]}"
        signed_info_id = f"SignedInfo-{uuid.uuid4().hex[:8]}"
        reference_id = f"Reference-{uuid.uuid4().hex[:8]}"
        key_info_id = f"KeyInfo-{uuid.uuid4().hex[:8]}"
        
        # Create XMLDSig Signature element
        signature_elem = ET.Element(
            "{http://www.w3.org/2000/09/xmldsig#}Signature",
            attrib={"Id": sig_id}
        )
        
        # SignedInfo
        signed_info = ET.SubElement(
            signature_elem,
            "{http://www.w3.org/2000/09/xmldsig#}SignedInfo",
            attrib={"Id": signed_info_id}
        )
        
        # CanonicalizationMethod
        ET.SubElement(
            signed_info,
            "{http://www.w3.org/2000/09/xmldsig#}CanonicalizationMethod",
            attrib={"Algorithm": "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"}
        )
        
        # SignatureMethod
        ET.SubElement(
            signed_info,
            "{http://www.w3.org/2000/09/xmldsig#}SignatureMethod",
            attrib={"Algorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"}
        )
        
        # Reference
        reference = ET.SubElement(
            signed_info,
            "{http://www.w3.org/2000/09/xmldsig#}Reference",
            attrib={"URI": "", "Id": reference_id}
        )
        
        # Transforms
        transforms = ET.SubElement(reference, "{http://www.w3.org/2000/09/xmldsig#}Transforms")
        ET.SubElement(
            transforms,
            "{http://www.w3.org/2000/09/xmldsig#}Transform",
            attrib={"Algorithm": "http://www.w3.org/2000/09/xmldsig#enveloped-signature"}
        )
        ET.SubElement(
            transforms,
            "{http://www.w3.org/2000/09/xmldsig#}Transform",
            attrib={"Algorithm": "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"}
        )
        
        # DigestMethod
        ET.SubElement(
            reference,
            "{http://www.w3.org/2000/09/xmldsig#}DigestMethod",
            attrib={"Algorithm": "http://www.w3.org/2001/04/xmlenc#sha256"}
        )
        
        # DigestValue
        digest_value = ET.SubElement(
            reference,
            "{http://www.w3.org/2000/09/xmldsig#}DigestValue"
        )
        digest_value.text = hash_b64
        
        # SignatureValue
        sig_value = ET.SubElement(
            signature_elem,
            "{http://www.w3.org/2000/09/xmldsig#}SignatureValue"
        )
        sig_value.text = signature_b64
        
        # KeyInfo
        key_info = ET.SubElement(
            signature_elem,
            "{http://www.w3.org/2000/09/xmldsig#}KeyInfo",
            attrib={"Id": key_info_id}
        )
        
        # X509Data
        x509_data = ET.SubElement(key_info, "{http://www.w3.org/2000/09/xmldsig#}X509Data")
        x509_cert = ET.SubElement(x509_data, "{http://www.w3.org/2000/09/xmldsig#}X509Certificate")
        x509_cert.text = cert_b64
        
        # Append signature to root element
        root.append(signature_elem)
        
        # Convert back to string
        signed_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
        
        return signed_xml, signature_b64
    
    def _canonicalize_xml_for_signing(self, xml_content: str) -> str:
        """
        Canonicalizes XML content for signing using W3C Canonical XML (C14N).
        
        ZATCA signature verification expects the digest over C14N form. When lxml
        is available, uses W3C C14N (excluding Signature element). Otherwise falls
        back to line-based canonicalization for sandbox compatibility.
        
        Args:
            xml_content: Raw XML content (unsigned or signed; Signature is excluded)
            
        Returns:
            Canonicalized XML string ready for hashing/signing
        """
        if LXML_AVAILABLE and lxml_etree is not None:
            return self._canonicalize_xml_c14n(xml_content)
        # Fallback for environments without lxml (e.g. sandbox placeholder)
        lines = xml_content.split("\n")
        canonical_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("<?xml"):
                canonical_lines.append(stripped)
        return "\n".join(canonical_lines)

    def _canonicalize_xml_c14n(self, xml_content: str) -> str:
        """
        W3C Canonical XML 1.0 (C14N) for ZATCA signature digest.
        
        Serializes the document excluding the Signature element so the digest
        matches what XMLDSig enveloped-signature transform expects.
        """
        root = lxml_etree.fromstring(xml_content.encode("utf-8"))
        # Remove Signature element(s) so digest is over document without signature
        ns = "http://www.w3.org/2000/09/xmldsig#"
        for sig in root.findall(f".//{{{ns}}}Signature"):
            parent = sig.getparent()
            if parent is not None:
                parent.remove(sig)
        c14n_bytes = lxml_etree.tostring(
            root,
            method="c14n",
            exclusive=False,
            with_comments=False,
        )
        return c14n_bytes.decode("utf-8")
    
    def _apply_fast_placeholder_signature(self, xml_content: str) -> str:
        """
        Applies FAST placeholder signature to XML content for sandbox/testing.
        
        CRITICAL: This is instant and non-blocking. No file I/O, no crypto operations.
        ZATCA Sandbox does NOT require real cryptographic verification.
        
        Args:
            xml_content: XML invoice to sign
            
        Returns:
            XML with placeholder signature structure (unchanged XML + signature element)
        """
        try:
            # Parse XML (fast, in-memory operation)
            root = ET.fromstring(xml_content)
            
            # Create minimal signature element
            signature_elem = ET.Element(
                "{http://www.w3.org/2000/09/xmldsig#}Signature"
            )
            
            signed_info = ET.SubElement(
                signature_elem,
                "{http://www.w3.org/2000/09/xmldsig#}SignedInfo"
            )
            
            ET.SubElement(
                signed_info,
                "{http://www.w3.org/2000/09/xmldsig#}CanonicalizationMethod",
                attrib={"Algorithm": "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"}
            )
            
            ET.SubElement(
                signed_info,
                "{http://www.w3.org/2000/09/xmldsig#}SignatureMethod",
                attrib={"Algorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"}
            )
            
            reference = ET.SubElement(
                signed_info,
                "{http://www.w3.org/2000/09/xmldsig#}Reference",
                attrib={"URI": ""}
            )
            
            transforms = ET.SubElement(reference, "{http://www.w3.org/2000/09/xmldsig#}Transforms")
            ET.SubElement(
                transforms,
                "{http://www.w3.org/2000/09/xmldsig#}Transform",
                attrib={"Algorithm": "http://www.w3.org/2000/09/xmldsig#enveloped-signature"}
            )
            
            ET.SubElement(
                reference,
                "{http://www.w3.org/2000/09/xmldsig#}DigestMethod",
                attrib={"Algorithm": "http://www.w3.org/2001/04/xmlenc#sha256"}
            )
            
            # Use hash of canonicalized XML as placeholder (fast, in-memory)
            canonical_xml = self._canonicalize_xml_for_signing(xml_content)
            hash_bytes = hashlib.sha256(canonical_xml.encode("utf-8")).digest()
            hash_b64 = base64.b64encode(hash_bytes).decode("utf-8")
            
            digest_value = ET.SubElement(
                reference,
                "{http://www.w3.org/2000/09/xmldsig#}DigestValue"
            )
            digest_value.text = hash_b64
            
            # Placeholder signature value (non-empty Base64 string)
            sig_value = ET.SubElement(
                signature_elem,
                "{http://www.w3.org/2000/09/xmldsig#}SignatureValue"
            )
            # Use a deterministic placeholder based on XML hash (non-empty, consistent)
            placeholder_sig = base64.b64encode(b"SANDBOX_SIGNATURE_" + hash_bytes[:16]).decode("utf-8")
            sig_value.text = placeholder_sig
            
            root.append(signature_elem)
            
            return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
            
        except Exception as e:
            logger.error(f"Error applying fast placeholder signature: {e}")
            # Return original XML if signature insertion fails
            return xml_content
    
    def _apply_placeholder_signature(self, xml_content: str) -> str:
        """
        Applies placeholder signature to XML content for sandbox/testing.
        
        This generates a minimal XMLDSig structure without actual cryptographic signing.
        For production, proper RSA-SHA256 signing must be used.
        
        Args:
            xml_content: XML invoice to sign
            
        Returns:
            XML with placeholder signature structure
        """
        logger.warning("Using placeholder signature - not suitable for production")
        
        try:
            # Parse XML
            root = ET.fromstring(xml_content)
            
            # Create minimal signature element
            signature_elem = ET.Element(
                "{http://www.w3.org/2000/09/xmldsig#}Signature"
            )
            
            signed_info = ET.SubElement(
                signature_elem,
                "{http://www.w3.org/2000/09/xmldsig#}SignedInfo"
            )
            
            ET.SubElement(
                signed_info,
                "{http://www.w3.org/2000/09/xmldsig#}CanonicalizationMethod",
                attrib={"Algorithm": "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"}
            )
            
            ET.SubElement(
                signed_info,
                "{http://www.w3.org/2000/09/xmldsig#}SignatureMethod",
                attrib={"Algorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"}
            )
            
            reference = ET.SubElement(
                signed_info,
                "{http://www.w3.org/2000/09/xmldsig#}Reference",
                attrib={"URI": ""}
            )
            
            transforms = ET.SubElement(reference, "{http://www.w3.org/2000/09/xmldsig#}Transforms")
            ET.SubElement(
                transforms,
                "{http://www.w3.org/2000/09/xmldsig#}Transform",
                attrib={"Algorithm": "http://www.w3.org/2000/09/xmldsig#enveloped-signature"}
            )
            
            ET.SubElement(
                reference,
                "{http://www.w3.org/2000/09/xmldsig#}DigestMethod",
                attrib={"Algorithm": "http://www.w3.org/2001/04/xmlenc#sha256"}
            )
            
            # Use hash of canonicalized XML as placeholder
            canonical_xml = self._canonicalize_xml_for_signing(xml_content)
            hash_bytes = hashlib.sha256(canonical_xml.encode("utf-8")).digest()
            hash_b64 = base64.b64encode(hash_bytes).decode("utf-8")
            
            digest_value = ET.SubElement(
                reference,
                "{http://www.w3.org/2000/09/xmldsig#}DigestValue"
            )
            digest_value.text = hash_b64
            
            # Placeholder signature value (not cryptographically valid)
            sig_value = ET.SubElement(
                signature_elem,
                "{http://www.w3.org/2000/09/xmldsig#}SignatureValue"
            )
            sig_value.text = base64.b64encode(b"PLACEHOLDER_SIGNATURE").decode("utf-8")
            
            root.append(signature_elem)
            
            return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
            
        except Exception as e:
            logger.error(f"Error applying placeholder signature: {e}")
            # Return original XML if signature insertion fails
            return xml_content
    
    def _extract_signature_from_xml(self, signed_xml: str) -> str:
        """
        Extracts digital signature value from signed XML.
        
        Args:
            signed_xml: Signed XML content
            
        Returns:
            Base64-encoded signature value (non-empty)
        """
        try:
            root = ET.fromstring(signed_xml)
            
            # Find SignatureValue element
            for elem in root.iter():
                if elem.tag.endswith("SignatureValue") or "SignatureValue" in elem.tag:
                    if elem.text:
                        return elem.text.strip()
            
            # If not found, generate a placeholder signature based on XML hash
            canonical_xml = self._canonicalize_xml_for_signing(signed_xml)
            hash_bytes = hashlib.sha256(canonical_xml.encode("utf-8")).digest()
            # Use first 256 bits (32 bytes) as placeholder signature
            placeholder_sig = base64.b64encode(hash_bytes[:32]).decode("utf-8")
            logger.warning("SignatureValue not found in XML, using hash-based placeholder")
            return placeholder_sig
            
        except Exception as e:
            logger.error(f"Error extracting signature from XML: {e}")
            # Return a non-empty placeholder signature
            return base64.b64encode(b"PLACEHOLDER_SIGNATURE_FOR_ZATCA").decode("utf-8")
