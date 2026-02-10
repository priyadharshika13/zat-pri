"""
ZATCA service for CSR generation and ZATCA operations.

Handles Certificate Signing Request (CSR) generation for ZATCA CSID certificates.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from cryptography.x509.oid import NameOID
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

from app.schemas.auth import TenantContext
from app.core.constants import Environment

logger = logging.getLogger(__name__)


class ZatcaService:
    """
    Service for ZATCA-related operations including CSR generation.
    
    CRITICAL: All operations enforce tenant isolation.
    """
    
    def __init__(self, db: Session, tenant_context: TenantContext):
        """
        Initializes ZATCA service.
        
        Args:
            db: Database session
            tenant_context: Tenant context from request (enforces isolation)
        """
        self.db = db
        self.tenant_context = tenant_context
    
    def generate_csr(
        self,
        environment: Environment,
        common_name: str,
        organization: Optional[str] = None,
        organizational_unit: Optional[str] = None,
        country: Optional[str] = "SA",
        state: Optional[str] = None,
        locality: Optional[str] = None,
        email: Optional[str] = None
    ) -> dict:
        """
        Generates a Certificate Signing Request (CSR) for ZATCA CSID certificate.
        
        **Process:**
        1. Generates RSA key pair (2048 bits)
        2. Creates CSR with provided subject information
        3. Returns CSR content and private key
        
        **Security:**
        - Private key is returned only once (user must save it securely)
        - CSR can be submitted to ZATCA to obtain CSID certificate
        
        Args:
            environment: Target environment (SANDBOX or PRODUCTION)
            common_name: Common Name (CN) for the certificate (required)
            organization: Organization (O) - optional
            organizational_unit: Organizational Unit (OU) - optional
            country: Country code (default: SA)
            state: State or Province - optional
            locality: Locality or City - optional
            email: Email address - optional
            
        Returns:
            Dictionary containing:
            - csr: CSR content (PEM format)
            - private_key: Private key (PEM format)
            - subject: Subject information
            - key_size: Key size in bits
            
        Raises:
            ValueError: If cryptography library is not available or generation fails
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ValueError("cryptography library is required for CSR generation")
        
        try:
            # Generate RSA key pair (2048 bits - ZATCA requirement)
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Build subject name
            name_attributes = [
                x509.NameAttribute(NameOID.COUNTRY_NAME, country or "SA"),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name)
            ]
            
            if organization:
                name_attributes.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization))
            
            if organizational_unit:
                name_attributes.append(x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, organizational_unit))
            
            if state:
                name_attributes.append(x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state))
            
            if locality:
                name_attributes.append(x509.NameAttribute(NameOID.LOCALITY_NAME, locality))
            
            if email:
                name_attributes.append(x509.NameAttribute(NameOID.EMAIL_ADDRESS, email))
            
            subject = x509.Name(name_attributes)
            
            # Create CSR
            csr = x509.CertificateSigningRequestBuilder().subject_name(
                subject
            ).sign(private_key, hashes.SHA256())
            
            # Serialize CSR to PEM format
            csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode('utf-8')
            
            # Serialize private key to PEM format
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            # Build subject string for display
            subject_parts = []
            if country:
                subject_parts.append(f"C={country}")
            if state:
                subject_parts.append(f"ST={state}")
            if locality:
                subject_parts.append(f"L={locality}")
            if organization:
                subject_parts.append(f"O={organization}")
            if organizational_unit:
                subject_parts.append(f"OU={organizational_unit}")
            subject_parts.append(f"CN={common_name}")
            if email:
                subject_parts.append(f"emailAddress={email}")
            
            subject_string = ", ".join(subject_parts)
            
            logger.info(
                f"CSR generated successfully: tenant_id={self.tenant_context.tenant_id}, "
                f"environment={environment.value}, cn={common_name}"
            )
            
            return {
                "csr": csr_pem,
                "private_key": private_key_pem,
                "subject": subject_string,
                "key_size": 2048,
                "environment": environment.value,
                "common_name": common_name
            }
            
        except Exception as e:
            logger.error(f"CSR generation failed: {e}", exc_info=True)
            raise ValueError(f"Failed to generate CSR: {str(e)}")

