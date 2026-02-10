# ZATCA Compliance CSID API - Quick Reference

## Quick Start

### 1. Generate CSR
```bash
curl -X POST \
  -H "X-API-Key: your-api-key" \
  -F "environment=SANDBOX" \
  -F "common_name=test-company.com" \
  -F "organization=Test Company" \
  -F "country=SA" \
  http://localhost:8000/api/v1/zatca/csr/generate
```

**Response:**
```json
{
  "csr": "-----BEGIN CERTIFICATE REQUEST-----\n...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "subject": "C=SA, O=Test Company, CN=test-company.com",
  "key_size": 2048,
  "environment": "SANDBOX"
}
```

### 2. Submit CSR to ZATCA Compliance CSID API
```bash
curl -X POST \
  -H "X-API-Key: your-api-key" \
  -F "csr=-----BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----" \
  -F "private_key=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----" \
  -F "environment=SANDBOX" \
  http://localhost:8000/api/v1/zatca/compliance/csid/submit
```

**Response:**
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

## How Certificate is Used

### 1. Invoice Signing (Clearance API)

The certificate is automatically used when signing invoices:

```python
# Certificate is automatically retrieved by environment
cert_service = CertificateService(db, tenant)
certificate = cert_service.get_certificate(environment=Environment.SANDBOX)

# Certificate files are loaded:
# - certs/tenant_{tenant_id}/sandbox/certificate.pem
# - certs/tenant_{tenant_id}/sandbox/privatekey.pem

# Invoice is signed using certificate + private key
signed_xml = crypto_service.sign(invoice_xml, certificate_path, private_key_path)
```

**What ZATCA Checks:**
- Certificate is valid and not expired
- Certificate is issued by ZATCA CA
- Certificate matches the private key used for signing
- Certificate serial is registered in ZATCA system

### 2. Reporting API

The certificate is used for authenticated reporting:

```python
# Reporting API uses OAuth + Certificate
# OAuth token authenticates the API call
# Certificate is embedded in signed invoice XML
# ZATCA validates both OAuth token and certificate
```

**What ZATCA Checks:**
- OAuth token is valid
- Certificate is valid and not expired
- Certificate matches the invoice signature
- Certificate is registered for the organization

### 3. Clearance API

The certificate is embedded in signed invoice XML:

```xml
<ds:Signature>
  <ds:SignedInfo>
    <!-- Invoice hash -->
  </ds:SignedInfo>
  <ds:SignatureValue>
    <!-- Signature value (signed with private key) -->
  </ds:SignatureValue>
  <ds:KeyInfo>
    <ds:X509Data>
      <ds:X509Certificate>
        <!-- Certificate (from binarySecurityToken) -->
      </ds:X509Certificate>
    </ds:X509Data>
  </ds:KeyInfo>
</ds:Signature>
```

**What ZATCA Checks:**
- Certificate is valid and not expired
- Certificate public key matches signature
- Certificate is issued by ZATCA CA
- Certificate serial is registered
- Certificate is not revoked

## ZATCA Approval Process

### What Happens During Approval

1. **CSR Submission:**
   - CSR is validated for format and content
   - Organization details are verified
   - CSR is queued for certificate issuance

2. **Certificate Issuance:**
   - ZATCA CA signs the certificate
   - Certificate is issued with validity period
   - Certificate serial is registered

3. **Certificate Response:**
   - `binarySecurityToken`: The issued certificate (PEM format)
   - `secret`: Secret for certificate management/revocation
   - `requestID`: Unique identifier for this request
   - `dispositionMessage`: Status message

4. **Certificate Storage:**
   - Certificate is stored securely
   - Private key (from CSR generation) is paired with certificate
   - Certificate metadata is extracted and stored

### ZATCA Validation Checks

**During CSR Submission:**
- ✅ CSR format is valid (PEM, proper structure)
- ✅ CSR subject fields are complete
- ✅ Organization is registered with ZATCA
- ✅ No duplicate CSR for same organization

**During Certificate Usage:**
- ✅ Certificate is not expired
- ✅ Certificate is not revoked
- ✅ Certificate matches private key
- ✅ Certificate is issued by ZATCA CA
- ✅ Certificate serial is registered

## Error Codes Reference

| Code | Meaning | Solution |
|------|---------|----------|
| 400 | Invalid CSR format | Check CSR is valid PEM format |
| 401 | OAuth failed | Verify OAuth credentials |
| 409 | CSR already submitted | Generate new CSR |
| 500 | Server error | Retry later |
| 502 | ZATCA error | Check ZATCA service status |

## Environment Variables

```bash
# Required
ZATCA_SANDBOX_CLIENT_ID=your_client_id
ZATCA_SANDBOX_CLIENT_SECRET=your_client_secret

# Optional
ZATCA_SANDBOX_BASE_URL=https://gw-apic-gov.gazt.gov.sa/e-invoicing/developer-portal
ZATCA_OAUTH_TIMEOUT=10.0
```

## Complete Workflow Example

```python
import requests

API_KEY = "your-api-key"
BASE_URL = "http://localhost:8000"

# Step 1: Generate CSR
csr_response = requests.post(
    f"{BASE_URL}/api/v1/zatca/csr/generate",
    headers={"X-API-Key": API_KEY},
    data={
        "environment": "SANDBOX",
        "common_name": "mycompany.com",
        "organization": "My Company",
        "country": "SA"
    }
)
csr_data = csr_response.json()
print(f"CSR Generated: {csr_data['subject']}")

# Step 2: Submit to Compliance CSID API
submit_response = requests.post(
    f"{BASE_URL}/api/v1/zatca/compliance/csid/submit",
    headers={"X-API-Key": API_KEY},
    data={
        "csr": csr_data["csr"],
        "private_key": csr_data["private_key"],
        "environment": "SANDBOX"
    }
)
result = submit_response.json()

if result["success"]:
    print(f"✅ Certificate stored: ID={result['certificate']['id']}")
    print(f"   Serial: {result['certificate']['serial']}")
    print(f"   Expiry: {result['certificate']['expiry_date']}")
    print(f"   ZATCA Request ID: {result['zatca_response']['requestID']}")
    print(f"\n📝 Certificate is now ready for use in Reporting & Clearance APIs")
else:
    print(f"❌ Error: {result.get('detail', 'Unknown error')}")
```

## Notes

1. **Certificate Type:** Certificates obtained via Compliance CSID API are marked as "COMPLIANCE" type (implicitly through the storage process).

2. **Private Key:** The private key from CSR generation must be provided during submission. It is paired with the certificate from ZATCA.

3. **Environment:** Currently only SANDBOX is supported. Production onboarding uses a separate API endpoint.

4. **Automatic Storage:** The certificate is automatically stored and activated. No manual upload step required.

5. **Certificate Usage:** Once stored, the certificate is automatically used for:
   - Invoice signing (XML signature)
   - Clearance API submissions
   - Reporting API calls

---

**Quick Reference Version:** 1.0  
**Last Updated:** 2026-01-27

