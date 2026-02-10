"""
Certificate database model.

Defines the certificate entity for tenant-scoped certificate management.
Each certificate belongs to exactly one tenant and environment.
"""

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.models import Base


class CertificateStatus(str, enum.Enum):
    """Certificate status values."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class Certificate(Base):
    """
    Certificate database model.
    
    Stores certificate metadata (not raw certificate/key data).
    Files are stored securely on filesystem in certs/tenant_{tenant_id}/.
    
    CRITICAL: Only one active certificate per tenant per environment.
    """
    
    __tablename__ = "certificates"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    environment = Column(String(20), nullable=False, index=True)  # SANDBOX or PRODUCTION
    
    # Certificate metadata (extracted from certificate file)
    certificate_serial = Column(String(100), nullable=True, index=True)
    issuer = Column(String(200), nullable=True)
    expiry_date = Column(DateTime, nullable=True, index=True)
    
    # Status and lifecycle
    status = Column(SQLEnum(CertificateStatus), nullable=False, default=CertificateStatus.ACTIVE, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", backref="certificates")
    
    def __repr__(self):
        return f"<Certificate(id={self.id}, tenant_id={self.tenant_id}, environment='{self.environment}', status='{self.status.value}', expiry_date={self.expiry_date})>"

