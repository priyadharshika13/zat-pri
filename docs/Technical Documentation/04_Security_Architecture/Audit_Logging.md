# Audit Logging

## Audit Log Architecture

The system maintains comprehensive audit logs for compliance, security, and operational monitoring.

## Log Types

### Request Audit Logs

**Location:** Application logs (stdout/stderr)

**Content:**
- Request method and path
- Client IP address
- Request timestamp
- Response status code
- Processing time
- Tenant context (implicit)

**Format:** JSON (structured logging)

**Retention:** Configurable (default: 30 days)

### Invoice Logs

**Location:** Database (`invoice_logs` table)

**Content:**
- Invoice number and UUID
- Request payload (full invoice data)
- Generated XML (Phase-2)
- ZATCA response
- Processing status
- Timestamps (submitted_at, cleared_at)
- Action type (RETRY, etc.)

**Retention:** Configurable (default: 180 days)

**Anonymization:** Configurable (data masking or purging)

### Security Event Logs

**Location:** Application logs

**Content:**
- Failed authentication attempts
- Invalid API key usage
- Rate limit violations
- Cross-tenant access attempts
- Certificate access events

**Format:** JSON with security event markers

**Retention:** Extended retention for security events

## Logging Implementation

### Request Logging

**Middleware:** AuditMiddleware

**Process:**
1. Request received, start time recorded
2. Request method, path, client IP logged
3. Request processed
4. Response status, processing time logged
5. Log entry written

**Fields:**
- `timestamp`: Request timestamp
- `method`: HTTP method
- `path`: Request path
- `client_ip`: Client IP address
- `status_code`: HTTP status code
- `process_time`: Processing time in seconds

### Invoice Logging

**Service:** InvoiceLogService

**Process:**
1. Invoice processing starts
2. InvoiceLog entry created with status SUBMITTED
3. Request payload stored
4. Processing completes
5. InvoiceLog updated with results
6. Status updated (CLEARED, REJECTED, ERROR)

**Fields:**
- `invoice_number`: Invoice identifier
- `uuid`: Invoice UUID (Phase-2)
- `hash`: XML hash (Phase-2)
- `environment`: SANDBOX or PRODUCTION
- `status`: Processing status
- `request_payload`: Full invoice request
- `generated_xml`: Generated XML (Phase-2)
- `zatca_response`: ZATCA API response
- `submitted_at`: Submission timestamp
- `cleared_at`: Clearance timestamp (if cleared)
- `action`: Action type (RETRY, etc.)

### Security Event Logging

**Location:** Application logs with security markers

**Events:**
- Authentication failures
- Invalid API key attempts
- Rate limit violations
- Cross-tenant access attempts
- Certificate access violations

**Fields:**
- `event_type`: Security event type
- `timestamp`: Event timestamp
- `tenant_id`: Tenant context (if available)
- `client_ip`: Client IP address
- `details`: Event-specific details

## Data Masking

### Sensitive Data Masking

**Fields Masked:**
- Private keys (never logged)
- Certificate content (metadata only)
- API keys (hashed representation)
- PII in invoice data (configurable)

**Implementation:**
- `mask_sensitive_fields()` utility function
- Applied before log storage
- Configurable masking rules
- Reversible masking (future)

### Invoice Data Masking

**Request Payload:**
- Full payload stored in InvoiceLog
- Sensitive fields can be masked (configurable)
- Masking applied before storage
- Original data not recoverable after masking

**ZATCA Response:**
- Full response stored
- Error codes preserved
- Sensitive data excluded (if any)

## Log Retention

### Retention Policy

**Configuration:**
- `RETENTION_DAYS`: Retention period (default: 180 days)
- `RETENTION_CLEANUP_MODE`: anonymize or purge

**Application:**
- InvoiceLog entries older than retention period
- Cleanup job runs periodically (future)
- Anonymization or purging based on mode

### Anonymization

**Process:**
- Invoice data anonymized
- Invoice numbers replaced with hashes
- PII removed
- Structure preserved for analytics

**Purging:**
- Complete data removal
- No trace of invoice data
- Metadata may be retained (counts, statistics)

## Log Access

### API Access

**Endpoints:**
- `GET /api/v1/invoices/{id}`: Invoice details with logs
- `GET /api/v1/invoices/{invoice_number}/status`: Status with history
- Invoice history includes log entries

**Access Control:**
- Tenant isolation enforced
- Only tenant's own logs accessible
- Cross-tenant access returns 404

### Database Access

**Direct Access:**
- Database access restricted to application
- No direct database access for tenants
- Admin access for system operations
- Read-only access for reporting (future)

## Compliance

### ZATCA Compliance

**Requirements:**
- Full audit trail for all invoices
- Request/response preservation
- Status change tracking
- Retry operation logging

**Implementation:**
- InvoiceLog entries for all operations
- Immutable log entries (append-only)
- Full request/response storage
- Status lifecycle tracking

### Data Privacy

**Requirements:**
- PII protection
- Data minimization
- Retention limits
- Right to deletion (future)

**Implementation:**
- Data masking in logs
- Retention policy enforcement
- Anonymization support
- Tenant data isolation

## Current Implementation Status

All audit logging components are implemented:

- Request audit logging
- Invoice log storage
- Security event logging
- Data masking
- Retention policy configuration

Future considerations (not currently implemented):

- Automated cleanup jobs
- Advanced anonymization
- Log encryption
- Centralized log aggregation
- Real-time security monitoring
- Compliance reporting automation

