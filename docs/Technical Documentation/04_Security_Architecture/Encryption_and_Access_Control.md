# Encryption and Access Control

## Encryption

### Encryption in Transit

**HTTPS/TLS:**
- All API communication over HTTPS
- TLS 1.2+ required
- Certificate validation enforced
- HSTS header in production

**ZATCA API Communication:**
- HTTPS connections to ZATCA APIs
- Certificate validation required
- Timeout and retry handling
- Error handling for connection failures

**AI Service Communication:**
- HTTPS connections to OpenRouter
- API key authentication
- Request timeout handling
- Error handling for service failures

### Encryption at Rest

**Database:**
- PostgreSQL connections use SSL/TLS
- Connection string includes SSL parameters
- Database credentials encrypted in configuration
- Backup encryption (database-level)

**Certificate Files:**
- Stored on filesystem with restricted permissions
- Not encrypted at rest (filesystem-level encryption recommended)
- Private keys never in database
- Certificate metadata in database (non-sensitive)

**Logs:**
- Log files stored on filesystem
- Sensitive data masked in logs
- Log rotation and retention policies
- Log encryption (filesystem-level recommended)

## Access Control

### API Key Authentication

**API Key Format:**
- Alphanumeric strings
- Stored in database (hashed, not plaintext)
- Unique per tenant
- Can be activated/deactivated

**Authentication Flow:**
1. API key extracted from `X-API-Key` header
2. API key validated against database
3. Tenant resolved from API key
4. Tenant context attached to request
5. Request proceeds if valid

**Invalid API Key:**
- 401 Unauthorized response
- Error logged (without exposing key)
- No tenant context attached
- Request rejected

### Tenant Isolation

**Database Level:**
- All tables include `tenant_id` column
- All queries filter by `tenant_id`
- Foreign key constraints enforce isolation
- Unique constraints scoped to tenant

**Application Level:**
- Tenant context required for all operations
- Tenant context resolved early in request
- Services receive tenant context
- No cross-tenant data access possible

**File System Level:**
- Certificates in tenant-specific directories
- Path validation prevents cross-tenant access
- Directory permissions enforce isolation
- File permissions restrict access

### Subscription-Based Access Control

**Plan Limits:**
- Rate limits per plan
- Invoice limits per plan
- AI usage limits per plan
- Production access per plan

**Enforcement:**
- Limits checked before resource consumption
- 403 Forbidden on limit exceeded
- 429 Too Many Requests on rate limit
- Usage tracked per tenant

**Production Access:**
- Production environment requires paid plan
- Explicit confirmation required
- Sandbox available to all plans
- Access validated before processing

## Role-Based Access (Future)

**Planned Roles:**
- Admin: Full system access
- Tenant Admin: Tenant management
- User: Standard API access
- Read-Only: Read-only access

**Implementation:**
- Role assignment per API key
- Permission checks per endpoint
- Role hierarchy
- Audit logging for role changes

## Data Access Control

### Invoice Access

**Tenant Scoping:**
- Invoices belong to single tenant
- Queries filter by tenant_id
- Cross-tenant access returns 404
- Invoice ID validation includes tenant check

### Certificate Access

**Tenant Scoping:**
- Certificates belong to single tenant
- Path validation enforces isolation
- Certificate metadata filtered by tenant
- Cross-tenant access prevented

### Report Access

**Tenant Scoping:**
- All reports filtered by tenant
- No cross-tenant data in reports
- Tenant context required
- Aggregations scoped to tenant

## Audit and Monitoring

**Access Logging:**
- All API requests logged
- Authentication attempts logged
- Failed access attempts logged
- Tenant context in all logs

**Security Events:**
- Invalid API key usage
- Rate limit violations
- Cross-tenant access attempts
- Certificate access events

**Monitoring:**
- Failed authentication rate
- Rate limit violations
- Unusual access patterns
- Security event alerts (future)

## Current Implementation Status

All encryption and access control components are implemented:

- HTTPS/TLS for all communication
- API key authentication
- Tenant isolation
- Subscription-based access control
- Audit logging

Future considerations (not currently implemented):

- Database encryption at rest
- Log encryption
- Role-based access control
- Advanced monitoring and alerting
- IP whitelisting
- Multi-factor authentication

