"""
Tenant database model.

Defines the tenant entity for multi-tenant isolation.
Each tenant represents a company with its own environment and configuration.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.models import Base


class Tenant(Base):
    """
    Tenant database model.
    
    Represents a company/organization with its own:
    - VAT number
    - Environment (SANDBOX or PRODUCTION)
    - API keys
    - Certificates
    - Invoice logs
    """
    
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200), nullable=False, index=True)
    vat_number = Column(String(15), unique=True, nullable=False, index=True)
    environment = Column(String(20), nullable=False)  # SANDBOX or PRODUCTION
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    api_keys = relationship("ApiKey", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, company_name='{self.company_name}', vat_number='{self.vat_number}', environment='{self.environment}')>"

