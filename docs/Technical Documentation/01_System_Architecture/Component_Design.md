# Component Design

## Service Layer Architecture

The service layer follows a clear separation of concerns with orchestration services coordinating specialized phase-specific services.

### InvoiceService (Orchestrator)

**Location:** `app/services/invoice_service.py`

**Responsibilities:**
- Routes invoice processing to Phase-1 or Phase-2 workflows
- Manages invoice persistence lifecycle (CREATED → PROCESSING → CLEARED/REJECTED/FAILED)
- Enforces idempotency (tenant_id + invoice_number uniqueness)
- Coordinates validation before processing
- Handles retry operations for failed/rejected invoices
- Creates audit log entries via InvoiceLogService

**Dependencies:**
- Phase-1 services: QRService, Phase1Validator
- Phase-2 services: XMLGenerator, CryptoService, ClearanceService, Phase2Validator, Phase2QRService
- ZatcaPolicyService: Environment and invoice-type policy enforcement
- Database session for persistence operations
- TenantContext for tenant isolation

**Key Methods:**
- `process_invoice()`: Non-persistent processing (legacy support)
- `process_invoice_with_persistence()`: Full persistence workflow with status tracking
- `retry_invoice()`: Retry failed/rejected invoices with audit trail

**Design Patterns:**
- Dependency injection via constructor parameters
- Service composition (delegates to specialized services)
- Transaction management via database session

### Phase-1 Services

**QRService** (`app/services/phase1/qr_service.py`)
- Generates QR codes for Phase-1 invoices
- Encodes seller info, invoice date, totals, tax amount
- Returns base64-encoded QR code image

**Phase1Validator** (`app/services/phase1/validator.py`)
- Validates Phase-1 invoice data structure
- Checks required fields, data types, value ranges
- Returns ValidationResponse with pass/fail status and issues

### Phase-2 Services

**XMLGenerator** (`app/services/phase2/xml_generator.py`)
- Generates UBL 2.1 XML invoices
- Handles XML structure, namespaces, required elements
- Validates XML has no unrendered template variables
- Does not handle signing or ZATCA submission

**CryptoService** (`app/services/phase2/crypto_service.py`)
- Performs XML cryptographic signing (XMLDSig, RSA-SHA256)
- Computes XML hashes (unsigned and signed)
- Manages certificate loading per tenant per environment
- Does not generate XML or submit to ZATCA

**ClearanceService** (`app/services/phase2/clearance_service.py`)
- Submits signed XML to ZATCA for clearance
- Handles retry logic with exponential backoff
- Manages ZATCA API communication
- Does not generate XML or perform signing

**Phase2Validator** (`app/services/phase2/validator.py`)
- Validates Phase-2 invoice data structure
- Checks required fields, UUID format, PIH requirements
- Returns ValidationResponse with pass/fail status

**Phase2QRService** (`app/services/phase2/qr_service.py`)
- Generates QR codes for Phase-2 invoices
- Includes XML hash and digital signature
- QR code is optional (ZATCA clearance QR takes precedence)

## Integration Layer

**ZATCA Client Factory** (`app/integrations/zatca/factory.py`)
- Factory pattern for creating ZATCA client instances
- Routes to SandboxClient or ProductionClient based on environment
- Abstracts client selection from service layer

**SandboxClient** (`app/integrations/zatca/sandbox.py`)
- Implements ZATCA sandbox API communication
- Handles HTTP requests, error parsing, response mapping
- Manages authentication headers and request formatting

**ProductionClient** (`app/integrations/zatca/production.py`)
- Implements ZATCA production API communication
- Same interface as SandboxClient, different base URL
- Production-specific error handling and retry logic

**Certificate Manager** (`app/integrations/zatca/cert_manager.py`)
- Manages certificate file paths per tenant per environment
- Handles certificate activation/deactivation
- Validates certificate format and expiration
- Does not perform cryptographic operations

**Compliance CSID Service** (`app/integrations/zatca/compliance_csid.py`)
- Handles automated sandbox certificate onboarding
- Submits CSR to ZATCA Compliance CSID API
- Automatically stores received certificates
- OAuth authentication integration

