# ZATCA Compliance CSID API Implementation

## Overview

This document describes the automated ZATCA Compliance CSID API integration for certificate onboarding. This implementation eliminates the need for manual ZATCA Developer Portal steps by directly submitting CSRs to ZATCA and automatically storing received certificates.

## Architecture

### Components

1. **Compliance CSID Service** (`backend/app/integrations/zatca/compliance_csid.py`)
   - Handles CSR submission to ZATCA Compliance CSID API
   - OAuth authentication integration
   - Error handling and retry logic
   - Certificate response parsing

2. **API Endpoint** (`backend/app/api/v1/routes/zatca.py`)
   - `POST /api/v1/zatca/compliance/csid/submit`
   - Validates input (CSR + private key)
   - Calls Compliance CSID service
   - Automatically stores certificate using `CertificateService`
   - Returns certificate metadata

3. **Certificate Service** (Existing)
   - Stores certificate and private key securely
   - Extracts certificate metadata
   - Manages tenant isolation

## Automated Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ Automated Certificate Onboarding Flow                      │
└─────────────────────────────────────────────────────────────┘

Step 1: Generate CSR ✅
  POST /api/v1/zatca/csr/generate
  → Returns: CSR (PEM) + Private Key (PEM)

Step 2: Submit to ZATCA Compliance CSID API ✅ (NEW)
  POST /api/v1/zatca/compliance/csid/submit
  → System calls ZATCA Compliance CSID API
  → System receives certificate + secret

Step 3: Automatic Certificate Storage ✅ (AUTOMATED)
  → System validates certificate
  → System stores certificate automatically
  → Returns certificate metadata

Step 4: Ready for Use ✅
  → Certificate available for invoice signing
  → Can be used in Reporting & Clearance APIs
```

## API Endpoint

### Submit CSR to Compliance CSID

**Endpoint:** `POST /api/v1/zatca/compliance/csid/submit`

**Authentication:** API Key (X-API-Key header)

**Request Format:**
```http
POST /api/v1/zatca/compliance/csid/submit
Content-Type: multipart/form-data
X-API-Key: your-api-key

Form Data:
  csr: "-----BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----"
  private_key: "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
  environment: "SANDBOX"
```

**Request Parameters:**
- `csr` (required): Certificate Signing Request in PEM format
- `private_key` (required): Private key in PEM format (from CSR generation)
- `environment` (optional): Target environment, defaults to "SANDBOX"

**Example Request (cURL):**
```bash
curl -X POST \
  -H "X-API-Key: your-api-key" \
  -F "csr=-----BEGIN CERTIFICATE REQUEST-----
MIIB...
-----END CERTIFICATE REQUEST-----" \
  -F "private_key=-----BEGIN PRIVATE KEY-----
MIIE...
-----END PRIVATE KEY-----" \
  -F "environment=SANDBOX" \
  http://localhost:8000/api/v1/zatca/compliance/csid/submit
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "CSR submitted successfully and certificate stored",
  "zatca_response": {
    "requestID": "12345678-1234-1234-1234-123456789012",
    "dispositionMessage": "Certificate issued successfully",
    "has_secret": true
  },
  "certificate": {
    "id": 1,
    "serial": "12345678901234567890",
    "issuer": "CN=ZATCA Sandbox CA, O=ZATCA, C=SA",
    "expiry_date": "2025-12-31T23:59:59",
    "uploaded_at": "2024-01-27T10:30:00",
    "environment": "SANDBOX",
    "status": "ACTIVE",
    "is_active": true
  },
  "note": "Certificate is now ready for use in Reporting and Clearance APIs"
}
```

**Error Responses:**

**400 Bad Request** - Invalid CSR or private key format:
```json
{
  "detail": "Invalid CSR format: must be PEM format starting with -----BEGIN CERTIFICATE REQUEST-----"
}
```

**401 Unauthorized** - OAuth authentication failed:
```json
{
  "detail": "ZATCA OAuth authentication failed: Invalid ZATCA OAuth credentials for SANDBOX"
}
```

**409 Conflict** - CSR already submitted:
```json
{
  "detail": "CSR submission conflict. This CSR may have already been submitted. ZATCA error: Duplicate request"
}
```

**502 Bad Gateway** - ZATCA server error:
```json
{
  "detail": "ZATCA server error. Please try again later. Error: Internal server error"
}
```

## ZATCA API Integration Details

### Endpoint
- **URL:** `{base_url}/compliance/csid`
- **Base URL (Sandbox):** `https://gw-apic-gov.gazt.gov.sa/e-invoicing/developer-portal`
- **Method:** POST
- **Content-Type:** application/json

