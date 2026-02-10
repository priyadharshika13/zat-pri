# Data Boundaries

## Data Scoping

All data in the system is scoped to tenants with strict boundaries preventing cross-tenant access.

## Database Boundaries

### Table Structure

**Tenant ID Column:**
- All data tables include `tenant_id` column
- Foreign key to `tenants` table
- Required (NOT NULL constraint)
- Indexed for performance

**Unique Constraints:**
- Scoped to tenant (e.g., `(tenant_id, invoice_number)`)
- Prevents duplicates within tenant
- Allows same values across tenants
- Database enforces constraint

### Query Boundaries

**Automatic Filtering:**
- All queries include `tenant_id` filter
- Tenant context required for queries
- No queries without tenant filter
- Database constraints prevent violations

**Example Queries:**
```sql
SELECT * FROM invoices WHERE tenant_id = ? AND invoice_number = ?
SELECT * FROM invoice_logs WHERE tenant_id = ? AND status = ?
SELECT * FROM certificates WHERE tenant_id = ? AND environment = ?
```

## Application Boundaries

### Service Layer

**Tenant Context Required:**
- All service methods require tenant context
- Services validate tenant context
- Database operations include tenant filter
- No cross-tenant operations possible

**Service Initialization:**
- Services receive tenant context in constructor
- Tenant context stored as instance variable
- All operations use stored tenant context
- No service can access cross-tenant data

### Route Handlers

**Dependency Injection:**
- `verify_api_key_and_resolve_tenant()` dependency
- Tenant context injected into handlers
- Handlers cannot proceed without tenant context
- All handlers receive tenant context

**Handler Execution:**
- Tenant context available in handler
- Handler passes tenant context to services
- Services use tenant context for operations
- No cross-tenant data access possible

## File System Boundaries

### Certificate Storage

**Directory Structure:**
- `certs/tenant_{tenant_id}/{environment}/`
- Tenant-specific directories
- Environment subdirectories
- Path validation enforces isolation

**Path Validation:**
- Paths resolved per tenant
- Tenant ID validated in path
- Cross-tenant path access prevented
- Directory permissions enforce isolation

### Log Storage

**Log Files:**
- Application logs: Shared (tenant context in log entries)
- Invoice logs: Database (tenant_id column)
- Audit logs: Database (tenant_id column)
- Certificate logs: Database (tenant_id column)

## Data Access Patterns

### Invoice Access

**Lookup by ID:**
- Invoice ID lookup includes tenant filter
- Cross-tenant access returns 404
- Tenant context validated
- No invoice data without tenant match

**Lookup by Number:**
- Invoice number lookup includes tenant filter
- Same invoice number can exist for different tenants
- Tenant context required
- No cross-tenant access

### Certificate Access

**Certificate Retrieval:**
- Certificate paths resolved per tenant
- Path validation checks tenant_id
- Certificate files not accessible via API
- Only tenant's own certificates accessible

**Certificate Metadata:**
- Certificate queries filter by tenant_id
- Cross-tenant access prevented
- Tenant context required
- No certificate data without tenant match

### Report Access

**Report Generation:**
- All reports filter by tenant
- No cross-tenant data in reports
- Tenant context required
- Aggregations scoped to tenant

## Boundary Enforcement

### Database Constraints

**Foreign Keys:**
- All tenant_id columns reference tenants table
- Database enforces referential integrity
- Cannot create data without valid tenant
- Cascade rules prevent orphaned data

**Unique Constraints:**
- Scoped to tenant (e.g., `(tenant_id, invoice_number)`)
- Database enforces uniqueness within tenant
- Same values allowed across tenants
- Prevents duplicates within tenant

### Application Validation

**Tenant Context Validation:**
- Tenant context validated in all operations
- Invalid tenant context rejected
- Missing tenant context rejected
- Cross-tenant access attempts logged

**Path Validation:**
- Certificate paths validated per tenant
- Tenant ID checked in path resolution
- Invalid paths rejected
- Cross-tenant path access prevented

## Current Implementation Status

All data boundary components are implemented:

- Database-level boundaries
- Application-level boundaries
- File system-level boundaries
- Query filtering
- Path validation
- Constraint enforcement

Future considerations (not currently implemented):

- Cross-tenant analytics (aggregated, anonymized)
- Data export with tenant boundaries
- Data deletion with tenant boundaries
- Tenant data migration
- Cross-tenant data sharing (with explicit permissions)

