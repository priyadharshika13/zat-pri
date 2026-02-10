# Certificate and Key Management

## Certificate Storage

Certificates and private keys are stored on the filesystem with strict tenant isolation.

## Storage Structure

**Directory Convention:**
```
certs/
  tenant_{tenant_id}/
    sandbox/
      certificate.pem
      privatekey.pem
    production/
      certificate.pem
      privatekey.pem
```

**Isolation:**
- Each tenant has separate directory
- Environment subdirectories (sandbox, production)
- Path validation prevents cross-tenant access

## File Permissions

**Certificate Files:**
- Permissions: 600 (owner read/write only)
- Group and others: no access
- Set on file creation
- Maintained throughout lifecycle

**Directory Permissions:**
- Tenant directories: 700 (owner read/write/execute)
- Environment directories: 700
- Base certs directory: 755

## Certificate Upload

**Process:**
1. Certificate and private key received via API
2. Certificate format validated (PEM)
3. Certificate expiry checked
4. Private key format validated (PEM)
5. Existing active certificate deactivated
6. Files written to tenant-specific directory
7. File permissions set to 600
8. Certificate metadata stored in database

**Validation:**
- Certificate must be valid PEM format
- Certificate must not be expired
- Private key must be valid PEM format
- Certificate and key must match (cryptographically verified)

## Certificate Metadata

**Database Storage:**
- Certificate serial number
- Issuer information
- Expiry date
- Status (ACTIVE, EXPIRED, REVOKED)
- Upload timestamp
- Environment (SANDBOX, PRODUCTION)

**Not Stored:**
- Certificate content (filesystem only)
- Private key content (filesystem only)
- Private key material (never in database)

## Certificate Access

**Path Resolution:**
- `get_tenant_cert_paths()` resolves paths
- Validates tenant_id matches authenticated tenant
- Validates environment is valid
- Returns paths only if files exist

**Access Control:**
- Tenant context required for all operations
- Path validation enforces tenant isolation
- Certificate files not accessible via API
- Only metadata returned in API responses

## Certificate Lifecycle

**Activation:**
- New certificate upload activates certificate
- Previous active certificate deactivated
- Only one active certificate per tenant per environment

**Deactivation:**
- Automatic on new certificate upload
- Manual deactivation via API (future)
- Status updated in database
- Files remain on filesystem

**Expiration:**
- Expiry date checked on upload
- Expired certificates rejected
- Expiration monitoring (future)
- Automatic deactivation on expiry (future)

**Revocation:**
- Manual revocation via API (future)
- Status updated to REVOKED
- Certificate cannot be used for signing
- Files remain on filesystem

## Private Key Security

**Storage:**
- Private keys stored on filesystem only
- Never stored in database
- Never exposed in API responses
- File permissions: 600

**Usage:**
- Loaded from filesystem during signing
- Kept in memory only during operation
- Never logged or exposed
- Cleared from memory after use

## Certificate Validation

**Format Validation:**
- PEM encoding required
- X.509 certificate structure
- Valid ASN.1 encoding
- Certificate chain validation (future)

**Expiry Validation:**
- Expiry date extracted from certificate
- Current date compared to expiry
- Expired certificates rejected
- Warning for certificates expiring soon (future)

**Key Validation:**
- PEM encoding required
- RSA key format (current)
- Cryptographic verification: Private key matches certificate public key
- RSA modulus and exponent comparison
- Zero tolerance for mismatch (rejects immediately)
- ECDSA key format (future)
- Key size validation (future)

## Current Implementation Status

All certificate management components are implemented:

- Certificate upload and validation
- Cryptographic certificate-private key verification
- Production CSID Onboarding (OTP-based flow)
- Sandbox Compliance CSID (automated)
- Secure filesystem storage
- Tenant isolation
- File permissions
- Metadata storage
- Certificate activation/deactivation
- Certificate lifecycle management (ACTIVE, EXPIRED, REVOKED)

**Certificate Onboarding:**

The system supports two certificate onboarding flows:

**Sandbox Onboarding:**
- Endpoint: `POST /api/v1/zatca/compliance/csid/submit`
- Automated flow: CSR submission → certificate receipt → automatic storage
- No OTP required for sandbox environment

**Production Onboarding:**
- Endpoint: `POST /api/v1/zatca/production/onboarding/submit`
- OTP-based flow: Submit request → receive OTP → validate OTP → receive certificate
- Automatic certificate storage after OTP validation
- Requires production OAuth credentials

**Cryptographic Verification:**

The system performs cryptographic verification to ensure the private key matches the certificate public key. This verification runs automatically during:

- Certificate upload operations
- Production onboarding (after OTP validation)
- Sandbox compliance CSID (after certificate receipt)

The verification process:
1. Extracts public key from X.509 certificate
2. Derives public key from private key
3. Compares RSA modulus (n) and exponent (e)
4. Rejects with `CERT_KEY_MISMATCH` error if mismatch detected

Implementation: `CertificateService._verify_certificate_key_match()`

Future considerations (not currently implemented):

- Certificate chain validation
- Automatic expiration monitoring
- Certificate revocation
- Key rotation automation
- HSM integration for key storage

