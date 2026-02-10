# Webhooks Module Documentation

## Overview

The Webhooks Module provides automatic event notifications to external client systems when important invoice events occur. Webhooks are delivered asynchronously after database transactions are committed, ensuring reliable delivery without blocking the invoice processing flow.

## Features

- **Event-Driven Notifications**: Automatic webhook delivery for invoice status changes
- **HMAC Signature Verification**: Secure webhook payloads with HMAC-SHA256 signatures
- **Retry Logic**: Automatic retries with exponential backoff (up to 3 attempts)
- **Tenant Isolation**: Complete tenant isolation for webhook configuration and delivery
- **Delivery Logging**: Comprehensive audit trail of all webhook delivery attempts
- **Non-Blocking**: Webhook failures never break invoice processing flow

## Supported Events

The following events trigger webhooks:

- `invoice.cleared` - Invoice successfully cleared by ZATCA
- `invoice.rejected` - Invoice rejected by ZATCA or validation
- `invoice.failed` - Invoice processing failed due to system error
- `invoice.retry_started` - Invoice retry processing started
- `invoice.retry_completed` - Invoice retry processing completed

## Webhook Payload Structure

All webhooks are sent as JSON with the following structure:

```json
{
  "event": "invoice.cleared",
  "timestamp": "2026-01-26T16:10:00Z",
  "data": {
    "invoice_id": 1,
    "invoice_number": "INV-2024-001234",
    "status": "CLEARED",
    "phase": "PHASE_2",
    "environment": "SANDBOX",
    "total_amount": 281.75,
    "vat_amount": 36.75,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "hash": "a1b2c3d4e5f6..."
  }
}
```

### Payload Fields

- `event` (string): Event type (e.g., "invoice.cleared")
- `timestamp` (string): ISO 8601 timestamp in UTC
- `data` (object): Event-specific data
  - `invoice_id` (integer): Internal invoice ID
  - `invoice_number` (string): Invoice number
  - `status` (string): Invoice status (CLEARED, REJECTED, FAILED)
  - `phase` (string): ZATCA phase (PHASE_1 or PHASE_2)
  - `environment` (string): Environment (SANDBOX or PRODUCTION)
  - `total_amount` (float): Total invoice amount including tax
  - `vat_amount` (float): VAT amount
  - `uuid` (string, optional): Invoice UUID from ZATCA (Phase-2 only)
  - `hash` (string, optional): XML hash value (Phase-2 only)

## Security: HMAC Signature Verification

All webhooks are signed using HMAC-SHA256 to ensure authenticity. The signature is sent in the `X-FATURAIX-Signature` header.

### Signature Format

- **Header Name**: `X-FATURAIX-Signature`
- **Algorithm**: HMAC-SHA256
- **Format**: Hex-encoded digest (64 characters)

### Verification Process

1. Extract the signature from the `X-FATURAIX-Signature` header
2. Compute HMAC-SHA256 of the request body using your webhook secret
3. Compare the computed signature with the received signature
4. If they match, the webhook is authentic

### Signature Verification Examples

#### Python

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload_body: str, signature: str, secret: str) -> bool:
    """
    Verify webhook signature.
    
    Args:
        payload_body: Raw request body (JSON string)
        signature: Signature from X-FATURAIX-Signature header
        secret: Webhook secret
        
    Returns:
        True if signature is valid, False otherwise
    """
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload_body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

# Example usage
payload = '{"event":"invoice.cleared","timestamp":"2026-01-26T16:10:00Z","data":{}}'
signature = request.headers.get('X-FATURAIX-Signature')
secret = 'your_webhook_secret'

if verify_webhook_signature(payload, signature, secret):
    # Process webhook
    data = json.loads(payload)
    print(f"Invoice {data['data']['invoice_id']} cleared")
else:
    # Reject webhook
    print("Invalid signature")
```

#### Node.js

```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payloadBody, signature, secret) {
  /**
   * Verify webhook signature.
   * 
   * @param {string} payloadBody - Raw request body (JSON string)
   * @param {string} signature - Signature from X-FATURAIX-Signature header
   * @param {string} secret - Webhook secret
   * @returns {boolean} True if signature is valid, False otherwise
   */
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payloadBody)
    .digest('hex');
  
  return crypto.timingSafeEqual(
    Buffer.from(expectedSignature),
    Buffer.from(signature)
  );
}

// Example usage
const payload = '{"event":"invoice.cleared","timestamp":"2026-01-26T16:10:00Z","data":{}}';
const signature = req.headers['x-faturaix-signature'];
const secret = 'your_webhook_secret';

