"""
Certificate manager for tenant-scoped certificate isolation.

Enforces strict folder convention to prevent cross-tenant certificate access.
Each tenant has its own certificate directory structure.
"""

import logging
from pathlib import Path
from typing import Dict, Optional
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def get_tenant_cert_paths(tenant_id: int, environment: str) -> Dict[str, Path]:
    """
    Returns certificate paths for a specific tenant and environment.
    
    Folder convention:
    certs/
      tenant_<tenant_id>/
        sandbox/
          certificate.pem
          privatekey.pem
        production/
          certificate.pem
          privatekey.pem
    
    CRITICAL: This enforces tenant isolation - tenant A cannot access tenant B's certs.
    
    Args:
        tenant_id: Tenant ID
        environment: Environment (SANDBOX or PRODUCTION)
        
    Returns:
        Dictionary with 'cert_path' and 'key_path' keys
        
    Raises:
        HTTPException: If certificate files are missing
    """
    # Normalize environment
    env_lower = environment.lower()
    if env_lower not in ("sandbox", "production"):
        raise ValueError(f"Invalid environment: {environment}. Must be SANDBOX or PRODUCTION")
    
    # Build tenant-specific certificate directory
    base_dir = Path("certs")
    tenant_dir = base_dir / f"tenant_{tenant_id}" / env_lower
    
    cert_path = tenant_dir / "certificate.pem"
    key_path = tenant_dir / "privatekey.pem"
    
    # CRITICAL: Verify files exist before returning paths
    # 503 = signing service unavailable (audit requirement: correct semantics)
    if not cert_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Certificate not found for tenant {tenant_id} in {environment} environment. "
                   f"Expected path: {cert_path}"
        )
    
    if not key_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Private key not found for tenant {tenant_id} in {environment} environment. "
                   f"Expected path: {key_path}"
        )
    
    logger.debug(
        f"Resolved certificate paths for tenant {tenant_id}, environment {environment}: "
        f"cert={cert_path}, key={key_path}"
    )
    
    return {
        "cert_path": cert_path,
        "key_path": key_path
    }


def validate_tenant_cert_access(tenant_id: int, cert_path: Path) -> bool:
    """
    Validates that a certificate path belongs to the specified tenant.
    
    CRITICAL: Security check to prevent cross-tenant certificate access.
    
    Args:
        tenant_id: Expected tenant ID
        cert_path: Certificate path to validate
        
    Returns:
        True if path belongs to tenant, False otherwise
    """
    # Normalize path
    cert_path = Path(cert_path).resolve()
    
    # Check if path contains tenant_<tenant_id>
    expected_tenant_dir = f"tenant_{tenant_id}"
    if expected_tenant_dir not in str(cert_path):
        logger.warning(
            f"Certificate path validation failed: path {cert_path} does not contain {expected_tenant_dir}"
        )
        return False
    
    return True


def ensure_tenant_cert_directory(tenant_id: int, environment: str) -> Path:
    """
    Ensures tenant certificate directory exists (creates if needed).
    
    Args:
        tenant_id: Tenant ID
        environment: Environment (SANDBOX or PRODUCTION)
        
    Returns:
        Path to tenant certificate directory
    """
    env_lower = environment.lower()
    base_dir = Path("certs")
    tenant_dir = base_dir / f"tenant_{tenant_id}" / env_lower
    
    tenant_dir.mkdir(parents=True, exist_ok=True)
    
    logger.debug(f"Ensured certificate directory exists: {tenant_dir}")
    
    return tenant_dir

