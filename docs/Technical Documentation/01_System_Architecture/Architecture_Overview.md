# System Architecture Overview

## Platform Description

FATURAIX is a multi-tenant SaaS platform providing ZATCA Phase-1 and Phase-2 e-invoicing compliance via REST APIs. The system processes invoices, generates UBL 2.1 XML, performs cryptographic signing, and submits invoices to ZATCA for clearance.

## High-Level Architecture

The platform consists of three primary components:

- **Backend API**: FastAPI application handling invoice processing, compliance logic, and ZATCA integration
- **Frontend Dashboard**: React + TypeScript UI for invoice management, reporting, and system administration
- **Database**: PostgreSQL for production, SQLite for development and testing

## Component Boundaries

### Backend Application

The backend is organized into distinct layers:

**API Layer** (`app/api/v1/routes/`)
- REST endpoint handlers
- Request/response validation via Pydantic schemas
- Dependency injection for services and database sessions
- Authentication and authorization enforcement

**Service Layer** (`app/services/`)
- Business logic orchestration
- Phase-specific invoice processing (Phase-1, Phase-2)
- Environment and invoice-type policy enforcement
- ZATCA integration coordination
- Reporting and analytics
- Certificate management with cryptographic verification

**Integration Layer** (`app/integrations/zatca/`)
- ZATCA API client implementations (sandbox, production)
- Production CSID Onboarding (OTP-based flow)
- Sandbox Compliance CSID (automated)
- Certificate management and validation
- Error catalog and mapping

**Data Layer** (`app/db/`, `app/models/`)
- SQLAlchemy ORM models
- Database session management
- CRUD operations

**Core Infrastructure** (`app/core/`)
- Configuration management
- Security and authentication
- Logging setup
- Error handling

**Middleware** (`app/middleware/`)
- Security headers injection
- Rate limiting
- Audit logging
- CORS handling

### Frontend Application

The frontend is a single-page application built with React and TypeScript:

- **Pages**: Dashboard, invoice management, API playground, billing
- **Components**: Reusable UI components for forms, tables, navigation
- **API Client**: HTTP client for backend communication
- **State Management**: React hooks and context for application state

### Database

PostgreSQL is used for production deployments. The database stores:

- Tenant configurations and API keys
- Invoice master records and audit logs
- Certificate metadata
- Subscription plans and usage tracking

## Request Flow

1. Client sends HTTP request to FastAPI application
2. Middleware processes request (security headers, CORS, rate limiting)
3. Authentication dependency verifies API key and resolves tenant context
4. Route handler validates request schema
5. Service layer executes business logic
6. Database operations performed via SQLAlchemy sessions
7. Response returned to client
8. Audit middleware logs request/response

## Multi-Tenancy Model

Tenant isolation is enforced at multiple levels:

- **API Key Resolution**: Each API key maps to a single tenant
- **Database Queries**: All queries filter by `tenant_id`
- **Certificate Storage**: Certificates stored per tenant, per environment
- **Subscription Limits**: Usage tracked per tenant

Tenant context is resolved early in the request pipeline and propagated to all service layers.

## Environment Separation

The system supports two ZATCA environments:

- **SANDBOX**: Development and testing environment
- **PRODUCTION**: Live ZATCA integration

Environment selection is controlled by `ZATCA_ENV` configuration. Each tenant can operate in one environment at a time. Certificates are isolated per environment.

## Compliance vs Intelligence Separation

The architecture maintains strict separation between compliance operations and advisory intelligence:

**Compliance Layer** (Rule-based, deterministic):
- Invoice validation
- UBL XML generation
- Cryptographic signing
- ZATCA API communication
- VAT calculations

**Intelligence Layer** (Advisory-only):
- Error explanation
- Rejection prediction
- Root cause analysis
- Compliance scoring
- Trend analysis

Intelligence services are optional and can be globally disabled. They never modify invoice data or compliance decisions.

## Technology Stack

**Backend:**
- Python 3.x
- FastAPI
- SQLAlchemy (ORM)
- Alembic (migrations)
- Pydantic (validation)

**Frontend:**
- React 18
- TypeScript
- Vite (build tool)
- Tailwind CSS
- React Router

**Database:**
- PostgreSQL (production)
- SQLite (development/testing)

**Infrastructure:**
- Docker containerization
- Gunicorn (production WSGI server)

## Deployment Model

The application is designed for containerized deployment:

- Backend runs as a FastAPI application behind Gunicorn
- Frontend builds to static assets served via web server or CDN
- Database runs as separate PostgreSQL instance
- Environment configuration via environment variables

## Current Implementation Status

The following components are implemented and production-ready:

- Phase-1 and Phase-2 invoice processing
- Multi-tenant architecture with strict isolation
- Certificate management per tenant per environment
- Production CSID Onboarding (OTP-based flow)
- Sandbox Compliance CSID (automated)
- Certificate-Private Key Cryptographic Verification
- Environment and Invoice-Type Policy Enforcement
- Invoice persistence with audit trails
- Reporting APIs (invoices, VAT summaries, status breakdown)
- Subscription and plan management
- Advisory intelligence services (optional)
- Production-ready UI dashboard
- API playground for testing

Future considerations (not currently implemented):

- Webhook delivery system
- Async invoice processing queue
- Horizontal scaling with load balancers
- Multi-region deployment

