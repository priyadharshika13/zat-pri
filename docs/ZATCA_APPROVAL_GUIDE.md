# ZATCA Approval Guide - FATURAIX API Product

**Complete Checklist and Application Flow for ZATCA e-Invoicing Compliance Approval**

---

## Table of Contents

1. [ZATCA Technical Checklist](#step-1-zatca-technical-checklist)
2. [Pre-Application Readiness Check](#step-2-pre-application-readiness-check)
3. [ZATCA Application Flow](#step-3-zatca-application-flow)
4. [Questions ZATCA May Ask](#step-4-questions-zatca-may-ask)
5. [Final Recommendations](#step-5-final-recommendations)

---

# STEP 1: ZATCA TECHNICAL CHECKLIST

## 1. Phase-1 Compliance Items

### Mandatory Requirements

- [x] **Invoice Number Uniqueness**: Enforced via `(tenant_id, invoice_number)` unique constraint
- [x] **Invoice Date Format**: ISO 8601 format (YYYY-MM-DD)
- [x] **VAT Rate Validation**: 15% VAT rate enforced in Phase-1 validator
- [x] **Tax Number Format**: 15-digit Saudi tax number validation
- [x] **QR Code Generation**: Phase-1 QR codes generated with required fields
- [x] **Total Amount Calculation**: VAT calculations validated (subtotal + VAT = total)
- [x] **Seller Information**: Seller name, tax number, address mandatory
- [x] **Buyer Information**: Buyer name, tax number mandatory
- [x] **Line Items**: At least one line item with description, quantity, unit price
- [x] **Currency**: SAR (Saudi Riyal) currency code

### Optional / Best Practice

- [x] **Idempotency**: Duplicate invoice prevention (tenant_id + invoice_number)
- [x] **Audit Logging**: Immutable audit trail for all invoice submissions
- [x] **Error Handling**: Comprehensive error responses with Arabic translations
- [x] **Validation Before Processing**: Pre-flight validation with detailed error messages

---

## 2. Phase-2 Clearance Requirements

### Mandatory Requirements

- [x] **UBL XML Generation**: Full UBL 2.1 XML schema compliance
- [x] **XML Digital Signature**: XMLDSig with RSA-SHA256 signing
- [x] **CSID Certificate**: Certificate-based signing (tenant-scoped, environment-aware)
- [x] **XML Hash Calculation**: SHA-256 hash of canonicalized XML
- [x] **Clearance Submission**: Submit signed XML to ZATCA clearance API
- [x] **Clearance Status Handling**: CLEARED / REJECTED status processing
- [x] **QR Code from ZATCA**: Use ZATCA-provided QR code (not local generation) when available
- [x] **UUID Generation**: Unique invoice UUID for Phase-2 invoices
- [x] **Signed XML Storage**: Store signed XML for audit purposes
- [x] **Clearance Response Parsing**: Extract clearance UUID, status, QR code from ZATCA response

### Optional / Best Practice

- [x] **Sandbox Placeholder Signing**: Fast placeholder signatures for sandbox (non-blocking)
- [x] **Production Real Signing**: Real cryptographic signing for production
- [x] **Certificate Expiry Monitoring**: Certificate expiry date tracking
- [x] **Certificate Rotation**: Support for certificate upload and activation
- [x] **Clearance Retry Logic**: Automatic retry with exponential backoff (3 retries)
- [x] **Clearance Timeout Handling**: Configurable timeout (default 30 seconds)

---

## 3. Cryptography & Certificate Requirements

### Mandatory Requirements

- [x] **Certificate Format**: PEM-encoded X.509 certificates
- [x] **Private Key Format**: PEM-encoded RSA private keys
- [x] **Certificate Validation**: Certificate format and expiry validation on upload
- [x] **Tenant Isolation**: Certificates stored per-tenant (certs/tenant_{id}/{environment}/)
- [x] **Environment Separation**: Separate certificates for SANDBOX and PRODUCTION
- [x] **XML Canonicalization**: C14N canonicalization before signing
- [x] **Hash Algorithm**: SHA-256 for XML hashing
- [x] **Signature Algorithm**: RSA-SHA256 for digital signatures
- [x] **Base64 Encoding**: Digital signature encoded in Base64

### Optional / Best Practice

- [x] **Certificate Metadata Storage**: Serial number, issuer, expiry date in database
- [x] **Certificate Status Tracking**: ACTIVE, EXPIRED, REVOKED status management
- [x] **One Active Certificate**: Only one active certificate per tenant per environment
- [x] **Secure File Permissions**: Certificate files stored with 600 permissions (owner read/write only)
- [x] **Certificate Rotation Support**: Deactivate old certificate when new one uploaded

---

## 4. XML / UBL Structure Validation

### Mandatory Requirements

- [x] **UBL 2.1 Schema**: Full compliance with UBL 2.1 Invoice schema
- [x] **Namespace Declarations**: Correct namespace declarations (urn:oasis:names:specification:ubl:schema:xsd:Invoice-2)
- [x] **Required Elements**: All mandatory UBL elements present
  - [x] Invoice ID (invoice_number)
  - [x] Issue Date (invoice_date)
  - [x] Invoice Type Code
  - [x] Document Currency Code (SAR)
  - [x] Seller Party (name, tax number, address)
  - [x] Buyer Party (name, tax number)
  - [x] Invoice Line Items (description, quantity, price, VAT)
  - [x] Legal Monetary Total (line extension, tax exclusive, tax inclusive)
- [x] **XML Encoding**: UTF-8 encoding
- [x] **XML Well-Formedness**: Valid XML structure (no unrendered templates)
- [x] **Template Validation**: Pre-signing validation to ensure no unrendered variables

### Optional / Best Practice

- [x] **XML Validation Before Signing**: Validate XML is fully rendered before cryptographic operations
- [x] **XML Storage**: Store generated XML in database for audit
- [x] **XML Retrieval**: API endpoint to retrieve invoice XML

---

## 5. Error Handling Expectations

### Mandatory Requirements

- [x] **ZATCA API Error Handling**: Handle HTTP errors (400, 401, 403, 404, 500, 502, 504)
- [x] **Timeout Handling**: Configurable timeout with retry logic
- [x] **Network Error Handling**: Connection errors, DNS failures
- [x] **Clearance Rejection Handling**: Parse and store REJECTED status with error codes
- [x] **Error Response Format**: Structured error responses with error codes
- [x] **Arabic Error Messages**: Bilingual error messages (English + Arabic)
- [x] **Error Logging**: All errors logged with context (tenant_id, invoice_number, error_type)

### Optional / Best Practice

- [x] **Retry Logic**: Automatic retry with exponential backoff (3 retries)
- [x] **Error Categorization**: Categorize errors (validation, network, ZATCA, system)
- [x] **Error Recovery**: Graceful degradation (e.g., fallback to rule-based AI responses)
- [x] **Error Notifications**: Log errors for monitoring and alerting

---

## 6. Audit & Traceability Expectations

### Mandatory Requirements

- [x] **Invoice Persistence**: All invoices stored in database with full metadata
- [x] **Invoice Status Tracking**: Status lifecycle (CREATED → PROCESSING → CLEARED/REJECTED/FAILED)
- [x] **ZATCA Response Storage**: Store full ZATCA API responses
- [x] **Timestamp Tracking**: Created, submitted, cleared timestamps
- [x] **UUID Tracking**: Invoice UUID stored for Phase-2 invoices
- [x] **Hash Tracking**: XML hash stored for verification
- [x] **Clearance Status**: CLEARED / REJECTED status stored
- [x] **ZATCA Response Code**: Error codes from ZATCA stored

### Optional / Best Practice

- [x] **Immutable Audit Logs**: Append-only audit trail (JSONL format)
- [x] **Request Payload Storage**: Original invoice request stored
- [x] **Generated XML Storage**: Generated XML stored for audit
- [x] **Tenant Isolation**: All audit records tenant-scoped
- [x] **Audit Record Immutability**: Frozen dataclass ensures immutability
- [x] **Observability Fields**: Extended logging with request payload, XML, ZATCA response

---

## 7. Sandbox vs Production Differences

### Sandbox Environment

- [x] **Placeholder Signatures**: Fast placeholder signatures (non-blocking, instant)
- [x] **ZATCA Sandbox URL**: `https://gw-apic-gov.gazt.gov.sa/e-invoicing/developer-portal`
- [x] **No Real Certificate Required**: Placeholder signatures work without real CSID
- [x] **Test Certificates**: Can use test/self-signed certificates
- [x] **No Legal Impact**: Sandbox invoices have no legal/tax implications

### Production Environment

- [x] **Real Cryptographic Signing**: Actual RSA-SHA256 signing with CSID certificate
- [x] **ZATCA Production URL**: `https://gw-apic-gov.gazt.gov.sa/e-invoicing/core`
- [x] **Valid CSID Certificate Required**: Must have valid, non-expired CSID certificate
- [x] **Production Access Guards**: Only paid plans can access production
- [x] **Production Confirmation**: Explicit `confirm_production=true` required
- [x] **Legal Compliance**: Production invoices are legally binding

### Environment Configuration

- [x] **Environment Variable**: `ZATCA_ENV` (SANDBOX or PRODUCTION)
- [x] **Tenant-Scoped Environment**: Each tenant can have different environment
- [x] **Certificate Per Environment**: Separate certificates for sandbox and production
- [x] **URL Routing**: Automatic URL selection based on environment

---

# STEP 2: PRE-APPLICATION READINESS CHECK

## What Must Be Verified in Sandbox

### Functional Verification

- [ ] **Phase-1 Invoice Flow**: Create and process Phase-1 invoice successfully
  - [ ] Invoice number uniqueness enforced
  - [ ] QR code generated correctly
  - [ ] VAT calculations correct
  - [ ] All mandatory fields validated

- [ ] **Phase-2 Invoice Flow**: Create and process Phase-2 invoice successfully
  - [ ] UBL XML generated correctly
  - [ ] XML signed (placeholder signature in sandbox)
  - [ ] Clearance submitted to ZATCA sandbox
  - [ ] Clearance status received (CLEARED or REJECTED)
  - [ ] QR code from ZATCA received (if cleared)

- [ ] **Certificate Upload**: Upload test certificate for sandbox
  - [ ] Certificate format validated
  - [ ] Certificate metadata extracted (serial, issuer, expiry)
  - [ ] Certificate stored securely (tenant-isolated)
  - [ ] Old certificate deactivated when new one uploaded

- [ ] **Error Handling**: Test error scenarios
  - [ ] Invalid invoice data → validation errors
  - [ ] ZATCA API timeout → retry logic works
  - [ ] ZATCA API error → error response parsed correctly
  - [ ] Network failure → graceful error handling

- [ ] **Idempotency**: Test duplicate invoice prevention
  - [ ] Same invoice_number submitted twice → second returns existing invoice
  - [ ] No duplicate invoices created

- [ ] **Audit Logging**: Verify audit trail
  - [ ] Invoice records created in database
  - [ ] InvoiceLog entries created
  - [ ] Audit file entries written (if file-based audit enabled)
  - [ ] All timestamps recorded correctly

### Technical Verification

- [ ] **API Endpoints**: All endpoints respond correctly
  - [ ] Health check endpoint
  - [ ] Invoice creation endpoint
  - [ ] Invoice retrieval endpoint
  - [ ] Certificate upload endpoint
  - [ ] Reporting endpoints

- [ ] **Database**: Database operations work correctly
  - [ ] Invoice persistence
  - [ ] Invoice retrieval
  - [ ] InvoiceLog creation
  - [ ] Certificate storage

- [ ] **ZATCA Integration**: ZATCA API communication works
  - [ ] Sandbox URL accessible
  - [ ] Clearance submission successful
  - [ ] Response parsing correct
  - [ ] Error handling works

---

## What Evidence Should Be Kept

### Documentation Evidence

1. **Test Invoice Samples** (Keep for 6+ months)
   - [ ] Phase-1 invoice request (JSON)
   - [ ] Phase-1 invoice response (with QR code)
   - [ ] Phase-2 invoice request (JSON)
   - [ ] Phase-2 generated XML (unsigned)
   - [ ] Phase-2 signed XML
   - [ ] Phase-2 clearance response (CLEARED)
   - [ ] Phase-2 clearance response (REJECTED - if applicable)

2. **Certificate Evidence**
   - [ ] Certificate upload API response
   - [ ] Certificate metadata (serial, issuer, expiry)
   - [ ] Certificate validation logs

3. **Error Handling Evidence**
   - [ ] Validation error responses
   - [ ] ZATCA API error responses
   - [ ] Network timeout handling logs

4. **Audit Trail Evidence**
   - [ ] Database invoice records (screenshots or exports)
   - [ ] InvoiceLog entries
   - [ ] Audit file samples (if file-based)

5. **API Test Results**
   - [ ] Postman/curl command examples
   - [ ] API response samples
   - [ ] Test execution logs

### Screenshots / Logs

- [ ] **ZATCA Sandbox Portal**: Screenshots of successful clearance submissions
- [ ] **API Responses**: Screenshots of successful API calls
- [ ] **Database Records**: Screenshots of invoice records in database
- [ ] **Error Logs**: Sample error logs showing proper error handling
- [ ] **Certificate Management**: Screenshots of certificate upload/management

### XML Samples

- [ ] **Phase-2 XML Samples**: Keep 3-5 sample XML files
  - [ ] One CLEARED invoice XML
  - [ ] One REJECTED invoice XML (if available)
  - [ ] One with different invoice types (standard, simplified, etc.)

---

## What Configuration Must Be Production-Ready

### Environment Configuration

- [ ] **ZATCA_ENV**: Set to `PRODUCTION` (not SANDBOX)
- [ ] **ZATCA_PRODUCTION_BASE_URL**: Correct production URL
- [ ] **ZATCA_TIMEOUT**: Appropriate timeout (30 seconds recommended)
- [ ] **ZATCA_MAX_RETRIES**: Retry count (3 recommended)

### Security Configuration

- [ ] **API_KEYS**: Production API keys configured
- [ ] **INTERNAL_SECRET_KEY**: Strong secret key for internal endpoints
- [ ] **Database Security**: SSL/TLS enabled for database connection
- [ ] **Certificate Storage**: Secure file permissions (600) for certificates

### Application Configuration

- [ ] **DEBUG**: Set to `false` in production
- [ ] **ENABLE_DOCS**: Set to `false` in production (disable Swagger UI)
- [ ] **ENVIRONMENT_NAME**: Set to `production`
- [ ] **Logging Level**: Set to `INFO` or `WARNING` (not DEBUG)

### Certificate Configuration

- [ ] **Production Certificates**: Valid CSID certificates uploaded for all tenants
- [ ] **Certificate Expiry**: Certificates not expired
- [ ] **Certificate Validation**: All certificates validated and active

### Database Configuration

- [ ] **Database URL**: Production database connection string
- [ ] **Database Migrations**: All migrations applied
- [ ] **Database Backups**: Backup strategy in place

---

# STEP 3: ZATCA APPLICATION FLOW

## 1. Where to Apply

### Application Portal

**ZATCA Developer Portal**: https://zatca.gov.sa/en/E-Invoicing/SystemsDevelopers/Pages/default.aspx

**Alternative**: Contact ZATCA directly via:
- Email: e-invoicing@zatca.gov.sa
- Phone: 19993 (ZATCA support line)
- ZATCA Service Centers (physical locations)

### Application Channel

- **Online Portal**: Preferred method (if available)
- **Email Application**: Send application documents to e-invoicing@zatca.gov.sa
- **Service Center**: Visit ZATCA service center with required documents

---

## 2. What Company Details Are Required

### Company Information

- [ ] **Company Name**: Full legal company name (Arabic and English)
- [ ] **Commercial Registration Number**: CR number
- [ ] **Tax Identification Number**: 15-digit Saudi tax number
- [ ] **Company Address**: Full business address
- [ ] **Contact Person**: Name and title of authorized contact
- [ ] **Contact Email**: Business email address
- [ ] **Contact Phone**: Business phone number
- [ ] **Company Website**: Company website URL (if applicable)

### Product Information

- [ ] **Product Name**: FATURAIX (or your product name)
- [ ] **Product Type**: API-based SaaS e-Invoicing solution
- [ ] **Product Description**: Brief description of the product
- [ ] **Target Market**: Who will use the product (B2B, B2C, etc.)
- [ ] **Integration Method**: REST API
- [ ] **Supported Phases**: Phase-1 and Phase-2

---

## 3. What Technical Details ZATCA Asks

### Technical Architecture

- [ ] **System Architecture**: Describe your system architecture
  - **Recommended Answer**: "RESTful API-based SaaS platform with multi-tenant architecture. Supports Phase-1 and Phase-2 invoice processing. Uses FastAPI (Python) backend with PostgreSQL database. Implements UBL 2.1 XML generation, XMLDSig signing with RSA-SHA256, and ZATCA clearance API integration."

- [ ] **UBL XML Generation**: How do you generate UBL XML?
  - **Recommended Answer**: "We generate UBL 2.1 compliant XML invoices using the standard UBL Invoice schema (urn:oasis:names:specification:ubl:schema:xsd:Invoice-2). XML is generated server-side from invoice request data, ensuring all mandatory fields are included and properly formatted."

- [ ] **Digital Signing**: How do you sign invoices?
  - **Recommended Answer**: "We use XML Digital Signature (XMLDSig) with RSA-SHA256 algorithm. XML is canonicalized (C14N) before signing. We use CSID certificates obtained from ZATCA for production signing. Certificates are stored securely per-tenant with proper isolation."

- [ ] **Clearance Process**: How do you submit invoices for clearance?
  - **Recommended Answer**: "We submit signed XML invoices to ZATCA clearance API endpoint. We handle CLEARED and REJECTED responses, store clearance status, and use ZATCA-provided QR codes when available. We implement retry logic with exponential backoff for network errors."

- [ ] **Error Handling**: How do you handle errors?
  - **Recommended Answer**: "We implement comprehensive error handling for validation errors, ZATCA API errors, network timeouts, and system errors. All errors are logged with context (tenant_id, invoice_number, error_type) and return structured error responses with bilingual messages (English and Arabic)."

- [ ] **Data Security**: How do you secure invoice data?
  - **Recommended Answer**: "We implement tenant isolation at database and file system levels. Certificates are stored with secure file permissions (600). API access is secured with API key authentication. All sensitive data is encrypted in transit (HTTPS) and at rest (database encryption)."

- [ ] **Audit Trail**: How do you maintain audit trails?
  - **Recommended Answer**: "We maintain immutable audit logs for all invoice submissions. Each invoice is stored in database with full metadata (UUID, hash, clearance status, ZATCA response). We also maintain append-only audit files for compliance. All audit records are tenant-scoped and timestamped."

### Testing Evidence

- [ ] **Sandbox Testing**: Evidence of successful sandbox testing
  - [ ] Test invoice samples (Phase-1 and Phase-2)
  - [ ] Clearance success examples
  - [ ] Error handling examples

- [ ] **Compliance Testing**: Evidence of compliance testing
  - [ ] XML validation results
  - [ ] Signature verification results
  - [ ] UBL schema validation results

---

## 4. What Environment They Test (Sandbox)

### ZATCA Testing Process

1. **Sandbox Access**: ZATCA will provide sandbox credentials
   - Sandbox API URL: `https://gw-apic-gov.gazt.gov.sa/e-invoicing/developer-portal`
   - Sandbox API credentials (if required)

2. **Test Scenarios**: ZATCA will test:
   - [ ] Phase-1 invoice creation
   - [ ] Phase-2 invoice creation and clearance
   - [ ] XML structure validation
   - [ ] Digital signature verification
   - [ ] Error handling
   - [ ] Clearance status handling

3. **Test Duration**: Typically 1-2 weeks for sandbox testing

4. **Test Results**: ZATCA will provide feedback on:
   - Compliance issues (if any)
   - Required fixes
   - Approval status

---

## 5. How Long Approval Typically Takes

### Timeline Expectations

- **Initial Application Review**: 1-2 weeks
- **Sandbox Testing**: 1-2 weeks
- **Compliance Review**: 1-2 weeks
- **Final Approval**: 1 week
- **Total Timeline**: **4-8 weeks** (typical)

### Factors Affecting Timeline

- **Application Completeness**: Complete applications are processed faster
- **Compliance Issues**: Any compliance issues will delay approval
- **ZATCA Workload**: Approval times may vary based on ZATCA workload
- **Response Time**: Faster responses to ZATCA queries speed up process

---

## 6. Common Rejection Reasons

### Technical Rejection Reasons

1. **XML Structure Issues**
   - Missing mandatory UBL elements
   - Incorrect namespace declarations
   - Invalid XML format
   - **Prevention**: Validate XML against UBL schema before submission

2. **Digital Signature Issues**
   - Invalid signature algorithm
   - Incorrect canonicalization
   - Invalid certificate
   - **Prevention**: Use proper XMLDSig implementation, validate certificates

3. **Clearance Submission Issues**
   - Incorrect API endpoint
   - Missing required fields
   - Invalid request format
   - **Prevention**: Follow ZATCA API documentation exactly

4. **Error Handling Issues**
   - No error handling for ZATCA API failures
   - No retry logic for network errors
   - **Prevention**: Implement comprehensive error handling and retry logic

### Compliance Rejection Reasons

1. **Missing Audit Trail**
   - No invoice persistence
   - No audit logging
   - **Prevention**: Implement full audit trail with immutable logs

2. **Security Issues**
   - No tenant isolation
   - Insecure certificate storage
   - **Prevention**: Implement proper security measures (tenant isolation, secure storage)

3. **Data Validation Issues**
   - No validation of invoice data
   - Incorrect VAT calculations
   - **Prevention**: Implement comprehensive validation before processing

---

# STEP 4: QUESTIONS ZATCA MAY ASK

## Typical Technical Questions

### Q1: How do you ensure invoice uniqueness?

**Recommended Answer**: "We enforce invoice uniqueness at the database level using a unique constraint on `(tenant_id, invoice_number)`. This ensures that the same invoice number cannot be submitted twice for the same tenant. We also implement idempotency checks before processing to return existing invoices if duplicates are detected."

**Evidence**: Show database schema with unique constraint, idempotency code.

---

### Q2: How do you handle ZATCA API failures?

**Recommended Answer**: "We implement comprehensive error handling for ZATCA API failures. We use retry logic with exponential backoff (3 retries) for transient errors (timeouts, 502, 504). For permanent errors (400, 401, 403), we return structured error responses to the client. All errors are logged with full context (tenant_id, invoice_number, error_type, ZATCA response) for troubleshooting."

**Evidence**: Show error handling code, retry logic implementation.

---

### Q3: How do you validate invoice data before submission?

**Recommended Answer**: "We implement phase-specific validators that check all mandatory fields, VAT calculations, tax number formats, and business rules before processing. Phase-1 validator checks QR code eligibility, VAT rate (15%), and total consistency. Phase-2 validator checks UUID presence, certificate availability, and XML generation prerequisites. Validation errors are returned immediately without ZATCA submission."

**Evidence**: Show validator code, validation test results.

---

### Q4: How do you store and manage CSID certificates?

**Recommended Answer**: "We store certificates securely per-tenant in isolated directories (certs/tenant_{id}/{environment}/). Certificates are stored with secure file permissions (600: owner read/write only). We validate certificate format and expiry on upload, extract metadata (serial, issuer, expiry) and store it in database. Only one active certificate per tenant per environment is allowed. We support certificate rotation by deactivating old certificates when new ones are uploaded."

**Evidence**: Show certificate service code, certificate storage structure.

---

### Q5: How do you generate and sign UBL XML?

**Recommended Answer**: "We generate UBL 2.1 compliant XML using the standard Invoice schema. XML is generated server-side from invoice request data, ensuring all mandatory elements are included. Before signing, we validate that XML is fully rendered (no template variables). We then canonicalize the XML (C14N), compute SHA-256 hash, and sign with RSA-SHA256 using the tenant's CSID certificate. The signed XML is embedded with XMLDSig signature element."

**Evidence**: Show XML generator code, signing code, sample XML files.

---

## Compliance Questions

### Q6: How do you ensure data integrity and auditability?

**Recommended Answer**: "We maintain immutable audit trails for all invoice submissions. Each invoice is persisted in database with full metadata (UUID, hash, clearance status, ZATCA response, timestamps). We also maintain append-only audit files (JSONL format) that cannot be modified. All audit records are tenant-scoped and timestamped. Invoice status lifecycle is tracked (CREATED → PROCESSING → CLEARED/REJECTED/FAILED)."

**Evidence**: Show audit service code, database schema, audit file samples.

---

### Q7: How do you handle multi-tenant data isolation?

**Recommended Answer**: "We implement strict tenant isolation at multiple levels. Database records are tenant-scoped (tenant_id foreign key). Certificates are stored in tenant-specific directories. API requests are authenticated with tenant-specific API keys. All queries filter by tenant_id to prevent cross-tenant data access. File system operations use tenant-specific paths."

**Evidence**: Show tenant isolation code, database queries, certificate paths.

---

### Q8: How do you ensure invoice data is not lost or corrupted?

**Recommended Answer**: "We implement idempotent invoice processing. Invoices are persisted in database BEFORE ZATCA submission, ensuring data is never lost even if ZATCA submission fails. We store original request payload, generated XML, and ZATCA response for full traceability. Database transactions ensure atomicity. We also implement data retention policies with configurable retention periods."

**Evidence**: Show persistence code, database transaction handling, retention policy.

---

## Security Questions

### Q9: How do you secure API access?

**Recommended Answer**: "We use API key authentication for all API endpoints. API keys are validated on every request and mapped to tenant context. We implement rate limiting per tenant to prevent abuse. Internal endpoints require additional secret key authentication. All API communication uses HTTPS (TLS 1.2+). We never log API keys or sensitive data."

**Evidence**: Show authentication middleware, rate limiting code.

---

### Q10: How do you protect certificate private keys?

**Recommended Answer**: "Private keys are stored in tenant-specific directories with secure file permissions (600: owner read/write only). Private keys are never logged or exposed in API responses. Keys are only accessed during signing operations and are never transmitted over the network. We recommend customers use secure key management practices and rotate certificates regularly."

**Evidence**: Show certificate storage code, file permissions, security documentation.

---

### Q11: How do you handle production vs sandbox environments?

**Recommended Answer**: "We support separate environments (SANDBOX and PRODUCTION) with environment-specific configuration. Each tenant can have different environments. Certificates are stored per-environment. Production access is restricted to paid plans only and requires explicit confirmation (`confirm_production=true`). Sandbox uses placeholder signatures for faster testing, while production uses real cryptographic signing."

**Evidence**: Show environment configuration, production access guards, certificate paths.

---

# STEP 5: FINAL RECOMMENDATIONS

## Are We Ready to Apply Now?

### ✅ **YES - You Are Ready to Apply**

Based on the codebase analysis, FATURAIX has all the **mandatory** ZATCA compliance requirements implemented:

1. ✅ **Phase-1 Compliance**: Full Phase-1 invoice processing with QR code generation
2. ✅ **Phase-2 Compliance**: UBL XML generation, digital signing, clearance submission
3. ✅ **Cryptography**: XMLDSig signing with RSA-SHA256, CSID certificate support
4. ✅ **XML/UBL**: UBL 2.1 compliant XML generation
5. ✅ **Error Handling**: Comprehensive error handling with retry logic
6. ✅ **Audit Trail**: Immutable audit logs, invoice persistence, full traceability
7. ✅ **Sandbox/Production**: Environment separation, production guards

### What You Should Complete Before Applying

#### 1. Sandbox Testing (MANDATORY)

- [ ] **Test Phase-1 Flow**: Create and process 5-10 Phase-1 invoices in sandbox
- [ ] **Test Phase-2 Flow**: Create and process 5-10 Phase-2 invoices in sandbox
- [ ] **Test Clearance**: Verify clearance submission and status handling
- [ ] **Test Error Scenarios**: Test validation errors, ZATCA API errors, network failures
- [ ] **Test Certificate Upload**: Upload test certificates and verify signing works
- [ ] **Test Idempotency**: Verify duplicate invoice prevention works

**Timeline**: 1-2 weeks of thorough testing

#### 2. Documentation Preparation (MANDATORY)

- [ ] **API Documentation**: Complete API documentation (Swagger/OpenAPI)
- [ ] **Integration Guide**: Step-by-step integration guide for customers
- [ ] **Certificate Setup Guide**: Guide for uploading and managing certificates
- [ ] **Error Handling Guide**: Documentation of error codes and handling
- [ ] **Test Evidence**: Collect test invoice samples, XML samples, API responses

**Timeline**: 1 week

#### 3. Production Configuration (MANDATORY)

- [ ] **Environment Variables**: Set all production environment variables
- [ ] **Database Setup**: Production database configured and migrated
- [ ] **Certificate Management**: Process for customers to upload production certificates
- [ ] **Monitoring Setup**: Logging, monitoring, alerting configured
- [ ] **Backup Strategy**: Database backup strategy in place

**Timeline**: 1 week

#### 4. Support Preparation (RECOMMENDED)

- [ ] **Support Process**: Define support process for ZATCA-related issues
- [ ] **Escalation Path**: Define escalation path for critical issues
- [ ] **Customer Communication**: Prepare communication templates for ZATCA-related updates

**Timeline**: 1 week

---

## What NOT to Worry About (Things ZATCA Does Not Check)

### ❌ Things ZATCA Does NOT Verify

1. **UI/UX Design**: ZATCA does not check your user interface or user experience
2. **Marketing Materials**: ZATCA does not review marketing content or website design
3. **Pricing Model**: ZATCA does not care about your pricing or subscription plans
4. **Business Model**: ZATCA does not verify your business model or revenue streams
5. **Third-Party Integrations**: ZATCA does not check integrations with other services (unless they affect ZATCA compliance)
6. **AI Features**: ZATCA does not verify AI/ML features (unless they affect invoice generation)
7. **Reporting Features**: ZATCA does not check reporting or analytics features
8. **Multi-Language Support**: ZATCA does not require multi-language support (though Arabic error messages are recommended)

### ✅ Things ZATCA DOES Verify

1. **Technical Compliance**: UBL XML structure, digital signatures, clearance submission
2. **Security**: Certificate management, data isolation, API security
3. **Error Handling**: Proper error handling for ZATCA API failures
4. **Audit Trail**: Invoice persistence, audit logging, traceability
5. **Testing**: Evidence of successful sandbox testing

---

## Application Readiness Summary

### Ready to Apply: ✅ YES

**Confidence Level**: **HIGH**

Your FATURAIX product has all mandatory ZATCA compliance requirements implemented. You should proceed with:

1. **Complete sandbox testing** (1-2 weeks)
2. **Prepare documentation** (1 week)
3. **Configure production environment** (1 week)
4. **Submit application to ZATCA** (4-8 weeks approval timeline)

### Estimated Timeline to Application Submission

- **Sandbox Testing**: 1-2 weeks
- **Documentation**: 1 week
- **Production Setup**: 1 week
- **Total**: **3-4 weeks** before application submission

### Estimated Total Timeline to Approval

- **Preparation**: 3-4 weeks
- **ZATCA Approval**: 4-8 weeks
- **Total**: **7-12 weeks** from now to full approval

---

## Next Steps

1. **Immediate Actions**:
   - [ ] Start comprehensive sandbox testing
   - [ ] Collect test evidence (invoices, XML, responses)
   - [ ] Prepare application documents

2. **This Week**:
   - [ ] Complete sandbox testing checklist
   - [ ] Document all test results
   - [ ] Prepare technical documentation

3. **Next Week**:
   - [ ] Finalize production configuration
   - [ ] Prepare application submission
   - [ ] Submit application to ZATCA

4. **Ongoing**:
   - [ ] Monitor ZATCA communication
   - [ ] Respond promptly to ZATCA queries
   - [ ] Address any compliance issues immediately

---

**Last Updated**: 2025-01-17  
**Document Version**: 1.0  
**Prepared For**: FATURAIX ZATCA Compliance Approval

