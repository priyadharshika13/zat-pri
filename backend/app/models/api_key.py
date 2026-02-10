"""
API Key database model.

Defines the API key entity linked to tenants.
Each API key belongs to exactly one tenant and provides access to that tenant's resources.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.models import Base


class ApiKey(Base):
    """
    API Key database model.
    
    Represents an API key that provides access to a specific tenant's resources.
    Each API key is unique and belongs to exactly one tenant.
    """
    
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(255), unique=True, nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")
    
    def __repr__(self):
        return f"<ApiKey(id={self.id}, api_key='{self.api_key[:10]}...', tenant_id={self.tenant_id}, is_active={self.is_active})>"

