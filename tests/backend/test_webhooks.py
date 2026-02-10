"""
Unit tests for webhook functionality.

Tests webhook management, delivery, and integration with invoice processing:
- Webhook registration and CRUD operations
- Event filtering and subscription
- HMAC signature generation and validation
- Retry logic with exponential backoff
- Tenant isolation enforcement
- Failure logging
- Integration with invoice status changes
"""

import pytest
import hmac
import hashlib
import json
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
import httpx

from app.models.webhook import Webhook, WebhookLog
from app.models.invoice import Invoice, InvoiceStatus
from app.models.tenant import Tenant
from app.models.api_key import ApiKey
from app.schemas.webhook import WebhookCreateRequest, WebhookUpdateRequest, WebhookEvent
from app.schemas.auth import TenantContext
from app.services.webhook_service import WebhookService
from app.core.constants import Environment, InvoiceMode


@pytest.fixture
def mock_tenant_context():
    """Mock tenant context for testing."""
    return TenantContext(
        tenant_id=1,
        company_name="Test Company LLC",
        vat_number="300123456700003",
        environment=Environment.SANDBOX.value
    )


@pytest.fixture
def mock_other_tenant_context():
    """Mock different tenant context for cross-tenant tests."""
    return TenantContext(
        tenant_id=2,
        company_name="Other Company LLC",
        vat_number="300123456700004",
        environment=Environment.SANDBOX.value
    )


