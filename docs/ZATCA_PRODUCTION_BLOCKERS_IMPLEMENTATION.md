# ZATCA Production Blockers Implementation

## Executive Summary

This document describes the implementation of three critical ZATCA production blockers:

1. **Production CSID Onboarding** - Full OTP-based onboarding flow
2. **Certificate-Private Key Cryptographic Verification** - Real cryptographic validation
3. **Environment & Invoice-Type Policy Enforcement** - Strict ZATCA rule enforcement

All implementations are production-safe, ZATCA-auditor friendly, and future-proof.

---

## 🧱 BLOCKER 1: Production CSID Onboarding

### Architecture

**Service:** `backend/app/integrations/zatca/production_onboarding.py`

**API Endpoint:** `POST /api/v1/zatca/production/onboarding/submit`

### Implementation Details

#### Two-Step OTP Flow

**Step 1: Submit Onboarding Request**
```
POST /api/v1/zatca/production/onboarding/submit
Body:
  - csr: Certificate Signing Request (PEM)
  - private_key: Private key (PEM)
  - organization_name: Organization legal name
  - vat_number: VAT registration number (15 digits)

Response:
  - requestID: ZATCA request identifier
  - otp: OTP code (if required)
  - next_step: Instructions for OTP validation
```

**Step 2: Validate OTP and Receive Certificate**
```
POST /api/v1/zatca/production/onboarding/submit
Body:
  - csr: (same as Step 1)
  - private_key: (same as Step 1)
  - organization_name: (same as Step 1)
  - vat_number: (same as Step 1)
  - otp: OTP code from ZATCA
  - request_id: Request ID from Step 1

Response:
  - certificate: Certificate metadata
  - zatca_response: ZATCA response details
```

#### Key Features

1. **OTP-Based Authentication**
   - Supports ZATCA Production OTP flow
   - Handles OTP validation with proper error codes (403 for invalid OTP)
   - Idempotent behavior (can retry OTP validation)

2. **Automatic Certificate Storage**
   - Certificate automatically stored after OTP validation
   - Uses existing `CertificateService` for secure storage
   - Enforces tenant isolation

3. **Error Handling**
   - 400: Invalid CSR format, missing organization details, invalid VAT number
   - 401: OAuth authentication failed
   - 403: Invalid OTP code
   - 404: Request ID not found
   - 409: CSR already submitted
   - 500: ZATCA server error

4. **Certificate Lifecycle Management**
   - Supports ACTIVE, EXPIRED, REVOKED statuses
   - Automatic deactivation of existing certificates
   - Secure storage in `certs/tenant_{tenant_id}/production/`

### Code Structure

```python
class ProductionOnboardingService:
    async def submit_onboarding_request(
        self,
        csr_pem: str,
        organization_name: str,
        vat_number: str
    ) -> Dict[str, str]
    
    async def validate_otp(
        self,
        request_id: str,
        otp: str
    ) -> Dict[str, str]
```

### Security Considerations

- OAuth credentials required for PRODUCTION environment
- Private key only transmitted during onboarding (never stored in logs)
- Certificate stored with 600 permissions (owner read/write only)
- Tenant isolation enforced at all levels

---

## 🧱 BLOCKER 2: Certificate-Private Key Cryptographic Verification

### Architecture

**Service:** `backend/app/services/certificate_service.py`

**Method:** `_verify_certificate_key_match()`

### Implementation Details

#### Cryptographic Verification Process

1. **Extract Public Key from Certificate**
   - Parse X.509 certificate using cryptography library
   - Extract public key from certificate

2. **Derive Public Key from Private Key**
   - Load private key (supports PKCS8 and traditional OpenSSL formats)
   - Derive public key from private key

3. **Compare Key Parameters**
   - Extract RSA modulus (n) from both keys
   - Extract RSA exponent (e) from both keys
   - Compare modulus and exponent values
   - Reject if mismatch detected

#### Error Response

```json
{
  "error": "CERT_KEY_MISMATCH",
  "message": "Private key does not match certificate public key. The RSA modulus values differ."
}
```

### Code Structure

```python
def _verify_certificate_key_match(
    self,
    certificate_content: bytes,
    private_key_content: bytes
) -> None:
    """
    Cryptographically verifies that the private key matches the certificate public key.
    
    Raises:
        ValueError: If private key does not match certificate public key
    """
    # 1. Extract public key from certificate
    cert_obj = x509.load_pem_x509_certificate(certificate_content, default_backend())
    cert_public_key = cert_obj.public_key()
    
    # 2. Load private key and derive public key
    private_key_obj = serialization.load_pem_private_key(...)
    key_public_key = private_key_obj.public_key()
    
    # 3. Compare RSA parameters
    cert_public_numbers = cert_public_key.public_numbers()
    key_public_numbers = key_public_key.public_numbers()
    
    if cert_public_numbers.n != key_public_numbers.n:
        raise ValueError("CERT_KEY_MISMATCH: RSA modulus mismatch")
    
    if cert_public_numbers.e != key_public_numbers.e:
        raise ValueError("CERT_KEY_MISMATCH: RSA exponent mismatch")
```