### Request Format
```json
{
  "csr": "-----BEGIN CERTIFICATE REQUEST-----\nMIIB...\n-----END CERTIFICATE REQUEST-----"
}
```

### Response Format
```json
{
  "requestID": "12345678-1234-1234-1234-123456789012",
  "dispositionMessage": "Certificate issued successfully",
  "secret": "base64-encoded-secret",
  "binarySecurityToken": "-----BEGIN CERTIFICATE-----\nMIIE...\n-----END CERTIFICATE-----"
}
```

### Headers
- `Authorization: Bearer <oauth_token>` - OAuth token (automatic)
- `Content-Type: application/json`
- `Accept: application/json`

## Error Handling

### HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Certificate stored and ready |
| 400 | Invalid request | Check CSR/private key format |
| 401 | OAuth failed | Verify OAuth credentials |
| 409 | Conflict | CSR already submitted |
| 500 | Server error | Retry later |
| 502 | ZATCA error | Check ZATCA service status |

### Error Handling Strategy

1. **OAuth 401 Errors:**
   - Automatic token refresh
   - Single retry with refreshed token
   - If still fails, return 401 to client

2. **ZATCA API Errors:**
   - 400: Invalid CSR format → Return 400 to client
   - 409: Duplicate CSR → Return 409 to client
   - 500: ZATCA server error → Return 502 to client

3. **Network Errors:**
   - Timeout: 30 seconds
   - Connection errors: Return 502

## Configuration

### Required Environment Variables

```bash
# Sandbox OAuth Credentials (Required)
ZATCA_SANDBOX_CLIENT_ID=your_sandbox_client_id
ZATCA_SANDBOX_CLIENT_SECRET=your_sandbox_client_secret

# Sandbox Base URL (Default, can be overridden)
ZATCA_SANDBOX_BASE_URL=https://gw-apic-gov.gazt.gov.sa/e-invoicing/developer-portal

# OAuth Timeout (Optional, default: 10.0 seconds)
ZATCA_OAUTH_TIMEOUT=10.0
```

### Configuration in Code

```python
# backend/app/core/config.py
zatca_sandbox_base_url: str = "https://gw-apic-gov.gazt.gov.sa/e-invoicing/developer-portal"
zatca_sandbox_client_id: Optional[str] = None
zatca_sandbox_client_secret: Optional[str] = None
zatca_oauth_timeout: float = 10.0
```

## Usage Examples

### Python Client Example

```python
import requests

# Step 1: Generate CSR
csr_response = requests.post(
    "http://localhost:8000/api/v1/zatca/csr/generate",
    headers={"X-API-Key": "your-api-key"},
    data={
        "environment": "SANDBOX",
        "common_name": "test-company.com",
        "organization": "Test Company",
        "country": "SA"
    }
)
csr_data = csr_response.json()
csr = csr_data["csr"]
private_key = csr_data["private_key"]

# Step 2: Submit to Compliance CSID API
submit_response = requests.post(
    "http://localhost:8000/api/v1/zatca/compliance/csid/submit",
    headers={"X-API-Key": "your-api-key"},
    data={
        "csr": csr,
        "private_key": private_key,
        "environment": "SANDBOX"
    }
)
result = submit_response.json()

print(f"Certificate ID: {result['certificate']['id']}")
print(f"Certificate Serial: {result['certificate']['serial']}")
print(f"ZATCA Request ID: {result['zatca_response']['requestID']}")
```

### JavaScript/TypeScript Example

```typescript
// Step 1: Generate CSR
const csrResponse = await fetch('http://localhost:8000/api/v1/zatca/csr/generate', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key'
  },
  body: new FormData([
    ['environment', 'SANDBOX'],
    ['common_name', 'test-company.com'],
    ['organization', 'Test Company'],
    ['country', 'SA']
  ])
});
const csrData = await csrResponse.json();

// Step 2: Submit to Compliance CSID API
const submitResponse = await fetch('http://localhost:8000/api/v1/zatca/compliance/csid/submit', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key'
  },
  body: new FormData([
    ['csr', csrData.csr],
    ['private_key', csrData.private_key],
    ['environment', 'SANDBOX']
  ])
});
const result = await submitResponse.json();

console.log(`Certificate ID: ${result.certificate.id}`);
console.log(`ZATCA Request ID: ${result.zatca_response.requestID}`);
```

