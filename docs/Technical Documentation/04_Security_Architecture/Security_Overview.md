# Security Overview

## Security Architecture

The system implements multiple layers of security controls to protect tenant data, API access, and compliance operations.

## Authentication

**API Key Authentication:**
- All API endpoints require `X-API-Key` header
- API keys stored in database (hashed, not plaintext)
- API key maps to single tenant
- Inactive API keys rejected

**Tenant Resolution:**
- API key validated against database
- Tenant context resolved from API key
- Inactive tenants rejected
- Tenant context attached to request state

## Authorization

**Tenant Isolation:**
- All database queries filter by tenant_id
- Cross-tenant access prevented at database level
- Certificate access restricted to tenant
- Invoice access restricted to tenant

**Subscription Limits:**
- Per-plan rate limits enforced
- Invoice limits enforced before processing
- Usage tracked per tenant
- Limits checked before resource consumption

**Production Access:**
- Production environment requires paid plan
- Explicit confirmation required for Production submissions
- Sandbox environment available to all plans

## Data Protection

**Encryption in Transit:**
- HTTPS required for all API communication
- TLS 1.2+ enforced
- Certificate validation required

**Encryption at Rest:**
- Database connections use SSL/TLS
- Certificate files stored with restricted permissions (600)
- Private keys never stored in database

**Data Masking:**
- Sensitive fields masked in logs
- PII excluded from audit logs
- Invoice data not stored in AI systems

## Security Headers

**HTTP Security Headers:**
- Content-Security-Policy (CSP)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- Strict-Transport-Security (HSTS) in production
- X-XSS-Protection: 1; mode=block
- Permissions-Policy

**Implementation:**
- SecurityHeadersMiddleware injects headers
- Applied to all responses
- Configurable per environment

## Rate Limiting

**Per-Tenant Rate Limits:**
- Token bucket algorithm
- Limits based on subscription plan
- 429 Too Many Requests on limit exceeded
- Rate limit headers in response

**Implementation:**
- RateLimitMiddleware enforces limits
- In-memory token buckets (per tenant)
- Limits retrieved from subscription service

## Input Validation

**Schema Validation:**
- Pydantic models validate all inputs
- Type checking and value validation
- Required field enforcement
- Format validation (dates, numbers, strings)

**Business Logic Validation:**
- Phase-specific validators
- ZATCA specification compliance
- VAT calculation validation
- Certificate format validation

## Error Handling

**Error Response Security:**
- Generic error messages for clients
- Detailed errors logged server-side
- No stack traces in production responses
- Error codes mapped to safe messages

**Exception Handling:**
- Global exception handler
- Errors logged with context
- No sensitive data in error responses
- Graceful degradation on errors

## Audit Logging

**Request Logging:**
- All API requests logged
- Request method, path, client IP
- Response status, processing time
- Tenant context included

**Invoice Logging:**
- InvoiceLog entries for all processing attempts
- Request payload, generated XML, ZATCA response
- Status changes tracked
- Retry operations logged

**Security Events:**
- Failed authentication attempts
- Rate limit violations
- Invalid API key usage
- Cross-tenant access attempts

## Certificate Security

**Storage:**
- Certificates stored in tenant-specific directories
- File permissions: 600 (owner read/write only)
- Private keys never in database
- Certificate metadata only in database

**Validation:**
- Certificate format validation
- Expiry date checking
- Private key format validation
- Cryptographic certificate-private key verification
- Certificate activation/deactivation

**Access Control:**
- Tenant isolation enforced
- Path validation prevents cross-tenant access
- Certificate access requires tenant context

## Current Implementation Status

All security components are implemented:

- API key authentication
- Tenant isolation
- Security headers
- Rate limiting
- Input validation
- Error handling
- Audit logging
- Certificate security
- Cryptographic certificate-private key verification
- Production CSID Onboarding (OTP-based flow)
- Environment and invoice-type policy enforcement

Future considerations (not currently implemented):

- API key rotation
- OAuth 2.0 support
- Multi-factor authentication
- IP whitelisting
- Advanced threat detection
- Security event monitoring

