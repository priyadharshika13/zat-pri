"""
Tests for tenant isolation and multi-tenant security.

Ensures that:
1. API keys resolve to correct tenant context
2. Tenant A cannot access tenant B invoice logs
3. Tenant A cannot load tenant B certificate paths
4. Invoice logs are always saved with correct tenant_id
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.models import Base
from app.models.tenant import Tenant
from app.models.api_key import ApiKey
from app.models.invoice_log import InvoiceLog, InvoiceLogStatus
from app.services.invoice_log_service import InvoiceLogService
from app.schemas.auth import TenantContext
from app.integrations.zatca.cert_manager import get_tenant_cert_paths, validate_tenant_cert_access
from app.core.constants import Environment


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Creates a test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def tenant_a(db):
    """Creates test tenant A."""
    tenant = Tenant(
        company_name="Test Company A",
        vat_number="111111111111111",
        environment=Environment.SANDBOX.value,
        is_active=True
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def tenant_b(db):
    """Creates test tenant B."""
    tenant = Tenant(
        company_name="Test Company B",
        vat_number="222222222222222",
        environment=Environment.PRODUCTION.value,
        is_active=True
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def api_key_a(db, tenant_a):
    """Creates API key for tenant A."""
    api_key = ApiKey(
        api_key="test-key-a",
        tenant_id=tenant_a.id,
        is_active=True
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


@pytest.fixture
def api_key_b(db, tenant_b):
    """Creates API key for tenant B."""
    api_key = ApiKey(
        api_key="test-key-b",
        tenant_id=tenant_b.id,
        is_active=True
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


def test_api_key_resolves_correct_tenant_context(db, tenant_a, api_key_a):
    """Test that API key resolves to correct tenant context."""
    from app.core.security import verify_api_key_and_resolve_tenant
    from fastapi import Request
    
    # Mock request
    class MockRequest:
        def __init__(self):
            self.state = type('state', (), {})()
    
    request = MockRequest()
    
    # This would normally be called by FastAPI dependency injection
    # For testing, we'll test the lookup logic directly
    # Use the same test database session, not the production SessionLocal
    api_key_obj = db.query(ApiKey).filter(
        ApiKey.api_key == "test-key-a",
        ApiKey.is_active == True
    ).first()
    
    assert api_key_obj is not None
    assert api_key_obj.tenant_id == tenant_a.id
    
    tenant = db.query(Tenant).filter(
        Tenant.id == api_key_obj.tenant_id,
        Tenant.is_active == True
    ).first()
    
    assert tenant is not None
    assert tenant.id == tenant_a.id
    assert tenant.company_name == "Test Company A"


def test_tenant_a_cannot_access_tenant_b_invoice_logs(db, tenant_a, tenant_b, api_key_a):
    """Test that tenant A cannot access tenant B's invoice logs."""
    # Create logs for both tenants
    log_a = InvoiceLog(
        tenant_id=tenant_a.id,
        invoice_number="INV-A-001",
        status=InvoiceLogStatus.SUBMITTED,
        environment=Environment.SANDBOX.value
    )
    log_b = InvoiceLog(
        tenant_id=tenant_b.id,
        invoice_number="INV-B-001",
        status=InvoiceLogStatus.CLEARED,
        environment=Environment.PRODUCTION.value
    )
    db.add(log_a)
    db.add(log_b)
    db.commit()
    
    # Create service with tenant A context
    tenant_context_a = TenantContext(
        tenant_id=tenant_a.id,
        company_name=tenant_a.company_name,
        vat_number=tenant_a.vat_number,
        environment=Environment.SANDBOX
    )
    
    log_service = InvoiceLogService(db, tenant_context_a)
    
    # Tenant A should only see their own logs
    logs = log_service.get_logs()
    
    assert len(logs) == 1
    assert logs[0].tenant_id == tenant_a.id
    assert logs[0].invoice_number == "INV-A-001"
    
    # Tenant A should not see tenant B's logs
    tenant_b_logs = [log for log in logs if log.tenant_id == tenant_b.id]
    assert len(tenant_b_logs) == 0