## Certificate Usage in Reporting & Clearance APIs

### How the Certificate is Used

Once the certificate is stored via Compliance CSID API, it is automatically available for:

1. **Invoice Signing:**
   - Certificate is used to cryptographically sign invoices
   - Private key is used for XML signature generation
   - Certificate metadata is included in signed XML

2. **Clearance API:**
   - Certificate is embedded in signed invoice XML
   - ZATCA validates certificate during clearance
   - Certificate must be valid and not expired

3. **Reporting API:**
   - Certificate is used for authenticated reporting requests
   - OAuth token + certificate provide dual authentication
   - Certificate serial is tracked in reporting logs

### Certificate Selection

The system automatically selects the active certificate for the tenant/environment:

```python
# Certificate is automatically retrieved by environment
cert_service = CertificateService(db, tenant)
certificate = cert_service.get_certificate(environment=Environment.SANDBOX)

# Certificate files are stored at:
# certs/tenant_{tenant_id}/sandbox/certificate.pem
# certs/tenant_{tenant_id}/sandbox/privatekey.pem
```

### Certificate Lifecycle

1. **Generation:** CSR + Private Key generated
2. **Submission:** CSR submitted to ZATCA Compliance CSID API
3. **Storage:** Certificate + Private Key stored automatically
4. **Activation:** Certificate marked as ACTIVE
5. **Usage:** Certificate used for signing and API calls
6. **Expiry:** Certificate expires (system should warn before expiry)

## Security Considerations

1. **Private Key Handling:**
   - Private key is only transmitted during CSR submission
   - Private key is stored with 600 permissions (owner read/write only)
   - Private key is never logged or exposed in responses

2. **OAuth Token:**
   - OAuth tokens are cached securely
   - Tokens automatically refresh on expiry
   - Token refresh on 401 errors

3. **Tenant Isolation:**
   - Certificates are stored in tenant-specific directories
   - Database records enforce tenant isolation
   - API endpoints validate tenant context

4. **Certificate Validation:**
   - Certificate format validation
   - Certificate expiry check
   - Certificate-key matching (recommended enhancement)

## Troubleshooting

### "OAuth authentication failed"
**Solution:** Verify `ZATCA_SANDBOX_CLIENT_ID` and `ZATCA_SANDBOX_CLIENT_SECRET` are set correctly.

### "Invalid CSR format"
**Solution:** Ensure CSR is in PEM format with proper headers/footers.

### "CSR submission conflict (409)"
**Solution:** This CSR has already been submitted. Generate a new CSR.

### "ZATCA server error (500/502)"
**Solution:** ZATCA service may be temporarily unavailable. Retry after a few minutes.

### "Certificate received but failed to store"
**Solution:** Check filesystem permissions and disk space. Verify certificate format is valid.

## Testing

### Unit Tests
- CSR submission to Compliance CSID API
- Error handling (400, 401, 409, 500)
- Certificate storage after submission
- OAuth token refresh on 401

### Integration Tests
- End-to-end flow: CSR generation → Submission → Storage
- Certificate retrieval and usage
- Tenant isolation verification

## Future Enhancements

1. **Certificate-Key Matching Validation:**
   - Verify private key matches certificate public key
   - Reject mismatched pairs

2. **Production Onboarding API:**
   - Similar implementation for Production environment
   - Different endpoint: `/onboarding/csid`

3. **Certificate Renewal:**
   - Automatic renewal before expiry
   - Seamless certificate rotation

4. **Secret Storage:**
   - Store ZATCA secret securely
   - Use secret for certificate revocation

## Related Documentation

- [ZATCA OAuth Implementation](./ZATCA_OAUTH_IMPLEMENTATION.md)
- [Certificate Lifecycle Analysis](./ZATCA_CERTIFICATE_LIFECYCLE_ANALYSIS.md)
- [ZATCA Setup & Testing](./ZATCA_SETUP_TESTING.md)

---

**Implementation Date:** 2026-01-27  
**Status:** ✅ **COMPLETE**  
**Environment:** SANDBOX (Production onboarding separate)