if (verifyWebhookSignature(payload, signature, secret)) {
  // Process webhook
  const data = JSON.parse(payload);
  console.log(`Invoice ${data.data.invoice_id} cleared`);
} else {
  // Reject webhook
  console.log('Invalid signature');
}
```

## API Endpoints

### Register Webhook

**POST** `/api/v1/webhooks`

Register a new webhook for your tenant.

**Request Body:**
```json
{
  "url": "https://example.com/webhook",
  "events": ["invoice.cleared", "invoice.rejected"],
  "secret": "optional_custom_secret",
  "is_active": true
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "tenant_id": 1,
  "url": "https://example.com/webhook",
  "events": ["invoice.cleared", "invoice.rejected"],
  "is_active": true,
  "created_at": "2026-01-26T16:00:00Z",
  "updated_at": "2026-01-26T16:00:00Z",
  "last_triggered_at": null,
  "failure_count": 0
}
```

**Notes:**
- `secret` is optional - if not provided, a secure random secret will be auto-generated
- `events` must contain at least one event type
- `url` must be a valid HTTP/HTTPS URL

### List Webhooks

**GET** `/api/v1/webhooks`

List all webhooks for your tenant.

**Response:** `200 OK`
```json
{
  "webhooks": [
    {
      "id": 1,
      "url": "https://example.com/webhook",
      "events": ["invoice.cleared"],
      "is_active": true,
      "created_at": "2026-01-26T16:00:00Z",
      "updated_at": "2026-01-26T16:00:00Z",
      "last_triggered_at": "2026-01-26T16:10:00Z",
      "failure_count": 0
    }
  ],
  "total": 1,
  "active_count": 1,
  "inactive_count": 0
}
```

### Get Webhook

**GET** `/api/v1/webhooks/{id}`

Get a specific webhook by ID.

**Response:** `200 OK`
```json
{
  "id": 1,
  "url": "https://example.com/webhook",
  "events": ["invoice.cleared"],
  "is_active": true,
  "created_at": "2026-01-26T16:00:00Z",
  "updated_at": "2026-01-26T16:00:00Z",
  "last_triggered_at": "2026-01-26T16:10:00Z",
  "failure_count": 0
}
```

### Update Webhook

**PUT** `/api/v1/webhooks/{id}`

Update webhook configuration. All fields are optional - only provided fields will be updated.

**Request Body:**
```json
{
  "url": "https://updated.com/webhook",
  "events": ["invoice.cleared", "invoice.failed"],
  "secret": "new_secret",
  "is_active": false
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "url": "https://updated.com/webhook",
  "events": ["invoice.cleared", "invoice.failed"],
  "is_active": false,
  "created_at": "2026-01-26T16:00:00Z",
  "updated_at": "2026-01-26T16:20:00Z",
  "last_triggered_at": "2026-01-26T16:10:00Z",
  "failure_count": 0
}
```

### Delete Webhook

**DELETE** `/api/v1/webhooks/{id}`

Delete a webhook. This will also delete all associated delivery logs.

**Response:** `204 No Content`

### Get Webhook Logs

**GET** `/api/v1/webhooks/{id}/logs?limit=100`

Get delivery logs for a specific webhook.

**Query Parameters:**
- `limit` (optional): Maximum number of logs to return (default: 100)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "webhook_id": 1,
    "event": "invoice.cleared",
    "payload": {
      "event": "invoice.cleared",
      "timestamp": "2026-01-26T16:10:00Z",
      "data": {
        "invoice_id": 1,
        "invoice_number": "INV-2024-001234",
        "status": "CLEARED"
      }
    },
    "response_status": 200,
    "error_message": null,
    "created_at": "2026-01-26T16:10:00Z"
  }
]
```

## Delivery Logic

### Retry Mechanism

Webhooks are delivered with automatic retries:

- **Timeout**: 5 seconds per attempt
- **Max Retries**: 3 attempts
- **Backoff**: Exponential backoff (1s, 2s, 4s)

### Delivery Flow

1. Event occurs (e.g., invoice status changes to CLEARED)
2. Database transaction is committed
3. Webhook service finds all active webhooks subscribed to the event
4. For each webhook:
   - Payload is constructed
   - HMAC signature is generated
   - HTTP POST request is sent to webhook URL
   - If successful (2xx status), delivery is logged and webhook metrics updated
   - If failed, retry with exponential backoff (up to 3 attempts)
   - If all retries fail, failure is logged and webhook `failure_count` is incremented

### Failure Handling

- Webhook delivery failures are logged in `webhook_logs` table
- Webhook `failure_count` is incremented on failure
- Webhook failures **never** break invoice processing flow
- Failed webhooks remain active and will continue to receive events

## Best Practices

### Webhook Endpoint Implementation

1. **Verify Signature**: Always verify the `X-FATURAIX-Signature` header before processing
2. **Idempotency**: Design your endpoint to handle duplicate webhooks gracefully
3. **Fast Response**: Respond quickly (within 5 seconds) to avoid timeouts
4. **Error Handling**: Return appropriate HTTP status codes:
   - `200 OK` - Webhook processed successfully
   - `4xx` - Client error (will be retried)
   - `5xx` - Server error (will be retried)

