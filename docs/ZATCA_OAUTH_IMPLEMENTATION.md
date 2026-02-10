# ZATCA OAuth Client-Credentials Flow Implementation

## Overview

This document describes the OAuth client-credentials flow implementation for ZATCA sandbox and production API authentication.

## Architecture

### Components

1. **OAuth Service** (`backend/app/integrations/zatca/oauth_service.py`)
   - Handles token generation, caching, and refresh
   - Thread-safe token caching with automatic expiry management
   - Singleton pattern per environment (SANDBOX/PRODUCTION)

2. **ZATCA Sandbox Client** (`backend/app/integrations/zatca/sandbox.py`)
   - Integrated OAuth authentication
   - Automatic token refresh on 401 errors
   - Real connectivity ping method

3. **Status Endpoint** (`backend/app/api/v1/routes/zatca.py`)
   - Real ZATCA connectivity verification
   - Certificate presence + OAuth connectivity check

## OAuth Flow

### 1. Token Generation

```
Client Request → OAuth Service
                ↓
         POST /oauth/token
         Headers:
           Authorization: Basic base64(client_id:client_secret)
           Content-Type: application/x-www-form-urlencoded
         Body:
           grant_type=client_credentials
                ↓
         ZATCA Response:
           {
             "access_token": "...",
             "token_type": "Bearer",
             "expires_in": 3600
           }
                ↓
         Cache Token (with 60s expiry buffer)
```

### 2. Token Usage

All ZATCA API requests include OAuth token:

```
POST /invoices/clearance
Headers:
  Authorization: Bearer <access_token>
  Content-Type: application/json
```

### 3. Token Refresh

- **Automatic**: Token refreshed when expired (checked before each request)
- **On 401**: Token refreshed and request retried once
- **Force Refresh**: `force_refresh=True` parameter available

## Configuration

### Environment Variables

```bash
# Sandbox OAuth Credentials
ZATCA_SANDBOX_CLIENT_ID=your_sandbox_client_id
ZATCA_SANDBOX_CLIENT_SECRET=your_sandbox_client_secret

# Production OAuth Credentials
ZATCA_PRODUCTION_CLIENT_ID=your_production_client_id
ZATCA_PRODUCTION_CLIENT_SECRET=your_production_client_secret

# OAuth Timeout (optional, default: 10.0 seconds)
ZATCA_OAUTH_TIMEOUT=10.0
```

### Config Class

OAuth settings are defined in `backend/app/core/config.py`:

```python
zatca_sandbox_client_id: Optional[str] = None
zatca_sandbox_client_secret: Optional[str] = None
zatca_production_client_id: Optional[str] = None
zatca_production_client_secret: Optional[str] = None
zatca_oauth_timeout: float = 10.0
```

## Usage

### Getting OAuth Token

```python
from app.integrations.zatca.oauth_service import get_oauth_service

# Get OAuth service for sandbox
oauth_service = get_oauth_service(environment="SANDBOX")

# Get access token (uses cache if valid)
token = await oauth_service.get_access_token()

# Force refresh
token = await oauth_service.get_access_token(force_refresh=True)
```

### Using in ZATCA Client

OAuth is automatically integrated into `ZATCASandboxClient`:

```python
from app.integrations.zatca.factory import get_zatca_client

client = get_zatca_client(environment="SANDBOX")

# OAuth token is automatically included in all requests
result = await client.submit_for_clearance(signed_xml, invoice_uuid)
```

### Checking Connectivity

```python
# Ping ZATCA sandbox to verify connectivity
result = await client.ping()

# Result:
# {
#   "connected": True,
#   "error_message": None,
#   "last_successful_ping": "2026-01-27T10:30:00"
# }
```

## Status Endpoint

The `/api/v1/zatca/status` endpoint now performs real connectivity checks:

```json
{
  "connected": true,
  "environment": "SANDBOX",
  "certificate": {...},
  "connectivity": {
    "has_certificate": true,
    "real_connectivity": true,
    "last_successful_ping": "2026-01-27T10:30:00",
    "error_message": null
  }
}
```

## Error Handling

### Invalid Credentials

```python
# Raises ValueError with clear message
ValueError: "Invalid ZATCA OAuth credentials for SANDBOX. 
Please verify ZATCA_SANDBOX_CLIENT_ID and ZATCA_SANDBOX_CLIENT_SECRET"
```

### Network Timeout

```python
# Raises ValueError
ValueError: "OAuth token request timed out for SANDBOX. 
Please check network connectivity and ZATCA service availability"
```

### 401 Unauthorized

- Automatically refreshes token
- Retries request once
- If still fails, returns error response

## Token Caching

- **In-Memory Cache**: Thread-safe singleton per environment
- **Expiry Buffer**: 60 seconds before actual expiry
- **Automatic Refresh**: Token refreshed when expired
- **Thread Safety**: Uses `asyncio.Lock` for refresh operations

## Testing

### Unit Tests

- `tests/backend/test_oauth.py`: OAuth service tests
  - Token generation
  - Token caching
  - Token expiry
  - 401 handling
  - Invalid credentials
  - Network timeout

### Integration Tests

- `tests/backend/test_sandbox_connectivity.py`: Connectivity tests
  - Ping success
  - Authentication failure
  - Timeout handling
  - Status endpoint integration

All tests use mocked HTTP responses - no real ZATCA API calls.

## Security Considerations

1. **Credentials Storage**: OAuth credentials stored in environment variables (never in code)
2. **Token Storage**: Tokens cached in memory only (not persisted)
3. **Token Expiry**: 60-second buffer prevents edge-case expiry
4. **Thread Safety**: All token operations are thread-safe
5. **Error Messages**: Clear but non-revealing error messages

## Production Deployment

### Required Steps

1. **Set Environment Variables**:
   ```bash
   export ZATCA_SANDBOX_CLIENT_ID="your_client_id"
   export ZATCA_SANDBOX_CLIENT_SECRET="your_client_secret"
   ```

2. **Verify Configuration**:
   ```bash
   # Check logs for OAuth service initialization
   # Should see: "Successfully fetched OAuth token for SANDBOX"
   ```

3. **Test Connectivity**:
   ```bash
   curl -H "X-API-Key: your_key" http://localhost:8000/api/v1/zatca/status
   # Should return: "connected": true, "real_connectivity": true
   ```

## Troubleshooting

### "OAuth credentials not configured"

**Solution**: Set `ZATCA_SANDBOX_CLIENT_ID` and `ZATCA_SANDBOX_CLIENT_SECRET` environment variables.

### "OAuth authentication failed (401)"

**Solution**: Verify client ID and secret are correct. Check ZATCA developer portal for credentials.

### "Connection timeout"

**Solution**: Check network connectivity to ZATCA sandbox. Verify firewall rules allow outbound HTTPS.

### Token not refreshing

**Solution**: Check logs for token expiry. Token should refresh automatically when expired.

## API Changes

### Breaking Changes

None - OAuth is additive and backward-compatible with existing certificate-based flow.

### New Features

- OAuth authentication for all ZATCA API calls
- Real connectivity verification in status endpoint
- Automatic token refresh on expiry or 401 errors

## Future Enhancements

1. **Redis Token Cache**: For multi-instance deployments
2. **Token Metrics**: Track token refresh frequency
3. **Production OAuth**: Full production environment support
4. **Token Rotation**: Proactive token refresh before expiry