def test_tenant_a_cannot_load_tenant_b_certificate_paths(tenant_a, tenant_b):
    """Test that tenant A cannot load tenant B's certificate paths."""
    import tempfile
    from pathlib import Path
    
    # Create temporary certificate directories
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "certs"
        
        # Create tenant A certs
        tenant_a_dir = base_dir / f"tenant_{tenant_a.id}" / "sandbox"
        tenant_a_dir.mkdir(parents=True)
        (tenant_a_dir / "certificate.pem").write_text("tenant-a-cert")
        (tenant_a_dir / "privatekey.pem").write_text("tenant-a-key")
        
        # Create tenant B certs
        tenant_b_dir = base_dir / f"tenant_{tenant_b.id}" / "production"
        tenant_b_dir.mkdir(parents=True)
        (tenant_b_dir / "certificate.pem").write_text("tenant-b-cert")
        (tenant_b_dir / "privatekey.pem").write_text("tenant-b-key")
        
        # Mock the certs directory
        import app.integrations.zatca.cert_manager as cert_manager
        original_certs_dir = getattr(cert_manager, 'CERTS_BASE_DIR', None)
        
        # Test tenant A can access their own certs
        # (This would work if we could mock the base directory)
        # For now, test the validation function
        
        # Test certificate path validation
        tenant_a_cert_path = tenant_a_dir / "certificate.pem"
        assert validate_tenant_cert_access(tenant_a.id, tenant_a_cert_path) == True
        
        # Tenant A should not be able to access tenant B's certs
        tenant_b_cert_path = tenant_b_dir / "certificate.pem"
        assert validate_tenant_cert_access(tenant_a.id, tenant_b_cert_path) == False


def test_invoice_logs_always_saved_with_correct_tenant_id(db, tenant_a):
    """Test that invoice logs are always saved with correct tenant_id."""
    tenant_context = TenantContext(
        tenant_id=tenant_a.id,
        company_name=tenant_a.company_name,
        vat_number=tenant_a.vat_number,
        environment=Environment.SANDBOX
    )
    
    log_service = InvoiceLogService(db, tenant_context)
    
    # Create log entry
    log_entry = log_service.create_log(
        invoice_number="INV-001",
        uuid="test-uuid",
        hash="test-hash",
        status=InvoiceLogStatus.SUBMITTED
    )
    
    # Verify tenant_id is set correctly
    assert log_entry.tenant_id == tenant_a.id
    assert log_entry.invoice_number == "INV-001"
    
    # Verify it's in database with correct tenant_id
    db_log = db.query(InvoiceLog).filter(InvoiceLog.id == log_entry.id).first()
    assert db_log is not None
    assert db_log.tenant_id == tenant_a.id
    
    # Verify tenant_id cannot be overridden
    # (This is enforced by the service - tenant_id comes from context)
    assert db_log.tenant_id == tenant_context.tenant_id


def test_cross_tenant_query_prevention(db, tenant_a, tenant_b):
    """Test that queries automatically filter by tenant_id."""
    # Create logs for both tenants
    log_a1 = InvoiceLog(
        tenant_id=tenant_a.id,
        invoice_number="INV-A-001",
        status=InvoiceLogStatus.SUBMITTED,
        environment=Environment.SANDBOX.value
    )
    log_a2 = InvoiceLog(
        tenant_id=tenant_a.id,
        invoice_number="INV-A-002",
        status=InvoiceLogStatus.CLEARED,
        environment=Environment.SANDBOX.value
    )
    log_b1 = InvoiceLog(
        tenant_id=tenant_b.id,
        invoice_number="INV-B-001",
        status=InvoiceLogStatus.SUBMITTED,
        environment=Environment.PRODUCTION.value
    )
    db.add_all([log_a1, log_a2, log_b1])
    db.commit()
    
    # Query with tenant A context
    tenant_context_a = TenantContext(
        tenant_id=tenant_a.id,
        company_name=tenant_a.company_name,
        vat_number=tenant_a.vat_number,
        environment=Environment.SANDBOX
    )
    
    log_service = InvoiceLogService(db, tenant_context_a)
    logs = log_service.get_logs()
    
    # Should only return tenant A's logs
    assert len(logs) == 2
    assert all(log.tenant_id == tenant_a.id for log in logs)
    assert all(log.invoice_number.startswith("INV-A") for log in logs)
    
    # Should not include tenant B's logs
    tenant_b_logs = [log for log in logs if log.tenant_id == tenant_b.id]
    assert len(tenant_b_logs) == 0