@pytest.fixture
def test_tenant(db: Session):
    """Create a test tenant."""
    tenant = Tenant(
        company_name="Test Company LLC",
        vat_number="300123456700003",
        environment=Environment.SANDBOX.value,
        is_active=True
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def test_api_key(db: Session, test_tenant: Tenant):
    """Create a test API key."""
    api_key = ApiKey(
        api_key="test_api_key_123",
        tenant_id=test_tenant.id,
        is_active=True
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


@pytest.fixture
def sample_webhook_request():
    """Sample webhook creation request."""
    return WebhookCreateRequest(
        url="https://example.com/webhook",
        events=[WebhookEvent.INVOICE_CLEARED, WebhookEvent.INVOICE_REJECTED],
        is_active=True
    )


class TestWebhookService:
    """Tests for WebhookService."""
    
    def test_create_webhook(self, db: Session, mock_tenant_context: TenantContext, sample_webhook_request: WebhookCreateRequest):
        """Test webhook creation."""
        service = WebhookService(db, mock_tenant_context)
        webhook = service.create_webhook(sample_webhook_request)
        
        assert webhook.id is not None
        assert webhook.tenant_id == mock_tenant_context.tenant_id
        assert webhook.url == sample_webhook_request.url
        assert webhook.is_active is True
        assert len(webhook.events) == 2
        assert "invoice.cleared" in webhook.events
        assert "invoice.rejected" in webhook.events
        assert webhook.secret is not None
        assert len(webhook.secret) == 64  # 32 bytes hex encoded
    
    def test_create_webhook_auto_generates_secret(self, db: Session, mock_tenant_context: TenantContext):
        """Test that secret is auto-generated if not provided."""
        request = WebhookCreateRequest(
            url="https://example.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        )
        service = WebhookService(db, mock_tenant_context)
        webhook = service.create_webhook(request)
        
        assert webhook.secret is not None
        assert len(webhook.secret) == 64
    
    def test_list_webhooks_tenant_isolation(self, db: Session, mock_tenant_context: TenantContext, mock_other_tenant_context: TenantContext):
        """Test that webhook listing respects tenant isolation."""
        # Create webhook for tenant 1
        service1 = WebhookService(db, mock_tenant_context)
        webhook1 = service1.create_webhook(WebhookCreateRequest(
            url="https://tenant1.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        # Create webhook for tenant 2
        service2 = WebhookService(db, mock_other_tenant_context)
        webhook2 = service2.create_webhook(WebhookCreateRequest(
            url="https://tenant2.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        # List webhooks for tenant 1
        webhooks = service1.list_webhooks()
        assert len(webhooks) == 1
        assert webhooks[0].id == webhook1.id
        assert webhooks[0].tenant_id == mock_tenant_context.tenant_id
    
    def test_get_webhook_tenant_isolation(self, db: Session, mock_tenant_context: TenantContext, mock_other_tenant_context: TenantContext):
        """Test that webhook retrieval respects tenant isolation."""
        # Create webhook for tenant 1
        service1 = WebhookService(db, mock_tenant_context)
        webhook1 = service1.create_webhook(WebhookCreateRequest(
            url="https://tenant1.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        # Try to get webhook from tenant 2's service
        service2 = WebhookService(db, mock_other_tenant_context)
        webhook = service2.get_webhook(webhook1.id)
        
        assert webhook is None  # Should not be accessible
    
    def test_update_webhook(self, db: Session, mock_tenant_context: TenantContext, sample_webhook_request: WebhookCreateRequest):
        """Test webhook update."""
        service = WebhookService(db, mock_tenant_context)
        webhook = service.create_webhook(sample_webhook_request)
        
        update_request = WebhookUpdateRequest(
            url="https://updated.com/webhook",
            is_active=False
        )
        updated = service.update_webhook(webhook.id, update_request)
        
        assert updated is not None
        assert updated.url == "https://updated.com/webhook"
        assert updated.is_active is False
        assert updated.events == webhook.events  # Events unchanged
    
    def test_delete_webhook(self, db: Session, mock_tenant_context: TenantContext, sample_webhook_request: WebhookCreateRequest):
        """Test webhook deletion."""
        service = WebhookService(db, mock_tenant_context)
        webhook = service.create_webhook(sample_webhook_request)
        
        deleted = service.delete_webhook(webhook.id)
        assert deleted is True
        
        # Verify webhook is deleted
        webhook_check = service.get_webhook(webhook.id)
        assert webhook_check is None
    
    def test_generate_signature(self, db: Session, mock_tenant_context: TenantContext):
        """Test HMAC signature generation."""
        service = WebhookService(db, mock_tenant_context)
        
        payload = '{"event":"invoice.cleared","timestamp":"2026-01-26T16:10:00Z","data":{}}'
        secret = "test_secret_123"
        
        signature = service._generate_signature(payload, secret)
        
        # Verify signature is hex-encoded
        assert len(signature) == 64  # SHA256 hex digest
        assert all(c in '0123456789abcdef' for c in signature)
        
        # Verify signature matches expected HMAC
        expected = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        assert signature == expected
    
    @pytest.mark.asyncio
    async def test_deliver_webhook_success(self, db: Session, mock_tenant_context: TenantContext):
        """Test successful webhook delivery."""
        service = WebhookService(db, mock_tenant_context)
        webhook = service.create_webhook(WebhookCreateRequest(
            url="https://example.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        with patch.object(service.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            success, status, error = await service._deliver_webhook(
                webhook,
                "invoice.cleared",
                {"invoice_id": 1, "status": "CLEARED"}
            )
            
            assert success is True
            assert status == 200
            assert error is None
            assert mock_post.called
            # Verify signature header
            call_args = mock_post.call_args
            assert "X-FATURAIX-Signature" in call_args.kwargs["headers"]
    
    @pytest.mark.asyncio
    async def test_deliver_webhook_retry(self, db: Session, mock_tenant_context: TenantContext):
        """Test webhook delivery with retries."""
        service = WebhookService(db, mock_tenant_context)
        webhook = service.create_webhook(WebhookCreateRequest(
            url="https://example.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        # Mock HTTP client to fail twice then succeed
        mock_responses = [
            MagicMock(status_code=500, text="Server Error"),
            MagicMock(status_code=500, text="Server Error"),
            MagicMock(status_code=200, text="OK")
        ]
        
        with patch.object(service.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = mock_responses
            
            success, status, error = await service._deliver_webhook(
                webhook,
                "invoice.cleared",
                {"invoice_id": 1, "status": "CLEARED"}
            )
            
            assert success is True
            assert status == 200
            assert mock_post.call_count == 3  # Retried 3 times
    
    @pytest.mark.asyncio
    async def test_deliver_webhook_timeout(self, db: Session, mock_tenant_context: TenantContext):
        """Test webhook delivery timeout handling."""
        service = WebhookService(db, mock_tenant_context)
        webhook = service.create_webhook(WebhookCreateRequest(
            url="https://example.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        # Mock timeout exception
        with patch.object(service.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timeout")
            
            success, status, error = await service._deliver_webhook(
                webhook,
                "invoice.cleared",
                {"invoice_id": 1, "status": "CLEARED"}
            )
            
            assert success is False
            assert status is None
            assert "timeout" in error.lower()
            assert mock_post.call_count == service.MAX_RETRIES
    
    @pytest.mark.asyncio
    async def test_trigger_webhook_event_filtering(self, db: Session, mock_tenant_context: TenantContext):
        """Test that webhooks are only triggered for subscribed events."""
        service = WebhookService(db, mock_tenant_context)
        
        # Create webhook subscribed to INVOICE_CLEARED only
        webhook = service.create_webhook(WebhookCreateRequest(
            url="https://example.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(service.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            # Trigger INVOICE_CLEARED event (should fire)
            await service.trigger_webhook(
                WebhookEvent.INVOICE_CLEARED,
                {"invoice_id": 1}
            )
            
            # Trigger INVOICE_REJECTED event (should NOT fire)
            await service.trigger_webhook(
                WebhookEvent.INVOICE_REJECTED,
                {"invoice_id": 1}
            )
            
            # Should only be called once (for INVOICE_CLEARED)
            assert mock_post.call_count == 1
    
    @pytest.mark.asyncio
    async def test_trigger_webhook_logs_delivery(self, db: Session, mock_tenant_context: TenantContext):
        """Test that webhook delivery is logged."""
        service = WebhookService(db, mock_tenant_context)
        webhook = service.create_webhook(WebhookCreateRequest(
            url="https://example.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(service.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            await service.trigger_webhook(
                WebhookEvent.INVOICE_CLEARED,
                {"invoice_id": 1, "status": "CLEARED"}
            )
            
            # Check that log was created
            logs = service.get_webhook_logs(webhook_id=webhook.id)
            assert len(logs) == 1
            assert logs[0].event == "invoice.cleared"
            assert logs[0].response_status == 200
            assert logs[0].error_message is None
    
    @pytest.mark.asyncio
    async def test_trigger_webhook_logs_failure(self, db: Session, mock_tenant_context: TenantContext):
        """Test that webhook delivery failures are logged."""
        service = WebhookService(db, mock_tenant_context)
        webhook = service.create_webhook(WebhookCreateRequest(
            url="https://example.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        # Mock HTTP client to fail
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch.object(service.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            await service.trigger_webhook(
                WebhookEvent.INVOICE_CLEARED,
                {"invoice_id": 1, "status": "CLEARED"}
            )
            
            # Check that log was created with error
            logs = service.get_webhook_logs(webhook_id=webhook.id)
            assert len(logs) == 1
            assert logs[0].response_status == 500
            assert logs[0].error_message is not None
    
    def test_get_webhook_logs_tenant_isolation(self, db: Session, mock_tenant_context: TenantContext, mock_other_tenant_context: TenantContext):
        """Test that webhook logs respect tenant isolation."""
        service1 = WebhookService(db, mock_tenant_context)
        webhook1 = service1.create_webhook(WebhookCreateRequest(
            url="https://tenant1.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        service2 = WebhookService(db, mock_other_tenant_context)
        webhook2 = service2.create_webhook(WebhookCreateRequest(
            url="https://tenant2.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        # Create logs for both webhooks
        service1._log_webhook_delivery(webhook1.id, "invoice.cleared", {}, 200, None)
        service2._log_webhook_delivery(webhook2.id, "invoice.cleared", {}, 200, None)
        
        # Tenant 1 should only see their logs
        logs1 = service1.get_webhook_logs()
        assert len(logs1) == 1
        assert logs1[0].webhook_id == webhook1.id


class TestWebhookAPI:
    """Tests for webhook API endpoints."""
    
    def test_create_webhook_endpoint(self, client: TestClient, test_api_key: ApiKey, db: Session):
        """Test POST /api/v1/webhooks endpoint."""
        # Ensure webhook models are registered
        from app.models.webhook import Webhook, WebhookLog
        from app.db.models import Base
        Base.metadata.create_all(bind=db.bind)
        
        response = client.post(
            "/api/v1/webhooks",
            json={
                "url": "https://example.com/webhook",
                "events": ["invoice.cleared", "invoice.rejected"],
                "is_active": True
            },
            headers={"X-API-Key": test_api_key.api_key}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["url"] == "https://example.com/webhook"
        assert len(data["events"]) == 2
        assert data["is_active"] is True
    
    def test_list_webhooks_endpoint(self, client: TestClient, test_api_key: ApiKey, db: Session, test_tenant: Tenant):
        """Test GET /api/v1/webhooks endpoint."""
        # Create a webhook first
        from app.services.webhook_service import WebhookService
        from app.schemas.auth import TenantContext
        tenant_context = TenantContext(
            tenant_id=test_tenant.id,
            company_name=test_tenant.company_name,
            vat_number=test_tenant.vat_number,
            environment=test_tenant.environment
        )
        service = WebhookService(db, tenant_context)
        service.create_webhook(WebhookCreateRequest(
            url="https://example.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        response = client.get(
            "/api/v1/webhooks",
            headers={"X-API-Key": test_api_key.api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["webhooks"]) == 1
    
    def test_update_webhook_endpoint(self, client: TestClient, test_api_key: ApiKey, db: Session, test_tenant: Tenant):
        """Test PUT /api/v1/webhooks/{id} endpoint."""
        # Create a webhook first
        from app.services.webhook_service import WebhookService
        from app.schemas.auth import TenantContext
        tenant_context = TenantContext(
            tenant_id=test_tenant.id,
            company_name=test_tenant.company_name,
            vat_number=test_tenant.vat_number,
            environment=test_tenant.environment
        )
        service = WebhookService(db, tenant_context)
        webhook = service.create_webhook(WebhookCreateRequest(
            url="https://example.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        response = client.put(
            f"/api/v1/webhooks/{webhook.id}",
            json={
                "url": "https://updated.com/webhook",
                "is_active": False
            },
            headers={"X-API-Key": test_api_key.api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://updated.com/webhook"
        assert data["is_active"] is False
    
    def test_delete_webhook_endpoint(self, client: TestClient, test_api_key: ApiKey, db: Session, test_tenant: Tenant):
        """Test DELETE /api/v1/webhooks/{id} endpoint."""
        # Create a webhook first
        from app.services.webhook_service import WebhookService
        from app.schemas.auth import TenantContext
        tenant_context = TenantContext(
            tenant_id=test_tenant.id,
            company_name=test_tenant.company_name,
            vat_number=test_tenant.vat_number,
            environment=test_tenant.environment
        )
        service = WebhookService(db, tenant_context)
        webhook = service.create_webhook(WebhookCreateRequest(
            url="https://example.com/webhook",
            events=[WebhookEvent.INVOICE_CLEARED]
        ))
        
        response = client.delete(
            f"/api/v1/webhooks/{webhook.id}",
            headers={"X-API-Key": test_api_key.api_key}
        )
        
        assert response.status_code == 204
        
        # Verify webhook is deleted
        response = client.get(
            f"/api/v1/webhooks/{webhook.id}",
            headers={"X-API-Key": test_api_key.api_key}
        )
        assert response.status_code == 404