### Integration Points

- **Certificate Upload:** Verification runs automatically during `upload_certificate()`
- **Production Onboarding:** Verification runs when certificate is stored after OTP validation
- **Compliance CSID:** Verification runs when certificate is stored from sandbox onboarding

### Security Considerations

- Zero tolerance for mismatch (rejects immediately)
- Clear error messages for debugging
- Supports RSA keys only (ZATCA requirement)
- No key material logged (only error codes)

---

## 🧱 BLOCKER 3: Environment & Invoice-Type Policy Enforcement

### Architecture

**Service:** `backend/app/services/zatca_policy_service.py`

**Integration:** `backend/app/services/invoice_service.py`

### Policy Rules

| Environment | Invoice Type | Allowed Action |
|------------|-------------|----------------|
| SANDBOX | Any (388, 383, 381) | Clearance + Reporting (BOTH) |
| PRODUCTION | Standard (388) | Clearance ONLY |
| PRODUCTION | Simplified (383) | Reporting ONLY |
| PRODUCTION | Debit Note (381) | Clearance ONLY |
| PRODUCTION | Mixed flow | ❌ Reject |

### Implementation Details

#### Policy Service Methods

```python
class ZatcaPolicyService:
    def validate_clearance_allowed(
        self,
        environment: Environment,
        invoice_type: str
    ) -> None
    
    def validate_reporting_allowed(
        self,
        environment: Environment,
        invoice_type: str
    ) -> None
    
    def validate_clearance_and_reporting_allowed(
        self,
        environment: Environment,
        invoice_type: str
    ) -> None
```

#### Error Response

```json
{
  "error": "ZATCA_POLICY_VIOLATION",
  "message": "Clearance is not allowed for 383 invoices in PRODUCTION. Standard invoices (388) can only be cleared in production. Simplified invoices (383) can only be reported in production."
}
```

### Integration Points

1. **Before Clearance Submission**
   - Policy check runs in `_process_phase2()` before XML generation
   - Raises `ZatcaPolicyViolation` if clearance not allowed
   - Prevents invalid API calls to ZATCA

2. **Before Automatic Reporting**
   - Policy check runs after successful clearance
   - Validates that automatic reporting (clearance + reporting) is allowed
   - In production, blocks automatic reporting for Standard invoices
   - Non-blocking: logs warning but does not fail invoice

### Code Flow

```python
# In InvoiceService._process_phase2()

# 1. Validate clearance is allowed
self.policy_service.validate_clearance_allowed(
    environment=request.environment,
    invoice_type=request.invoice_type
)

# 2. Process invoice (XML generation, signing, clearance)

# 3. After clearance, validate reporting is allowed
if clearance_status == "CLEARED":
    try:
        self.policy_service.validate_clearance_and_reporting_allowed(
            environment=request.environment,
            invoice_type=request.invoice_type
        )
        # Proceed with automatic reporting
    except ZatcaPolicyViolation:
        # Skip reporting (non-blocking)
        logger.warning("Automatic reporting blocked by ZATCA policy")
```

### Security Considerations

- Fail-fast: Policy checks run before ZATCA API calls
- Clear error messages for audit trails
- Non-blocking reporting errors (clearance success preserved)
- Centralized policy rules (easy to update)

---

## 📦 File Structure

```
backend/
├── app/
│   ├── integrations/
│   │   └── zatca/
│   │       └── production_onboarding.py      # Production onboarding service
│   ├── services/
│   │   ├── certificate_service.py            # Enhanced with cryptographic verification
│   │   ├── zatca_policy_service.py            # Policy enforcement service
│   │   └── invoice_service.py                # Enhanced with policy checks
│   └── api/
│       └── v1/
│           └── routes/
│               └── zatca.py                  # Production onboarding endpoint
```

---

## 🔒 Production Readiness Checklist

### ✅ Production CSID Onboarding
- [x] OTP-based onboarding flow implemented
- [x] CSR submission with organization details
- [x] OTP validation endpoint
- [x] Automatic certificate storage
- [x] Certificate lifecycle management (ACTIVE, EXPIRED, REVOKED)
- [x] Retry-safe and idempotent behavior
- [x] Comprehensive error handling
- [x] Secure certificate storage per tenant

