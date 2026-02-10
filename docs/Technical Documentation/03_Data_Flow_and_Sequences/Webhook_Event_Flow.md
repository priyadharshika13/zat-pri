# Webhook Event Flow

## Current Status

Webhook functionality is not currently implemented. This document describes the planned architecture for future implementation.

## Planned Architecture

### Event Types

**Invoice Events:**
- `invoice.created`: Invoice record created
- `invoice.processing`: Invoice processing started
- `invoice.cleared`: Invoice successfully cleared
- `invoice.rejected`: Invoice rejected by ZATCA or validation
- `invoice.failed`: Invoice processing failed
- `invoice.retry`: Invoice retry initiated

**Certificate Events:**
- `certificate.uploaded`: Certificate uploaded
- `certificate.activated`: Certificate activated
- `certificate.expiring`: Certificate expiring soon
- `certificate.expired`: Certificate expired

### Webhook Configuration

**Per-Tenant Configuration:**
- Webhook URL endpoint
- Secret key for signature verification
- Event subscriptions (which events to receive)
- Retry configuration

**Storage:**
- Webhook configurations stored in database
- Tenant-scoped (one configuration per tenant)
- Multiple webhook endpoints per tenant (future)

### Event Delivery

**Delivery Process:**
1. Event occurs in system
2. Webhook service checks tenant configuration
3. If webhook configured and event subscribed:
   - Create webhook delivery record
   - Queue webhook for delivery
   - Send HTTP POST to webhook URL
4. Wait for response
5. Update delivery record with status

**HTTP Request:**
- Method: POST
- Headers: Content-Type: application/json, X-Webhook-Signature
- Body: JSON event payload
- Timeout: Configurable (default: 30 seconds)

### Event Payload Structure

**Invoice Event Payload:**
```json
{
  "event_type": "invoice.cleared",
  "timestamp": "2024-01-15T10:30:00Z",
  "tenant_id": 123,
  "data": {
    "invoice_id": 456,
    "invoice_number": "INV-2024-001",
    "status": "CLEARED",
    "phase": "PHASE_2",
    "uuid": "invoice-uuid",
    "hash": "xml-hash"
  }
}
```

**Certificate Event Payload:**
```json
{
  "event_type": "certificate.expiring",
  "timestamp": "2024-01-15T10:30:00Z",
  "tenant_id": 123,
  "data": {
    "certificate_id": 789,
    "environment": "PRODUCTION",
    "expires_at": "2024-02-15T00:00:00Z",
    "days_until_expiry": 30
  }
}
```

### Signature Verification

**Purpose:** Verify webhook requests are from this system

**Algorithm:** HMAC-SHA256

**Header:** `X-Webhook-Signature`

**Format:** `sha256={signature}`

**Verification:**
1. Extract signature from header
2. Compute HMAC-SHA256 of payload with secret key
3. Compare signatures (constant-time comparison)
4. Reject if mismatch

### Retry Logic

**Retry Strategy:**
- Exponential backoff
- Maximum retries: 3 (configurable)
- Retry intervals: 1s, 5s, 30s

**Retry Conditions:**
- HTTP 5xx errors
- Network timeouts
- Connection errors

**No Retry:**
- HTTP 2xx responses (success)
- HTTP 4xx responses (client errors)

### Delivery Status

**Status Values:**
- `pending`: Queued for delivery
- `delivered`: Successfully delivered (HTTP 2xx)
- `failed`: Delivery failed (after all retries)
- `retrying`: Currently retrying

**Status Tracking:**
- Delivery records stored in database
- Status updated after each delivery attempt
- Full delivery history maintained

## Integration Points

### Invoice Service Integration

**Location:** `app/services/invoice_service.py`

**Integration Points:**
- After invoice creation: `invoice.created`
- After status update to PROCESSING: `invoice.processing`
- After status update to CLEARED: `invoice.cleared`
- After status update to REJECTED: `invoice.rejected`
- After status update to FAILED: `invoice.failed`
- After retry initiation: `invoice.retry`

**Implementation:**
- Webhook service called after status updates
- Non-blocking (async fire-and-forget)
- Errors logged but don't affect invoice processing

### Certificate Service Integration

**Location:** `app/services/certificate_service.py`

**Integration Points:**
- After certificate upload: `certificate.uploaded`
- After certificate activation: `certificate.activated`
- Certificate expiration check: `certificate.expiring`, `certificate.expired`

**Implementation:**
- Webhook service called after certificate operations
- Scheduled job for expiration checks
- Non-blocking delivery

## Database Schema (Planned)

### WebhookConfig Table

**Fields:**
- `id`: Primary key
- `tenant_id`: Foreign key to tenants
- `url`: Webhook endpoint URL
- `secret_key`: Secret for signature verification
- `events`: JSON array of subscribed events
- `is_active`: Boolean flag
- `created_at`: Timestamp
- `updated_at`: Timestamp

### WebhookDelivery Table

**Fields:**
- `id`: Primary key
- `webhook_config_id`: Foreign key to webhook_configs
- `event_type`: Event type string
- `payload`: JSON event payload
- `status`: Delivery status
- `response_code`: HTTP response code
- `response_body`: Response body (on error)
- `retry_count`: Number of retry attempts
- `delivered_at`: Timestamp of successful delivery
- `created_at`: Timestamp
- `updated_at`: Timestamp

## API Endpoints (Planned)

### Webhook Configuration

**POST** `/api/v1/webhooks`
- Create webhook configuration

**GET** `/api/v1/webhooks`
- List webhook configurations for tenant

**GET** `/api/v1/webhooks/{id}`
- Get webhook configuration details

**PUT** `/api/v1/webhooks/{id}`
- Update webhook configuration

**DELETE** `/api/v1/webhooks/{id}`
- Delete webhook configuration

### Webhook Delivery

**GET** `/api/v1/webhooks/{id}/deliveries`
- List webhook delivery history

**GET** `/api/v1/webhooks/{id}/deliveries/{delivery_id}`
- Get webhook delivery details

**POST** `/api/v1/webhooks/{id}/deliveries/{delivery_id}/retry`
- Manually retry failed delivery

## Security Considerations

**Authentication:**
- Webhook endpoints require API key
- Tenant isolation enforced
- Webhook configurations tenant-scoped

**Signature Verification:**
- HMAC-SHA256 signatures required
- Secret keys stored encrypted
- Signature verification mandatory

**Rate Limiting:**
- Webhook delivery rate limited
- Per-tenant delivery limits
- Prevents abuse

**Data Privacy:**
- Event payloads contain minimal data
- No sensitive data in webhook payloads
- PII excluded from events

## Current Implementation Status

Webhook functionality is not currently implemented. All components described above are planned for future implementation.

Future implementation considerations:

- Async webhook delivery queue
- Webhook delivery service
- Database schema for webhook configuration
- API endpoints for webhook management
- Signature verification library
- Retry mechanism with exponential backoff
- Delivery status tracking
- Webhook testing endpoint

