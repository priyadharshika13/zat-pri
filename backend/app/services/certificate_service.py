"""
Certificate management service.

Handles certificate upload, validation, storage, and metadata extraction.
Enforces tenant isolation and ensures only one active certificate per tenant/environment.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

from app.models.certificate import Certificate, CertificateStatus
from app.schemas.auth import TenantContext
from app.integrations.zatca.cert_manager import ensure_tenant_cert_directory, validate_tenant_cert_access
from app.core.constants import Environment

logger = logging.getLogger(__name__)


class CertificateService:
    """
    Service for managing tenant-scoped certificates.
    
    CRITICAL: All operations enforce tenant isolation.
    Files are stored in certs/tenant_{tenant_id}/{environment}/
    """
    
    def __init__(self, db: Session, tenant_context: TenantContext):
        """
        Initializes certificate service.
        
        Args:
            db: Database session
            tenant_context: Tenant context from request (enforces isolation)
        """
        self.db = db
        self.tenant_context = tenant_context
    
    def upload_certificate(
        self,
        certificate_content: bytes,
        private_key_content: bytes,
        environment: Environment
    ) -> Certificate:
        """
        Uploads and validates a certificate and private key.
        
        CRITICAL: 
        - Validates certificate format and expiry
        - Stores files securely in tenant-specific directory
        - Deactivates any existing active certificate for this tenant/environment
        - Extracts and stores certificate metadata in DB
        
        Args:
            certificate_content: PEM-encoded certificate content
            private_key_content: PEM-encoded private key content
            environment: Target environment (SANDBOX or PRODUCTION)
            
        Returns:
            Created Certificate instance
            
        Raises:
            ValueError: If certificate is invalid, expired, or format is incorrect
            HTTPException: If file operations fail
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ValueError("cryptography library is required for certificate management")
        
        # Validate and parse certificate
        try:
            cert_obj = x509.load_pem_x509_certificate(certificate_content, default_backend())
        except Exception as e:
            logger.error(f"Failed to parse certificate: {e}")
            raise ValueError(f"Invalid certificate format: {str(e)}")
        
        # Extract certificate metadata
        certificate_serial = str(cert_obj.serial_number)
        issuer = cert_obj.issuer.rfc4514_string()
        expiry_date = cert_obj.not_valid_after_utc
        
        # Validate certificate expiry
        if expiry_date < datetime.utcnow().replace(tzinfo=expiry_date.tzinfo):
            raise ValueError(f"Certificate has expired. Expiry date: {expiry_date}")
        
        # Validate private key format (basic check)
        try:
            # Try to parse as PEM
            if not private_key_content.startswith(b"-----BEGIN"):
                raise ValueError("Invalid private key format: must be PEM-encoded")
        except Exception as e:
            logger.error(f"Failed to validate private key: {e}")
            raise ValueError(f"Invalid private key format: {str(e)}")
        
        # CRITICAL: Cryptographic verification - ensure private key matches certificate public key
        self._verify_certificate_key_match(certificate_content, private_key_content)
        
        # Deactivate existing active certificates for this tenant/environment
        self._deactivate_existing_certificates(environment)
        
        # Ensure certificate directory exists
        cert_dir = ensure_tenant_cert_directory(self.tenant_context.tenant_id, environment.value)
        
        # Store certificate and private key files
        cert_path = cert_dir / "certificate.pem"
        key_path = cert_dir / "privatekey.pem"
        
        try:
            # Write certificate file (secure permissions: owner read/write only)
            cert_path.write_bytes(certificate_content)
            os.chmod(cert_path, 0o600)
            
            # Write private key file (secure permissions: owner read/write only)
            key_path.write_bytes(private_key_content)
            os.chmod(key_path, 0o600)
            
            logger.info(
                f"Certificate files stored: tenant_id={self.tenant_context.tenant_id}, "
                f"environment={environment.value}, cert_path={cert_path}, key_path={key_path}"
            )
        except Exception as e:
            logger.error(f"Failed to store certificate files: {e}")
            # Clean up on failure
            if cert_path.exists():
                cert_path.unlink()
            if key_path.exists():
                key_path.unlink()
            raise ValueError(f"Failed to store certificate files: {str(e)}")
        
        # Create certificate record in database
        certificate = Certificate(
            tenant_id=self.tenant_context.tenant_id,
            environment=environment.value,
            certificate_serial=certificate_serial,
            issuer=issuer,
            expiry_date=expiry_date,
            status=CertificateStatus.ACTIVE,
            is_active=True,
            uploaded_at=datetime.utcnow()
        )
        
        self.db.add(certificate)
        self.db.commit()
        self.db.refresh(certificate)
        
        logger.info(
            f"Certificate uploaded successfully: id={certificate.id}, "
            f"tenant_id={self.tenant_context.tenant_id}, environment={environment.value}, "
            f"serial={certificate_serial}, expiry={expiry_date}"
        )
        
        return certificate
    
    def get_certificate(self, environment: Optional[Environment] = None) -> Optional[Certificate]:
        """
        Gets the active certificate for the current tenant.
        
        CRITICAL: Automatically scoped to current tenant.
        
        Args:
            environment: Optional filter by environment (defaults to tenant's environment)
            
        Returns:
            Active Certificate or None
        """
        query = self.db.query(Certificate).filter(
            Certificate.tenant_id == self.tenant_context.tenant_id,
            Certificate.is_active == True
        )
        
        if environment:
            query = query.filter(Certificate.environment == environment.value)
        else:
            query = query.filter(Certificate.environment == self.tenant_context.environment)
        
        return query.order_by(Certificate.uploaded_at.desc()).first()
    
    def list_certificates(self, environment: Optional[Environment] = None) -> list[Certificate]:
        """
        Lists all certificates for the current tenant.
        
        CRITICAL: Automatically scoped to current tenant.
        
        Args:
            environment: Optional filter by environment
            
        Returns:
            List of Certificate instances (tenant-scoped)
        """
        query = self.db.query(Certificate).filter(
            Certificate.tenant_id == self.tenant_context.tenant_id
        )
        
        if environment:
            query = query.filter(Certificate.environment == environment.value)
        
        return query.order_by(Certificate.uploaded_at.desc()).all()
    
    def delete_certificate(self, certificate_id: int) -> bool:
        """
        Deletes a certificate and its associated files.
        
        CRITICAL: 
        - Only deletes certificates belonging to current tenant
        - Securely removes certificate and private key files
        - Removes database record
        
        Args:
            certificate_id: Certificate ID to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If certificate belongs to different tenant
        """
        certificate = self.db.query(Certificate).filter(
            Certificate.id == certificate_id,
            Certificate.tenant_id == self.tenant_context.tenant_id
        ).first()
        
        if not certificate:
            logger.warning(
                f"Certificate not found: id={certificate_id}, tenant_id={self.tenant_context.tenant_id}"
            )
            return False
        
        # Get certificate paths
        cert_dir = Path("certs") / f"tenant_{certificate.tenant_id}" / certificate.environment.lower()
        cert_path = cert_dir / "certificate.pem"
        key_path = cert_dir / "privatekey.pem"
        
        # Validate tenant access (security check)
        if not validate_tenant_cert_access(self.tenant_context.tenant_id, cert_path):
            raise ValueError("Certificate access validation failed")
        
        # Delete files securely
        try:
            if cert_path.exists():
                cert_path.unlink()
                logger.info(f"Deleted certificate file: {cert_path}")
            
            if key_path.exists():
                key_path.unlink()
                logger.info(f"Deleted private key file: {key_path}")
        except Exception as e:
            logger.error(f"Failed to delete certificate files: {e}")
            # Continue with DB deletion even if file deletion fails
        
        # Delete database record
        self.db.delete(certificate)
        self.db.commit()
        
        logger.info(
            f"Certificate deleted: id={certificate_id}, tenant_id={self.tenant_context.tenant_id}, "
            f"environment={certificate.environment}"
        )
        
        return True
    
    def _deactivate_existing_certificates(self, environment: Environment) -> None:
        """
        Deactivates all existing active certificates for the current tenant/environment.
        
        CRITICAL: Ensures only one active certificate per tenant/environment.
        
        Args:
            environment: Target environment
        """
        existing = self.db.query(Certificate).filter(
            Certificate.tenant_id == self.tenant_context.tenant_id,
            Certificate.environment == environment.value,
            Certificate.is_active == True
        ).all()
        
        for cert in existing:
            cert.is_active = False
            cert.status = CertificateStatus.REVOKED
            logger.info(
                f"Deactivated existing certificate: id={cert.id}, tenant_id={self.tenant_context.tenant_id}"
            )
        
        if existing:
            self.db.commit()
    
    def _verify_certificate_key_match(
        self,
        certificate_content: bytes,
        private_key_content: bytes
    ) -> None:
        """
        Cryptographically verifies that the private key matches the certificate public key.
        
        CRITICAL: This is a ZATCA compliance requirement. The system MUST reject
        certificate uploads if the private key does not match the certificate.
        
        Process:
        1. Extract public key from X.509 certificate
        2. Derive public key from private key
        3. Compare key parameters (RSA modulus and exponent)
        4. Raise ValueError if mismatch detected
        
        Args:
            certificate_content: PEM-encoded certificate content
            private_key_content: PEM-encoded private key content
            
        Raises:
            ValueError: If private key does not match certificate public key
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ValueError("cryptography library is required for certificate-key verification")
        
        try:
            # Step 1: Extract public key from certificate
            cert_obj = x509.load_pem_x509_certificate(certificate_content, default_backend())
            cert_public_key = cert_obj.public_key()
            
            # Step 2: Load private key and derive public key
            try:
                # Try PKCS8 format first (most common)
                private_key_obj = serialization.load_pem_private_key(
                    private_key_content,
                    password=None,
                    backend=default_backend()
                )
            except ValueError:
                # Try traditional OpenSSL format
                try:
                    private_key_obj = serialization.load_pem_private_key(
                        private_key_content,
                        password=None,
                        backend=default_backend()
                    )
                except Exception as e:
                    logger.error(f"Failed to parse private key: {e}")
                    raise ValueError(f"Invalid private key format: {str(e)}")
            
            key_public_key = private_key_obj.public_key()
            
            # Step 3: Compare public keys (RSA-specific comparison)
            # Extract RSA parameters from both keys
            # Both keys should be RSA keys (ZATCA requirement)
            try:
                cert_public_numbers = cert_public_key.public_numbers()
                key_public_numbers = key_public_key.public_numbers()
            except AttributeError:
                # Non-RSA keys are not supported by ZATCA
                raise ValueError(
                    "CERT_KEY_MISMATCH: Only RSA keys are supported for ZATCA certificates. "
                    "The certificate or private key is not an RSA key."
                )
            
            # Compare modulus and exponent (RSA key parameters)
            if cert_public_numbers.n != key_public_numbers.n:
                logger.error(
                    "Certificate-private key mismatch: RSA modulus does not match",
                    extra={
                        "cert_modulus_preview": str(cert_public_numbers.n)[:20] + "...",
                        "key_modulus_preview": str(key_public_numbers.n)[:20] + "..."
                    }
                )
                raise ValueError(
                    "CERT_KEY_MISMATCH: Private key does not match certificate public key. "
                    "The RSA modulus values differ. Please ensure the private key was generated "
                    "with the same key pair as the certificate."
                )
            
            if cert_public_numbers.e != key_public_numbers.e:
                logger.error(
                    "Certificate-private key mismatch: RSA exponent does not match",
                    extra={
                        "cert_exponent": cert_public_numbers.e,
                        "key_exponent": key_public_numbers.e
                    }
                )
                raise ValueError(
                    "CERT_KEY_MISMATCH: Private key does not match certificate public key. "
                    "The RSA exponent values differ. Please ensure the private key was generated "
                    "with the same key pair as the certificate."
                )
            
            # Keys match - verification successful
            logger.info(
                "Certificate-private key cryptographic verification passed",
                extra={
                    "certificate_serial": str(cert_obj.serial_number),
                    "key_type": type(private_key_obj).__name__
                }
            )
            
        except ValueError:
            # Re-raise ValueError as-is (already formatted)
            raise
        except Exception as e:
            logger.error(
                f"Failed to verify certificate-key match: {e}",
                exc_info=True
            )
            # If verification fails due to parsing errors, still reject
            raise ValueError(
                f"CERT_KEY_MISMATCH: Failed to verify certificate-private key match: {str(e)}. "
                f"Please ensure the private key corresponds to the certificate."
            ) from e