### ✅ Certificate-Private Key Verification
- [x] Cryptographic verification implemented
- [x] Public key extraction from certificate
- [x] Public key derivation from private key
- [x] RSA modulus and exponent comparison
- [x] Zero tolerance for mismatch
- [x] Clear error messages
- [x] Integration with certificate upload
- [x] Integration with onboarding flows

### ✅ Environment & Invoice-Type Policy Enforcement
- [x] Policy service implemented
- [x] Clearance policy validation
- [x] Reporting policy validation
- [x] Mixed flow policy validation
- [x] Integration with invoice processing
- [x] Fail-fast before ZATCA API calls
- [x] Non-blocking reporting errors
- [x] Clear policy violation errors

### ✅ Non-Functional Requirements
- [x] No breaking changes to sandbox flow
- [x] Non-blocking reporting errors
- [x] Idempotent API behavior
- [x] Clear logs for ZATCA audits
- [x] Clean separation (sandbox vs production)
- [x] No hardcoded secrets
- [x] Environment-driven configuration

---

## 🚀 Usage Examples

### Production Onboarding

**Step 1: Submit Onboarding Request**
```bash
curl -X POST "https://api.example.com/api/v1/zatca/production/onboarding/submit" \
  -H "X-API-Key: your-api-key" \
  -F "csr=$(cat csr.pem)" \
  -F "private_key=$(cat private_key.pem)" \
  -F "organization_name=My Company Ltd" \
  -F "vat_number=123456789012345"
```

**Step 2: Validate OTP**
```bash
curl -X POST "https://api.example.com/api/v1/zatca/production/onboarding/submit" \
  -H "X-API-Key: your-api-key" \
  -F "csr=$(cat csr.pem)" \
  -F "private_key=$(cat private_key.pem)" \
  -F "organization_name=My Company Ltd" \
  -F "vat_number=123456789012345" \
  -F "otp=123456" \
  -F "request_id=req-12345"
```

### Policy Violation Example

**Production Standard Invoice (Clearance Only)**
```json
{
  "invoice_type": "388",
  "environment": "PRODUCTION"
}
```
✅ Clearance allowed  
❌ Reporting blocked (automatic reporting skipped)

**Production Simplified Invoice (Reporting Only)**
```json
{
  "invoice_type": "383",
  "environment": "PRODUCTION"
}
```
❌ Clearance blocked (policy violation error)  
✅ Reporting allowed

---

## 📝 Error Handling Strategy

### Production Onboarding Errors

| Error Code | HTTP Status | Description |
|-----------|-------------|-------------|
| Invalid CSR format | 400 | CSR must be PEM format |
| Invalid VAT number | 400 | VAT number must be 15 digits |
| OAuth failed | 401 | Production OAuth credentials invalid |
| Invalid OTP | 403 | OTP code is incorrect |
| Request not found | 404 | Request ID expired or invalid |
| CSR conflict | 409 | CSR already submitted |
| ZATCA server error | 502 | ZATCA service unavailable |

### Certificate-Key Mismatch Errors

| Error Code | Description |
|-----------|-------------|
| CERT_KEY_MISMATCH | Private key does not match certificate |
| Invalid key format | Private key is not PEM format |
| Non-RSA key | Only RSA keys are supported |

### Policy Violation Errors

| Error Code | Description |
|-----------|-------------|
| ZATCA_POLICY_VIOLATION | Operation not allowed for environment/invoice type |

---

## 🎯 Success Criteria

✅ **Fully ready for ZATCA Production Onboarding**
- Complete OTP-based flow implemented
- Automatic certificate storage
- Certificate lifecycle management

✅ **Safe for real taxpayers**
- Cryptographic verification prevents mismatched keys
- Policy enforcement prevents invalid operations
- Clear error messages for debugging

✅ **Acceptable to ZATCA auditors**
- Comprehensive logging
- Clear audit trails
- Policy compliance enforced

✅ **Enterprise-grade and scalable**
- Tenant isolation
- Idempotent operations
- Retry-safe behavior
- Environment-driven configuration

---

## 🔄 Future Enhancements

1. **Certificate Expiry Monitoring**
   - Automatic alerts before expiry
   - Certificate renewal workflow

2. **Production OTP Delivery**
   - Integration with email/SMS providers
   - OTP delivery status tracking

3. **Policy Rule Updates**
   - Dynamic policy configuration
   - A/B testing support

4. **Enhanced Audit Logging**
   - Detailed policy decision logs
   - Certificate verification audit trails

---

## 📚 References

- ZATCA Developer Portal Manual
- ZATCA Production Onboarding API Specification
- ZATCA Phase-2 Compliance Requirements
- RSA Key Pair Generation Standards