**Production Onboarding Service** (`app/integrations/zatca/production_onboarding.py`)
- Handles production certificate onboarding with OTP flow
- Two-step process: submit request → validate OTP → receive certificate
- Automatic certificate storage after OTP validation
- OAuth authentication for production environment
- Comprehensive error handling for OTP validation failures

**Error Catalog** (`app/integrations/zatca/error_catalog.py`)
- Maps ZATCA error codes to human-readable messages
- Provides bilingual error explanations (English, Arabic)
- Extracts error codes from ZATCA response messages

## Data Layer

**Models** (`app/models/`)
- SQLAlchemy ORM models for database entities
- Invoice: Master invoice record with status tracking
- InvoiceLog: Immutable audit log entries
- Tenant: Tenant configuration and isolation
- ApiKey: API key management with tenant mapping
- Certificate: Certificate metadata storage
- Subscription: Plan and usage tracking

**CRUD Operations** (`app/db/crud.py`)
- Generic CRUD operations for database entities
- Tenant-scoped queries (all operations filter by tenant_id)
- Transaction management via SQLAlchemy sessions

**Session Management** (`app/db/session.py`)
- Database session factory
- Session lifecycle management
- Connection pooling configuration

## API Layer

**Route Handlers** (`app/api/v1/routes/`)
- Thin controllers that delegate to service layer
- Request/response validation via Pydantic schemas
- Dependency injection for services and database sessions
- Authentication enforcement via dependencies

**Router Aggregation** (`app/api/v1/router.py`)
- Combines all route modules into single router
- Registers routes with FastAPI application
- Separates public routes from internal routes

**Dependencies** (`app/core/security.py`)
- `verify_api_key_and_resolve_tenant()`: API key validation and tenant resolution
- Attaches TenantContext to request.state
- Enforces tenant isolation at request level

## Middleware

**SecurityHeadersMiddleware** (`app/middleware/security_headers.py`)
- Injects security headers (CSP, HSTS, X-Frame-Options)
- Applied to all responses
- Configurable via settings

**RateLimitMiddleware** (`app/middleware/rate_limit.py`)
- Enforces rate limits per API key
- Uses subscription plan limits
- Returns 429 Too Many Requests on limit exceeded

**AuditMiddleware** (`app/middleware/audit.py`)
- Logs all API requests and responses
- Captures request payload, response status, timing
- Writes to audit log storage (separate from InvoiceLog)

**CORS Middleware** (FastAPI built-in)
- Handles cross-origin resource sharing
- Configurable allowed origins, methods, headers

## Core Infrastructure

**Configuration** (`app/core/config.py`)
- Environment-based settings management
- Loads from environment variables and .env files
- Type-safe settings via Pydantic BaseSettings
- Single source of truth for ZATCA environment selection

**Logging** (`app/core/logging.py`)
- Structured JSON logging setup
- Configurable log levels and formats
- Request correlation IDs for tracing

**Error Handling** (`app/core/error_handling.py`)
- Global exception handlers
- Standardized error response formats
- Error code mapping and translation

**Constants** (`app/core/constants.py`)
- Enum definitions for InvoiceMode, Environment, InvoiceStatus
- Shared constants across application
- Type-safe enum usage

## Utility Layer

**XML Utilities** (`app/utils/xml_utils.py`)
- XML escaping and sanitization
- XML parsing helpers
- Template variable detection

**Hash Utilities** (`app/utils/hash_utils.py`)
- Hash computation for XML content
- SHA-256 hashing for ZATCA compliance
- Hash formatting and encoding

**Time Utilities** (`app/utils/time_utils.py`)
- ZATCA timestamp formatting
- Timezone handling
- Date parsing and validation

**Data Masking** (`app/utils/data_masking.py`)
- Sensitive data masking for logs
- PII anonymization
- Safe JSON/XML serialization

## Component Interactions

### Invoice Processing Flow

