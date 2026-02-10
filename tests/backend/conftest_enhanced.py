"""
Enhanced test fixtures with async support and mocking.

Provides async test client, mocked external services, and comprehensive test data.
"""

import sys
from pathlib import Path

# Add backend directory to Python path so app imports work
backend_dir = Path(__file__).parent.parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.db.models import Base
from app.models.tenant import Tenant
from app.models.api_key import ApiKey
from app.models.subscription import Plan, Subscription, SubscriptionStatus
from app.models.invoice_log import InvoiceLog  # Import to ensure columns are registered
from app.core.constants import Environment

# Test database setup - engine is now created per-test in db_engine fixture


@pytest.fixture(scope="function")
def db_engine():
    """
    Function-scoped database engine.
    
    Creates a fresh SQLite in-memory database for each test.
    This ensures complete test isolation - no shared state between tests.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db(db_engine):
    """
    Function-scoped database session.
    
    Provides a fresh database session for each test using a fresh engine.
    """
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest_asyncio.fixture(scope="function")
async def async_client(db_engine):
    """Async test client with fresh database."""
    from app.db import session as db_session_module
    
    # Create sessionmaker for this engine
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine
    )
    
    def override_get_db():
        db_session = SessionLocal()
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[db_session_module.get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_tenant(db):
    """Test tenant fixture."""
    tenant = db.query(Tenant).filter(
        Tenant.vat_number == "123456789012345"
    ).first()
    if not tenant:
        tenant = Tenant(
            company_name="Test Company",
            vat_number="123456789012345",
            environment=Environment.SANDBOX.value,
            is_active=True
        )
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    return tenant


@pytest.fixture
def test_api_key(db, test_tenant):
    """Test API key fixture."""
    api_key = db.query(ApiKey).filter(
        ApiKey.api_key == "test-key"
    ).first()
    if not api_key:
        api_key = ApiKey(
            api_key="test-key",
            tenant_id=test_tenant.id,
            is_active=True
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
    return api_key


@pytest.fixture
def paid_plan(db):
    """Paid plan fixture (Starter plan with production access)."""
    plan = db.query(Plan).filter(Plan.name == "Starter").first()
    if not plan:
        plan = Plan(
            name="Starter",
            monthly_invoice_limit=500,
            monthly_ai_limit=100,
            rate_limit_per_minute=60,
            features={
                "phase1": True,
                "phase2": True,
                "ai_explanations": True,
                "production_access": True
            },
            is_active=True
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
    return plan


@pytest.fixture
def trial_plan(db):
    """Trial plan fixture (no production access)."""
    plan = db.query(Plan).filter(Plan.name == "Trial").first()
    if not plan:
        plan = Plan(
            name="Trial",
            monthly_invoice_limit=50,
            monthly_ai_limit=20,
            rate_limit_per_minute=30,
            features={
                "phase1": True,
                "phase2": True,
                "ai_explanations": True,
                "production_access": False
            },
            is_active=True
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
    return plan


@pytest.fixture
def test_subscription_trial(db, test_tenant, trial_plan):
    """Test subscription with Trial plan."""
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == test_tenant.id
    ).first()
    if subscription:
        subscription.plan_id = trial_plan.id
        subscription.status = SubscriptionStatus.TRIAL
    else:
        subscription = Subscription(
            tenant_id=test_tenant.id,
            plan_id=trial_plan.id,
            status=SubscriptionStatus.TRIAL,
            trial_starts_at=datetime.utcnow(),
            trial_ends_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@pytest.fixture
def test_subscription_paid(db, test_tenant, paid_plan):
    """Test subscription with paid plan."""
    subscription = db.query(Subscription).filter(
        Subscription.tenant_id == test_tenant.id
    ).first()
    if subscription:
        subscription.plan_id = paid_plan.id
        subscription.status = SubscriptionStatus.ACTIVE
    else:
        subscription = Subscription(
            tenant_id=test_tenant.id,
            plan_id=paid_plan.id,
            status=SubscriptionStatus.ACTIVE,
            started_at=datetime.utcnow()
        )
        db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@pytest.fixture
def headers(test_api_key):
    """Headers with test API key."""
    return {
        "X-API-Key": test_api_key.api_key,
        "Content-Type": "application/json"
    }


@pytest.fixture
def mock_zatca_client():
    """Mock ZATCA client for testing."""
    with patch('app.integrations.zatca.sandbox.ZATCASandboxClient') as mock, \
         patch('app.integrations.zatca.production.ZATCAProductionClient') as mock_prod:
        
        # Mock sandbox client
        mock_instance = AsyncMock()
        mock_instance.submit_for_clearance = AsyncMock(return_value={
            "status": "CLEARED",
            "uuid": "test-uuid-123",
            "qr_code": "test-qr-code",
            "reporting_status": "REPORTED"
        })
        mock.return_value = mock_instance
        
        # Mock production client
        mock_prod_instance = AsyncMock()
        mock_prod_instance.submit_for_clearance = AsyncMock(return_value={
            "status": "CLEARED",
            "uuid": "test-uuid-123",
            "qr_code": "test-qr-code",
            "reporting_status": "REPORTED"
        })
        mock_prod.return_value = mock_prod_instance
        
        yield {
            "sandbox": mock_instance,
            "production": mock_prod_instance
        }


@pytest.fixture
def mock_openrouter_service():
    """Mock OpenRouter service for testing."""
    with patch('app.services.ai.openrouter_service.get_openrouter_service') as mock:
        mock_instance = AsyncMock()
        mock_instance.call_openrouter = AsyncMock(return_value={
            "content": "Test AI response",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            },
            "model": "openai/gpt-4o-mini"
        })
        mock_instance.api_key = "test-openrouter-key"
        mock_instance.base_url = "https://openrouter.ai/api/v1"
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for external API calls."""
    with patch('httpx.AsyncClient') as mock:
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"status": "ok"})
        mock_response.text = "OK"
        mock_instance.head = AsyncMock(return_value=mock_response)
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_instance

