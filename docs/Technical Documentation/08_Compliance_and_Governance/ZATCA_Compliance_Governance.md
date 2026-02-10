# ZATCA Compliance Governance

## Compliance Framework

The system implements strict governance to ensure ZATCA compliance requirements are met.

## Compliance Architecture

### Rule-Based Compliance

**Implementation:**
- All ZATCA-critical operations are rule-based
- Deterministic processing (same input = same output)
- No AI involvement in compliance operations
- Full audit trail for all operations

**Operations:**
- Invoice validation
- UBL XML generation
- Cryptographic signing
- ZATCA API communication
- VAT calculations

### Regulatory Separation

**Compliance Layer:**
- 100% rule-based logic
- ZATCA specification compliance
- Deterministic operations
- Auditable and traceable

**Intelligence Layer:**
- Advisory-only operations
- No compliance decisions
- Optional feature
- Can be disabled globally

## ZATCA Specification Compliance

### Phase-1 Compliance

**Requirements:**
- QR code generation
- Basic invoice validation
- UBL 2.1 XML structure
- Invoice persistence

**Implementation:**
- QRService: QR code generation
- Phase1Validator: Validation rules
- Invoice persistence: Database storage
- Audit logging: Full trail

### Phase-2 Compliance

**Requirements:**
- Real-time clearance with ZATCA
- Cryptographic signing (X.509 certificates)
- UUID and hash chaining (PIH)
- Invoice reporting

**Implementation:**
- XMLGenerator: UBL 2.1 XML generation
- CryptoService: XMLDSig signing
- ClearanceService: ZATCA API communication
- ZatcaPolicyService: Environment and invoice-type policy enforcement
- Certificate-Private Key Cryptographic Verification
- Production CSID Onboarding (OTP-based flow)
- Invoice persistence: Full metadata storage

## Compliance Validation

### Pre-Submission Validation

**Validation Rules:**
- Required fields present
- Data types correct
- Value ranges valid
- ZATCA specification compliance

**Implementation:**
- Phase1Validator: Phase-1 rules
- Phase2Validator: Phase-2 rules
- ZatcaPolicyService: Environment and invoice-type policy validation
- Validation before processing
- Early rejection on validation failure
- Policy checks before clearance submission
- Policy checks before automatic reporting

### Post-Submission Validation

**ZATCA Response:**
- ZATCA clearance status
- Error code mapping
- Response validation
- Status update

**Implementation:**
- ClearanceService: Response handling
- Error catalog: Error code mapping
- Status tracking: Invoice status updates
- Audit logging: Full response storage

## Audit and Traceability

### Invoice Audit Trail

**InvoiceLog Entries:**
- All processing attempts logged
- Request payload stored
- Generated XML stored (Phase-2)
- ZATCA response stored
- Status changes tracked

**Retention:**
- Configurable retention period
- Anonymization or purging
- Compliance requirements met
- Full traceability maintained

### Request Audit Trail

**Request Logging:**
- All API requests logged
- Request method, path, client IP
- Response status, processing time
- Tenant context included

**Security:**
- Sensitive data masked
- PII excluded
- Log encryption (future)
- Secure log storage

## Compliance Monitoring

### Status Tracking

**Invoice Status:**
- CREATED → PROCESSING → CLEARED/REJECTED/FAILED
- Status changes logged
- Status history maintained
- Retry operations tracked

### Error Tracking

**Error Management:**
- ZATCA error codes mapped
- Error explanations provided
- Error trends analyzed
- Root cause analysis

## Current Implementation Status

All ZATCA compliance governance components are implemented:

- Rule-based compliance operations
- ZATCA specification compliance
- Pre and post-submission validation
- Environment and invoice-type policy enforcement
- Production CSID Onboarding (OTP-based flow)
- Certificate-Private Key Cryptographic Verification
- Full audit trail
- Status tracking
- Error management

**Policy Enforcement:**

The system enforces strict ZATCA production rules based on environment and invoice type:

- SANDBOX: Any invoice type → Clearance + Reporting (allowed)
- PRODUCTION: Standard (388) → Clearance ONLY
- PRODUCTION: Simplified (383) → Reporting ONLY
- PRODUCTION: Debit Note (381) → Clearance ONLY
- PRODUCTION: Mixed flow → Reject

Policy checks run before ZATCA API calls to prevent invalid operations. The system fails fast with clear error messages when policy violations are detected.

**Certificate Onboarding:**

The system supports automated certificate onboarding for both environments:

- Sandbox: Automated Compliance CSID API integration
- Production: OTP-based onboarding flow with two-step validation
- Both: Automatic certificate storage with cryptographic verification

All certificate onboarding flows include cryptographic verification to ensure the private key matches the certificate public key before storage.

Future considerations (not currently implemented):

- Automated compliance testing
- Compliance reporting
- Regulatory change management
- Compliance certification
- Advanced monitoring and alerting

