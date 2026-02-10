# Tenant Isolation Model

## Multi-Tenancy Architecture

The system implements strict tenant isolation at multiple layers to ensure complete data separation between tenants.

## Tenant Model

**Database Entity:** `tenants` table

**Fields:**
- `id`: Primary key
- `company_name`: Company name
- `vat_number`: VAT registration number (unique)
- `environment`: SANDBOX or PRODUCTION
- `is_active`: Active status flag
- `created_at`: Creation timestamp

**Isolation:**
- Each tenant is completely isolated
- No shared data between tenants
- Tenant ID used for all data scoping

## API Key to Tenant Mapping

**Database Entity:** `api_keys` table

**Relationship:**
- Each API key belongs to one tenant
- Foreign key: `tenant_id`
- API key used for authentication
- Tenant context resolved from API key

**Authentication Flow:**
1. API key extracted from request header
2. API key validated against database
3. Tenant resolved from API key
4. Tenant context created and attached to request
5. All subsequent operations use tenant context

## Data Isolation

### Database Level

**Tenant ID Column:**
- All data tables include `tenant_id` column
- Foreign key to `tenants` table
- Indexed for performance
- Required (NOT NULL)

**Query Filtering:**
- All queries filter by `tenant_id`
- Tenant context required for all operations
- No cross-tenant queries possible
- Database constraints enforce isolation

**Unique Constraints:**
- Scoped to tenant (e.g., `(tenant_id, invoice_number)`)
- Prevents duplicates within tenant
- Allows same values across tenants

### Application Level

**Tenant Context:**
- Resolved early in request pipeline
- Attached to request state
- Propagated to all services
- Required for all database operations

**Service Layer:**
- All services receive tenant context
- Services filter queries by tenant_id
- No service can access cross-tenant data
- Tenant context validated in all operations

### File System Level

**Certificate Storage:**
- Certificates in tenant-specific directories
- Path: `certs/tenant_{tenant_id}/{environment}/`
- Path validation prevents cross-tenant access
- Directory permissions enforce isolation

## Isolation Enforcement Points

### Authentication

**API Key Validation:**
- API key must exist and be active
- Tenant must exist and be active
- Inactive API key or tenant rejected
- No tenant context if validation fails

### Route Handlers

**Dependency Injection:**
- `verify_api_key_and_resolve_tenant()` dependency
- Tenant context injected into handlers
- Handlers cannot proceed without tenant context
- All handlers receive tenant context

### Service Layer

**Tenant Context Required:**
- All service methods require tenant context
- Services validate tenant context
- Database queries include tenant filter
- No cross-tenant operations possible

### Database Queries

**Automatic Filtering:**
- All queries include `tenant_id` filter
- Tenant context used in WHERE clauses
- No queries without tenant filter
- Database constraints prevent violations

## Certificate Isolation

**Storage:**
- Certificates in tenant-specific directories
- Path validation enforces isolation
- Certificate metadata filtered by tenant_id
- No cross-tenant certificate access

**Access:**
- Certificate paths resolved per tenant
- Path validation checks tenant_id
- Certificate files not accessible via API
- Only tenant's own certificates accessible

## Invoice Isolation

**Storage:**
- Invoices include `tenant_id` column
- All queries filter by tenant_id
- Unique constraint: `(tenant_id, invoice_number)`
- No cross-tenant invoice access

**Access:**
- Invoice lookups include tenant filter
- Invoice ID validation includes tenant check
- Cross-tenant access returns 404
- Invoice history scoped to tenant

## Subscription Isolation

**Storage:**
- Subscriptions include `tenant_id` column
- Usage tracked per tenant
- Limits enforced per tenant
- No cross-tenant usage sharing

**Access:**
- Subscription data filtered by tenant
- Usage metrics per tenant
- Limits checked per tenant
- No cross-tenant limit sharing

## Current Implementation Status

All tenant isolation components are implemented:

- Database-level isolation
- Application-level isolation
- File system-level isolation
- Certificate isolation
- Invoice isolation
- Subscription isolation

Future considerations (not currently implemented):

- Cross-tenant analytics (aggregated, anonymized)
- Tenant hierarchy (parent-child relationships)
- Shared resources (with explicit permissions)
- Tenant data export
- Tenant data deletion

