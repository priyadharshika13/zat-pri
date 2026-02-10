# AI Data Isolation

## Tenant Isolation

All AI operations are scoped to a single tenant. No cross-tenant data access is possible.

## Data Flow Isolation

### Request Isolation

**Tenant Context Required:**
- All AI API endpoints require authentication
- Tenant context resolved from API key
- Tenant context propagated to AI services

**Service-Level Isolation:**
- AI services receive tenant context
- All queries filter by tenant_id
- No cross-tenant data in AI prompts

### Response Isolation

**Tenant-Scoped Responses:**
- AI responses are tenant-specific
- No tenant data in responses
- Responses cannot access other tenants' data

## Data Storage Isolation

### No Invoice Data Storage

**AI Services:**
- Do not store invoice data
- Do not maintain invoice databases
- Only process data in-memory during request

**OpenRouter:**
- Receives invoice data for processing
- Does not store data (per API contract)
- Data not used for training (per API contract)

### Usage Tracking

**Token Usage:**
- Tracked per tenant
- Stored in database (tenant_id scoped)
- Used for subscription billing
- No invoice data in usage records

## Privacy and Security

### Data Transmission

**To OpenRouter:**
- Invoice data sent via HTTPS
- Encrypted in transit
- No persistent storage by OpenRouter

**From OpenRouter:**
- AI responses received via HTTPS
- Encrypted in transit
- Responses not stored by AI services

### Data Masking

**Logging:**
- Sensitive fields masked in logs
- PII not logged
- AI prompts not logged with full data

**Error Handling:**
- Error messages sanitized
- No tenant data in error logs
- Stack traces do not include invoice data

## Prompt Construction

### Tenant-Scoped Prompts

**Error Explanation:**
- Error code and message only
- No invoice data in prompt
- Tenant context implicit (not in prompt)

**Rejection Prediction:**
- Invoice payload included in prompt
- Tenant context not included
- Prompt scoped to single invoice

**Root Cause Analysis:**
- Historical invoice data (tenant-scoped)
- No cross-tenant data
- Tenant context implicit

### Data Minimization

**Minimal Data in Prompts:**
- Only necessary fields included
- Sensitive data excluded when possible
- Structured data format (JSON)

**Prompt Templates:**
- Reusable templates
- No hardcoded tenant data
- Tenant data injected at runtime

## Database Isolation

### AI Usage Records

**Table:** Subscription usage tracking

**Isolation:**
- All records include tenant_id
- Queries filter by tenant_id
- No cross-tenant queries possible

**Data Stored:**
- Token usage counts
- API call timestamps
- No invoice data

### Audit Logs

**Table:** InvoiceLog

**Isolation:**
- All records include tenant_id
- Queries filter by tenant_id
- AI operations logged per tenant

**Data Stored:**
- Request/response metadata
- No full invoice data in logs
- Sensitive fields masked

## API-Level Isolation

### Endpoint Protection

**Authentication Required:**
- All AI endpoints require API key
- API key maps to single tenant
- No anonymous AI access

**Authorization:**
- Tenant context verified
- Subscription limits enforced
- Rate limits per tenant

### Response Filtering

**Tenant-Scoped Results:**
- All AI responses filtered by tenant
- No cross-tenant data in responses
- Responses include only tenant's data

## Current Implementation Status

All data isolation mechanisms are implemented:

- Tenant isolation in all AI operations
- No invoice data storage by AI services
- Usage tracking per tenant
- Data masking in logs
- API-level tenant verification

Future considerations (not currently implemented):

- Data encryption at rest for AI usage records
- Advanced data masking for sensitive fields
- Audit logging for AI data access
- Compliance certifications for data handling