1. Route handler receives request, validates schema
2. Dependency resolves tenant context from API key
3. InvoiceService.process_invoice_with_persistence() called
4. InvoiceService creates invoice record (status: CREATED)
5. Phase-specific validator runs (Phase1Validator or Phase2Validator)
6. If validation fails, invoice status updated to REJECTED, response returned
7. If validation passes, invoice status updated to PROCESSING
8. Policy Check: Clearance Allowed? (Phase-2 only)
   - ZatcaPolicyService validates environment and invoice-type policy
   - Rejects with `ZATCA_POLICY_VIOLATION` if not allowed
9. Phase-specific processing:
   - Phase-1: QRService generates QR code
   - Phase-2: XMLGenerator → CryptoService → ClearanceService
10. Policy Check: Reporting Allowed? (after clearance, Phase-2 only)
    - ZatcaPolicyService validates automatic reporting is allowed
    - Skips reporting if policy blocks (non-blocking, clearance success preserved)
11. Invoice status updated based on result (CLEARED/REJECTED/FAILED)
12. InvoiceLogService creates audit log entry
13. Response returned to client

### Retry Flow

1. Route handler receives retry request with invoice_id
2. InvoiceService.retry_invoice() called
3. Invoice fetched with tenant isolation check
4. Status validated (only FAILED/REJECTED can be retried)
5. Original request payload reconstructed from InvoiceLog
6. RETRY audit log entry created
7. Invoice status updated to PROCESSING
8. Normal processing flow executed
9. Invoice status updated based on result
10. Final audit log entry created

### Certificate Management Flow

**Manual Upload:**
1. Route handler receives certificate upload request
2. CertificateService validates certificate format
3. Cryptographic verification: Private key matches certificate
4. Certificate file stored per tenant per environment
5. Old certificate deactivated (if exists)
6. New certificate activated
7. Certificate metadata stored in database

**Sandbox Onboarding (Automated):**
1. User generates CSR via API
2. User calls `POST /api/v1/zatca/compliance/csid/submit`
3. ComplianceCSIDService submits CSR to ZATCA
4. System receives certificate from ZATCA
5. Cryptographic verification: Private key matches certificate
6. Certificate automatically stored
7. Certificate metadata stored in database

**Production Onboarding (OTP-based):**
1. User generates CSR via API
2. User calls `POST /api/v1/zatca/production/onboarding/submit` (Step 1)
3. ProductionOnboardingService submits onboarding request
4. System receives OTP challenge from ZATCA
5. User validates OTP (Step 2: same endpoint with OTP)
6. System receives certificate from ZATCA
7. Cryptographic verification: Private key matches certificate
8. Certificate automatically stored
9. Certificate metadata stored in database

## Design Principles

**Separation of Concerns:**
- Services handle business logic, not HTTP concerns
- Route handlers are thin, delegate to services
- Models represent data, not business rules

**Dependency Injection:**
- Services accept dependencies via constructor
- Enables testing with mock dependencies
- No global state or singletons

**Tenant Isolation:**
- All database queries filter by tenant_id
- Tenant context resolved early in request pipeline
- No cross-tenant data access possible

**Error Handling:**
- Services raise exceptions, don't return error codes
- Route handlers catch exceptions and return HTTP responses
- Error messages are tenant-scoped and auditable

**Transaction Management:**
- Database sessions managed per request
- Transactions committed at service boundaries
- Rollback on exceptions

## Current Implementation Status

All components described above are implemented and production-ready. The architecture supports:

- Phase-1 and Phase-2 invoice processing
- Environment and invoice-type policy enforcement
- Multi-tenant isolation
- Certificate management per tenant per environment
- Production CSID Onboarding (OTP-based flow)
- Sandbox Compliance CSID (automated)
- Cryptographic certificate-private key verification
- Invoice persistence with audit trails
- Retry operations with audit tracking
- Reporting and analytics
- Subscription and plan management

Future considerations (not currently implemented):

- Async invoice processing queue
- Webhook delivery system
- Horizontal scaling with message queues
- Distributed tracing across services

