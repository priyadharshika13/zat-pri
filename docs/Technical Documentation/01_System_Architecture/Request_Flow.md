# Request Flow

## HTTP Request Processing Pipeline

All HTTP requests follow a consistent processing pipeline through middleware, authentication, route handlers, and service layers.

## Middleware Execution Order

Middleware executes in reverse order of registration (last registered = first executed):

1. **SecurityHeadersMiddleware** (outermost)
   - Injects security headers (CSP, HSTS, X-Frame-Options)
   - Applied to all responses
   - No request modification

2. **CORSMiddleware**
   - Handles preflight OPTIONS requests
   - Adds CORS headers to responses
   - Allows all origins, methods, headers (configurable)

3. **RateLimitMiddleware**
   - Enforces per-tenant rate limits
   - Requires tenant context (resolved in dependency)
   - Returns 429 Too Many Requests on limit exceeded
   - Uses token bucket algorithm

4. **AuditMiddleware** (innermost)
   - Logs request method, path, client IP
   - Logs response status code and processing time
   - No request/response modification

## Authentication Flow

Authentication occurs via FastAPI dependency injection before route handler execution:

1. **API Key Extraction**
   - Extracts `X-API-Key` header from request
   - Returns 401 if header missing

2. **API Key Validation**
   - Queries database for active API key
   - Returns 401 if key not found or inactive

3. **Tenant Resolution**
   - Joins API key with tenant table
   - Verifies tenant is active
   - Returns 401 if tenant inactive

4. **Tenant Context Creation**
   - Creates TenantContext object
   - Attaches to `request.state.tenant`
   - Updates API key `last_used_at` timestamp

5. **Dependency Injection**
   - TenantContext injected into route handler
   - Available to all downstream services

## Route Handler Execution

Route handlers execute after authentication:

1. **Request Schema Validation**
   - Pydantic validates request body/query parameters
   - Returns 422 if validation fails
   - Type-safe request objects created

2. **Dependency Resolution**
   - Database session created via `get_db()`
   - Service instances created with dependencies
   - Tenant context propagated to services

3. **Business Logic Execution**
   - Route handler calls service methods
   - Services perform business operations
   - Database transactions managed per request

4. **Response Serialization**
   - Pydantic serializes response models
   - JSON response returned to client
   - Status codes set per operation

## Invoice Processing Request Flow

Detailed flow for `POST /api/v1/invoices`:

1. **Request Received**
   - FastAPI receives HTTP POST request
   - Request body parsed as JSON

2. **Middleware Processing**
   - Security headers added
   - CORS headers added
   - Rate limit checked (requires tenant context)
   - Audit log entry started

3. **Authentication**
   - `verify_api_key_and_resolve_tenant()` dependency executes
   - API key validated, tenant context resolved
   - Tenant context attached to request state

4. **Route Handler Execution**
   - `process_invoice()` route handler called
   - Request schema validated (InvoiceRequest)
   - Database session created
   - InvoiceService instance created with dependencies

5. **Production Access Guards**
   - `check_production_access()` validates paid plan for Production
   - `require_production_confirmation()` validates confirmation flag
   - Returns 403 if guards fail

6. **Subscription Limit Check**
   - SubscriptionService checks invoice limit
   - Returns 403 or 429 if limit exceeded
   - Limit check occurs before invoice creation

7. **Invoice Processing**
   - `InvoiceService.process_invoice_with_persistence()` called
   - Invoice record created (status: CREATED)
   - Phase-specific validation executed
   - Policy Check: Clearance Allowed? (Phase-2 only)
     - `ZatcaPolicyService.validate_clearance_allowed()` called
     - Validates environment and invoice-type policy
     - Rejects with `ZATCA_POLICY_VIOLATION` if not allowed
   - Invoice status updated to PROCESSING
   - Phase-specific processing (Phase-1 or Phase-2)
   - Policy Check: Reporting Allowed? (after clearance, Phase-2 only)
     - `ZatcaPolicyService.validate_clearance_and_reporting_allowed()` called
     - Skips automatic reporting if policy blocks (non-blocking)
   - Invoice status updated based on result

8. **Response Generation**
   - InvoiceResponse serialized
   - JSON response returned
   - Status code 200 on success

9. **Audit Logging**
   - AuditMiddleware logs response
   - Processing time recorded
   - Log entry completed

## Error Handling Flow

Errors propagate through layers:

1. **Service Layer Errors**
   - Services raise exceptions (ValueError, HTTPException)
   - No HTTP status codes in service layer

2. **Route Handler Errors**
   - Route handlers catch service exceptions
   - Convert to HTTPException with appropriate status codes
   - Error details serialized in response

3. **Global Exception Handler**
   - Catches unhandled exceptions
   - Returns 500 Internal Server Error
   - Error details logged, not exposed to client

4. **ZATCA Error Handling**
   - ZATCA errors mapped via error catalog
   - Human-readable error messages
   - Bilingual support (English, Arabic)

## Database Transaction Flow

Database transactions managed per request:

1. **Session Creation**
   - Database session created via `get_db()` dependency
   - Session scoped to request lifecycle

2. **Transaction Start**
   - Transaction starts on first database operation
   - All operations within same transaction

3. **Transaction Commit**
   - Transaction committed on successful request
   - Changes persisted to database

4. **Transaction Rollback**
   - Transaction rolled back on exception
   - No partial commits on errors

5. **Session Cleanup**
   - Session closed after request completes
   - Connection returned to pool

## Tenant Isolation Enforcement

Tenant isolation enforced at multiple points:

1. **Authentication Level**
   - Tenant context resolved from API key
   - No tenant context = no access

2. **Route Handler Level**
   - Tenant context injected as dependency
   - All service calls include tenant context

3. **Service Level**
   - All database queries filter by `tenant_id`
   - Tenant context required for all operations

4. **Database Level**
   - All tables include `tenant_id` column
   - Foreign key constraints enforce isolation

## Rate Limiting Flow

Rate limiting enforced per tenant:

1. **Tenant Context Required**
   - RateLimitMiddleware requires tenant context
   - Skips rate limiting if tenant context unavailable

2. **Rate Limit Retrieval**
   - SubscriptionService retrieves plan rate limit
   - Default rate limit used if retrieval fails

3. **Token Bucket Algorithm**
   - Token bucket created per tenant (in-memory)
   - Tokens refilled at fixed rate
   - Request consumes one token

4. **Limit Enforcement**
   - Returns 429 if no tokens available
   - Rate limit headers added to response
   - Retry-After header indicates when to retry

## Current Implementation Status

All request flow components are implemented and production-ready:

- Middleware pipeline with correct execution order
- Authentication via API key with tenant resolution
- Route handlers with dependency injection
- Database transaction management
- Tenant isolation enforcement
- Rate limiting per tenant
- Error handling and logging

Future considerations (not currently implemented):

- Request correlation IDs for distributed tracing
- Request queuing for high-volume scenarios
- Async request processing with background tasks
- Request/response compression