### Security Recommendations

1. **Use HTTPS**: Always use HTTPS for webhook URLs
2. **Store Secret Securely**: Store webhook secrets securely (environment variables, secrets manager)
3. **Rotate Secrets**: Periodically rotate webhook secrets
4. **Validate Payload**: Validate webhook payload structure before processing
5. **Rate Limiting**: Implement rate limiting on your webhook endpoint

### Monitoring

1. **Monitor Logs**: Regularly check webhook delivery logs for failures
2. **Alert on Failures**: Set up alerts for consecutive webhook failures
3. **Track Metrics**: Monitor webhook `failure_count` and `last_triggered_at`
4. **Test Webhooks**: Use the webhook logs endpoint to verify delivery

## ZATCA Compliance Note

Webhooks are a convenience feature for external system integration and do not affect ZATCA compliance. All ZATCA processing and compliance requirements remain unchanged. Webhooks are delivered **after** database commits, ensuring that webhook delivery failures do not impact invoice processing or ZATCA submission.

## Example Integration

### Complete Webhook Handler (Python/Flask)

```python
from flask import Flask, request, jsonify
import hmac
import hashlib
import json

app = Flask(__name__)

WEBHOOK_SECRET = "your_webhook_secret"

def verify_signature(payload_body, signature):
    expected = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload_body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    # Get signature from header
    signature = request.headers.get('X-FATURAIX-Signature')
    if not signature:
        return jsonify({'error': 'Missing signature'}), 401
    
    # Get raw payload
    payload_body = request.data.decode('utf-8')
    
    # Verify signature
    if not verify_signature(payload_body, signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Parse payload
    try:
        payload = json.loads(payload_body)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    # Process webhook based on event type
    event = payload.get('event')
    data = payload.get('data', {})
    
    if event == 'invoice.cleared':
        invoice_id = data.get('invoice_id')
        invoice_number = data.get('invoice_number')
        print(f"Invoice {invoice_number} (ID: {invoice_id}) cleared")
        # Update your system...
        
    elif event == 'invoice.rejected':
        invoice_id = data.get('invoice_id')
        invoice_number = data.get('invoice_number')
        print(f"Invoice {invoice_number} (ID: {invoice_id}) rejected")
        # Handle rejection...
        
    elif event == 'invoice.failed':
        invoice_id = data.get('invoice_id')
        invoice_number = data.get('invoice_number')
        print(f"Invoice {invoice_number} (ID: {invoice_id}) failed")
        # Handle failure...
    
    # Return success
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(port=5000)
```

## Troubleshooting

### Webhook Not Received

1. **Check Webhook Status**: Verify webhook is active (`is_active: true`)
2. **Check Event Subscription**: Verify webhook is subscribed to the event
3. **Check Logs**: Review webhook delivery logs for errors
4. **Check URL**: Verify webhook URL is accessible and returns 2xx status
5. **Check Network**: Verify network connectivity and firewall rules

### Invalid Signature

1. **Verify Secret**: Ensure you're using the correct webhook secret
2. **Check Payload**: Ensure you're using the raw request body (not parsed JSON)
3. **Check Encoding**: Ensure payload is UTF-8 encoded
4. **Check Algorithm**: Ensure you're using HMAC-SHA256

### Delivery Failures

1. **Check Response Time**: Ensure your endpoint responds within 5 seconds
2. **Check Status Code**: Ensure your endpoint returns 2xx status codes
3. **Check Logs**: Review webhook logs for specific error messages
4. **Check Retries**: Review retry attempts in logs

## Database Schema

### webhooks Table

- `id` (integer, PK): Webhook ID
- `tenant_id` (integer, FK): Tenant ID (foreign key to tenants)
- `url` (string): Webhook URL endpoint
- `events` (JSON): Array of subscribed event types
- `secret` (string): HMAC secret for signature verification
- `is_active` (boolean): Whether webhook is active
- `created_at` (datetime): Creation timestamp
- `updated_at` (datetime): Last update timestamp
- `last_triggered_at` (datetime, nullable): Last trigger timestamp
- `failure_count` (integer): Number of consecutive failures

### webhook_logs Table

- `id` (integer, PK): Log entry ID
- `webhook_id` (integer, FK): Webhook ID (foreign key to webhooks)
- `event` (string): Event type that triggered the webhook
- `payload` (JSON): Webhook payload sent
- `response_status` (integer, nullable): HTTP response status code
- `error_message` (text, nullable): Error message if delivery failed
- `created_at` (datetime): Delivery attempt timestamp

## Migration

To apply the webhooks module database changes:

```bash
cd backend
alembic upgrade head
```

This will create the `webhooks` and `webhook_logs` tables.

## Support

For issues or questions about the webhooks module, please contact support or refer to the main API documentation.

