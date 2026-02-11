# FATURAIX

**Enterprise-Grade Saudi E-Invoicing & Compliance Intelligence Platform**

---

## 🚀 Overview

**FATURAIX** is a production-ready, enterprise-grade API platform designed to help businesses in Saudi Arabia comply with **ZATCA Phase-1 and Phase-2 (E-Invoicing)** regulations, while adding **safe, advisory-only AI intelligence** to reduce invoice rejections and improve compliance maturity.

**FATURAIX** provides a complete SaaS solution for ZATCA e-invoicing compliance with:
- Full Phase-1 and Phase-2 invoice processing
- Enterprise-grade invoice persistence and audit trails
- Comprehensive reporting and analytics APIs
- Multi-tenant architecture with strict isolation
- Production-ready UI dashboard
- Advisory AI intelligence (optional, non-interfering)

The platform is built with **strict regulatory separation**:

- **All ZATCA-critical operations are 100% rule-based and deterministic**
- **AI is advisory-only and never interferes with compliance logic**

---

## 🇸🇦 What is ZATCA?

The **Zakat, Tax and Customs Authority (ZATCA)** is the regulatory body governing:

- VAT compliance
- E-Invoicing (FATOORA)
- Invoice clearance & reporting in Saudi Arabia

ZATCA mandates:

- UBL 2.1 XML invoices
- Cryptographic signing
- UUID & hash chaining (PIH)
- Real-time clearance (Phase-2)
- Strict validation rules

Failure to comply can result in:

- Invoice rejection
- Business disruption
- Regulatory penalties

---

## 🧠 What AI Does (and Does NOT Do)

### ✅ What AI DOES

AI in this platform is **advisory intelligence only**. It helps by:

- **Explaining ZATCA rejection errors** in human-readable terms (English & Arabic)
- **Predicting invoice rejection risk** before submission
- **Highlighting risky invoice fields** (pre-check advisor)
- **Identifying root causes** of recurring failures
- **Scoring overall ZATCA compliance readiness** (tenant-level health)
- **Detecting error & risk trends** over time

AI outputs are:

- Read-only
- Non-blocking
- Explainable
- Tenant-scoped
- Fully optional (can be globally disabled)

---

### ❌ What AI DOES NOT Do (Critical Guarantee)

AI **NEVER**:

- Modifies invoice data
- Generates or alters XML
- Calculates VAT
- Changes hashes, UUIDs, PIH, or signatures
- Submits invoices to ZATCA
- Overrides ZATCA validation logic

All ZATCA-critical workflows remain **deterministic, auditable, and rule-based**.

---

## 🔐 Compliance & Regulatory Guarantees

### Deterministic Compliance Engine

All ZATCA-critical operations are implemented without AI involvement:

- UBL XML generation
- VAT calculations
- Hashing & cryptographic signing
- Certificate handling
- ZATCA API communication

These operations are:

- **100% rule-based**
- **Deterministic** (same input = same output)
- **Auditable** (full traceability)
- **Regulatory-compliant**

---

### Audit-Ready Architecture

- **Tenant isolation** (per company)
- **Environment isolation** (sandbox / production)
- **Certificate isolation** per tenant
- **Immutable invoice logs**
- **Full traceability** of all operations

---

### AI Governance Controls

- **Global AI enable/disable toggle** (`ENABLE_AI_EXPLANATION`)
- **Per-plan AI usage limits**
- **AI usage logging** (no invoice data stored)
- **Graceful fallback** when AI is disabled
- **Subscription-based access control**

---

## 🏢 Enterprise Positioning

**FATURAIX** is designed for:

- **ERP providers** integrating ZATCA compliance
- **Accounting platforms** adding Saudi e-invoicing
- **POS systems** requiring real-time clearance
- **E-commerce platforms** processing Saudi transactions
- **Large enterprises** with multi-entity operations
- **SaaS vendors** entering the Saudi market

### Key Enterprise Features

- **Multi-tenant architecture** (complete data isolation)
- **Subscription-based usage control** (plans, limits, billing)
- **API-first design** (RESTful, well-documented)
- **High availability & scalability** (production-ready)
- **Clear separation** of compliance vs intelligence
- **Invoice persistence** (master table with full audit trails)
- **Reporting APIs** (invoice and VAT analytics)
- **Production-ready UI** (React + TypeScript dashboard)
- **Saudi Vision 2030 aligned** (digital transformation)

---

## 🧩 Feature Overview

### Core ZATCA Compliance

**Phase-1 (Simplified E-Invoicing)**
- QR code generation
- Basic invoice validation
- UBL 2.1 XML structure
- Invoice persistence with idempotency

**Phase-2 (Advanced E-Invoicing)**
- Real-time clearance with ZATCA
- Cryptographic signing (X.509 certificates)
- UUID & hash chaining (PIH)
- Invoice reporting
- Sandbox & Production environments
- Full invoice persistence and audit trails

**Technical Capabilities**
- UBL 2.1 XML generation (UBL 2.1 compliant)
- Cryptographic signing & validation (XMLDSig, RSA-SHA256)
- Certificate management (per tenant, per environment)
- Retry logic with exponential backoff (3 retries)
- Comprehensive error handling (bilingual messages)
- Invoice master persistence (idempotent, audit-safe)
- Status lifecycle tracking (CREATED → PROCESSING → CLEARED/REJECTED/FAILED)

---

### AI Intelligence (Advisory-Only)

**Phase-2 AI Features**
- **ZATCA Error Explanation** (English & Arabic)
  - Human-readable error explanations
  - Step-by-step fix guidance
  - Bilingual support (EN/AR)

**Phase-3 AI Intelligence Suite**

1. **Invoice Rejection Prediction** (`/api/v1/ai/predict-rejection`)
   - Predicts rejection likelihood before submission
   - Risk levels: LOW, MEDIUM, HIGH
   - Identifies likely rejection reasons

2. **Smart Pre-Check Advisor** (`/api/v1/ai/precheck-advisor`)
   - Field-level risk analysis
   - Actionable warnings with JSONPath pointers
   - Identifies risky patterns before submission

3. **Root Cause Intelligence** (`/api/v1/ai/root-cause-analysis`)
   - Analyzes WHY failures occur (not just WHAT)
   - Primary & secondary cause identification
   - Prevention checklist for systemic fixes

4. **ZATCA Readiness Score** (`/api/v1/ai/readiness-score`)
   - Tenant-level compliance health score (0-100)
   - Status classification: GREEN, AMBER, RED
   - Risk factors & improvement suggestions

5. **Error & Trend Intelligence** (`/api/v1/ai/error-trends`)
   - Time-based trend analysis
   - Emerging risk detection
   - Operational recommendations
   - Supports tenant or global scope

---

### Invoice Persistence & Audit

- **Invoice master table** - Complete invoice persistence with full metadata
- **Idempotent processing** - Duplicate invoice prevention (tenant_id + invoice_number)
- **Status lifecycle tracking** - CREATED → PROCESSING → CLEARED/REJECTED/FAILED
- **Immutable audit logs** - Append-only audit trail for compliance
- **Full observability** - Request payload, generated XML, ZATCA response storage
- **Data retention policy** - Configurable retention with anonymization support

### Reporting & Analytics

- **Invoice Reports** - Paginated invoice listing with filtering (status, phase, date range)
- **VAT Summaries** - VAT reporting with period-based aggregation
- **Status Statistics** - Invoice status counts and trends
- **Tenant-scoped** - All reports automatically filtered by tenant

### Tenant & Security

- **API key → tenant mapping** (automatic tenant resolution)
- **Company & VAT number isolation** (no cross-tenant access)
- **Certificate isolation** per tenant per environment
- **Environment-specific enforcement** (SANDBOX / PRODUCTION)
- **Subscription-based access control** (plans, limits, usage tracking)
- **Production access guards** (paid plans only, explicit confirmation required)

---

## 📊 Saudi Vision 2030 Alignment

This platform aligns directly with **Saudi Vision 2030** by:

- **Supporting digital tax transformation** (automated compliance)
- **Enabling compliance automation** (reducing manual work)
- **Reducing manual intervention** (streamlined workflows)
- **Improving business transparency** (audit-ready architecture)
- **Enabling scalable digital infrastructure** (API-first, multi-tenant)
- **Encouraging AI-assisted innovation** (governed, transparent, responsible)

AI is used **responsibly, transparently, and in compliance** with regulatory expectations.

---

## 🛠️ Designed for Production

- **✅ Production Ready** - All production readiness requirements completed
- **✅ Production-Ready UI** - Complete frontend implementation with professional UX
- **Docker-ready** (containerized deployment)
- **Structured logging** (JSON logs, traceability)
- **Timeout & retry handling** (resilient ZATCA communication)
- **Graceful degradation** (AI failures never break compliance)
- **Clear operational boundaries** (compliance vs intelligence)
- **Enterprise-safe defaults** (AI disabled by default)
- **Security headers** (CSP, HSTS, X-Frame-Options, etc.)
- **End-to-end testing** (Playwright framework with 12+ critical scenarios)
- **Production build verification** (optimized builds with source maps)
- **Professional UX** (skeleton loaders, empty states, error handling)
- **Comprehensive test coverage** (data-testids for all interactive elements)

---

## 🔒 Safety & Non-Interference Guarantee

This platform implements **strict non-interference** between compliance and AI:

- **Compliance logic is never modified by AI**
- **AI cannot access or modify invoice payloads**
- **AI cannot generate or alter XML**
- **AI cannot calculate or change VAT**
- **AI cannot touch hashes, PIH, or signatures**
- **AI cannot block or prevent submissions**

See [`docs/ZATCA_NON_INTERFERENCE.md`](docs/ZATCA_NON_INTERFERENCE.md) for detailed technical guarantees.

---

## 📌 Summary

**FATURAIX** is not just an integration —  

it is a **compliance-first, intelligence-enabled platform** designed to help organizations:

- ✅ **Comply with ZATCA confidently** (deterministic, rule-based compliance)
- ✅ **Reduce invoice rejections** (AI-powered risk prediction & pre-check)
- ✅ **Understand failures deeply** (root cause analysis)
- ✅ **Improve compliance maturity over time** (readiness scoring & trend analysis)
- ✅ **Scale safely in Saudi Arabia** (multi-tenant, enterprise-ready)

---

> **Compliance is deterministic.**  
> **Intelligence is advisory.**  
> **Control always stays with the enterprise.**

---

## 📚 Documentation

### Core Documentation
- [`docs/COMPETITIVE_INTELLIGENCE_OVERVIEW.md`](docs/COMPETITIVE_INTELLIGENCE_OVERVIEW.md) - Competitive analysis and intelligence overview for investors, enterprises, and regulators
- [`docs/ZATCA_APPROVAL_GUIDE.md`](docs/ZATCA_APPROVAL_GUIDE.md) - Complete ZATCA approval checklist and application flow
- [`docs/ZATCA_NON_INTERFERENCE.md`](docs/ZATCA_NON_INTERFERENCE.md) - Technical non-interference guarantees
- [`docs/AI_USAGE_DISCLAIMER.md`](docs/AI_USAGE_DISCLAIMER.md) - AI usage guidelines and disclaimers
- [`docs/PRODUCTION_READINESS.md`](docs/PRODUCTION_READINESS.md) - Production deployment checklist and guidelines
- [`docs/RELEASE_READINESS_SUMMARY.md`](docs/RELEASE_READINESS_SUMMARY.md) - Production readiness assessment
- [`docs/PHASE2_FIX_SUMMARY.md`](docs/PHASE2_FIX_SUMMARY.md) - Phase-2 invoice processing fixes and verification

### Testing & Verification
- [`docs/SMOKE_TEST_COMMANDS.md`](docs/SMOKE_TEST_COMMANDS.md) - Quick reference for smoke tests
- [`docs/E2E_SMOKE_TEST_REPORT.md`](docs/E2E_SMOKE_TEST_REPORT.md) - End-to-end test results
- [`docs/PLAYWRIGHT_E2E_ANALYSIS.md`](docs/PLAYWRIGHT_E2E_ANALYSIS.md) - Playwright E2E testing guide
- [`tests/UAT_TEST_REPORT.md`](tests/UAT_TEST_REPORT.md) - User Acceptance Testing report

### UI Implementation
- [`docs/UI_IMPLEMENTATION_SUMMARY.md`](docs/UI_IMPLEMENTATION_SUMMARY.md) - Complete UI implementation summary
- [`docs/UI_IMPLEMENTATION_TEST_CHECKLIST.md`](docs/UI_IMPLEMENTATION_TEST_CHECKLIST.md) - Comprehensive UI testing checklist

### API & Integration
- [`docs/API_PLAYGROUND.md`](docs/API_PLAYGROUND.md) - Interactive API playground documentation
- [`docs/API_IMPLEMENTATION_SUMMARY.md`](docs/API_IMPLEMENTATION_SUMMARY.md) - API implementation details
- [`docs/REPORTING_APIS.md`](docs/REPORTING_APIS.md) - Invoice and VAT reporting APIs documentation
- [`docs/REPORTING_IMPLEMENTATION_SUMMARY.md`](docs/REPORTING_IMPLEMENTATION_SUMMARY.md) - Reporting APIs implementation summary

### Database & Infrastructure
- [`docs/POSTGRESQL_E2E_SETUP.md`](docs/POSTGRESQL_E2E_SETUP.md) - PostgreSQL setup guide
- [`docs/POSTGRESQL_MIGRATION.md`](docs/POSTGRESQL_MIGRATION.md) - Database migration guide
- [`docs/INVOICE_PERSISTENCE_REFACTORING.md`](docs/INVOICE_PERSISTENCE_REFACTORING.md) - Invoice persistence architecture
- [`docs/INVOICE_DOMAIN_FREEZE.md`](docs/INVOICE_DOMAIN_FREEZE.md) - Invoice domain freeze documentation

---

## 📁 Project Structure

```
ZATCA_AI_API/
├── backend/                 # Backend API (FastAPI)
│   ├── app/                # Application code
│   ├── alembic/            # Database migrations
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Backend container
│   ├── gunicorn.conf.py    # Production server config
│   ├── alembic.ini         # Migration config
│   └── .env.example        # Environment variables template
│
├── frontend/               # Frontend (React + TypeScript + Vite)
│   ├── src/                # Source code
│   │   ├── pages/          # Page components
│   │   ├── components/     # Reusable components
│   │   │   ├── common/     # Common UI components
│   │   │   ├── invoice/    # Invoice-specific components
│   │   │   ├── billing/    # Billing components
│   │   │   └── playground/ # API Playground components
│   │   ├── lib/            # API clients and utilities
│   │   └── types/          # TypeScript type definitions
│   ├── e2e/                # Playwright E2E tests
│   ├── public/             # Static assets
│   ├── package.json        # Node dependencies
│   ├── tsconfig.json       # TypeScript config
│   └── playwright.config.ts # Playwright configuration
│
├── tests/                  # Test suite
│   ├── backend/            # Backend tests
│   └── pytest.ini          # Test configuration
│
├── infra/                  # Infrastructure
│   └── docker-compose.yml  # Docker Compose config
│
├── scripts/                # Utility scripts
│   ├── run_tests.sh        # Test runner (Linux/Mac)
│   └── run_tests.bat       # Test runner (Windows)
│
└── docs/                   # Documentation
    ├── README.md
    ├── PRODUCTION_READINESS.md
    └── ...
```

## 🚦 Getting Started

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Activate virtual environment (if using one)
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template (if .env doesn't exist)
# cp .env.example .env
# Edit .env with your configuration

# Set DATABASE_URL for PostgreSQL (required for non-test environments)
# Windows PowerShell:
# $env:DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/zatca_ai"
# Linux/Mac:
# export DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/zatca_ai

# Run database migrations
alembic upgrade head

# Run development server
# Option 1: Use the helper script (recommended - works without uvicorn in PATH)
python run_dev.py

# Option 2: Use python -m uvicorn (recommended if uvicorn not in PATH)
python -m uvicorn app.main:app --reload

# Option 3: Use shell scripts (Linux/Mac/Windows)
# Linux/Mac: ./run_dev.sh
# Windows: run_dev.bat

# Option 4: Run uvicorn directly (requires uvicorn in PATH)
# uvicorn app.main:app --reload
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Frontend UI Features

The frontend is a **production-ready React + TypeScript + Vite** application with a clean, professional SaaS dashboard design.

**Key UI Features:**

- **Complete Invoice Creation Form** - Full form UI with seller/buyer details, dynamic line items, and real-time tax calculation
- **Invoice Management** - List view with pagination, detail view with tabs (Summary, Request, XML, Response, Troubleshooting)
- **API Playground** - Interactive endpoint testing with templates, syntax highlighting, and response viewer
- **Billing & Subscription** - Usage meters, plan management, and subscription details
- **Dashboard** - Overview with stats, system status, and recent invoices

**UX Enhancements:**

- **Skeleton Loaders** - No blank screens; professional loading states for all pages
- **Empty States** - Friendly empty states with clear CTAs and icons
- **Error Handling** - User-friendly error messages with retry buttons
- **Form Validation** - Comprehensive client-side validation with inline error messages
- **Responsive Design** - Mobile, tablet, and desktop optimized
- **RTL Support** - Full Arabic/RTL language support

**Testing:**

- Comprehensive `data-testid` coverage for E2E testing
- Playwright test suite included
- All user flows tested and verified

See [`docs/UI_IMPLEMENTATION_SUMMARY.md`](docs/UI_IMPLEMENTATION_SUMMARY.md) for complete UI implementation details.

### Docker Setup

```bash
# From project root
cd infra
docker-compose up -d
```

### Environment Variables

Create a `.env` file in the `backend` directory with the following variables:

```bash
# Application
ENVIRONMENT_NAME=development  # or production
DEBUG=true  # false in production
ENABLE_DOCS=true  # false in production

# API Security
API_KEYS=test-key,prod-key-1,prod-key-2  # Comma-separated list

# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/zatca_ai
# For SQLite (development only):
# DATABASE_URL=sqlite:///./zatca.db

# ZATCA Configuration
ZATCA_ENV=SANDBOX  # or PRODUCTION
ZATCA_SANDBOX_BASE_URL=https://gw-apic-gov.gazt.gov.sa/e-invoicing/developer-portal
ZATCA_PRODUCTION_BASE_URL=https://gw-apic-gov.gazt.gov.sa/e-invoicing/core
ZATCA_TIMEOUT=30
ZATCA_MAX_RETRIES=3

# AI Services (Optional)
ENABLE_AI_EXPLANATION=true  # Set to false to disable globally
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_DEFAULT_MODEL=openai/gpt-4o-mini
OPENROUTER_TIMEOUT=60
```

See [`docs/PRODUCTION_READINESS.md`](docs/PRODUCTION_READINESS.md) for complete environment variable checklist.

### Initial Configuration

1. **Set up tenant** (company, VAT number, environment)
2. **Configure API keys** (tenant-scoped authentication)
3. **Upload certificates** (Phase-2 signing certificates)
4. **Start processing invoices** (Phase-1 or Phase-2)
5. **Enable AI intelligence** (optional, advisory-only features)

---

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install -r backend/requirements.txt

# Run all tests (from project root)
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/backend/test_health.py -v

# Run tests matching a pattern
pytest -k "test_ai" -v

# Using test runner scripts (from project root)
# Linux/Mac:
./scripts/run_tests.sh

# Windows:
scripts\run_tests.bat
```

### Test Coverage

```bash
# Run tests with coverage report (terminal)
pytest --cov=backend.app --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=backend.app --cov-report=html

# View HTML report (opens in browser)
# Open htmlcov/index.html

# Generate coverage report with specific threshold
pytest --cov=backend.app --cov-report=term-missing --cov-fail-under=80
```

### Coverage Reports

- **Terminal Report**: Shows coverage percentage and missing lines
- **HTML Report**: Detailed interactive report in `htmlcov/index.html`
- **XML Report**: Machine-readable report in `coverage.xml` (for CI/CD)

### Test Structure

```
tests/
├── backend/
│   ├── conftest.py              # Shared fixtures
│   ├── test_health.py            # Health check tests
│   ├── test_tenant_auth.py       # Authentication tests
│   ├── test_invoices.py          # Invoice processing tests
│   ├── test_errors_rule_based.py # Error explanation tests
│   ├── test_ai_phase3.py         # AI Phase-3 tests (3.1-3.5)
│   ├── test_ai_governance.py     # AI governance tests
│   └── test_subscription_limits.py # Subscription limit tests
└── pytest.ini                    # Test configuration
```

### Coverage Configuration

Coverage settings are configured in `.coveragerc`:
- Excludes test files, migrations, and virtual environments
- Enables branch coverage
- Configures HTML and XML report generation

### End-to-End Testing (Playwright)

The project includes comprehensive E2E tests using Playwright:

```bash
# Navigate to frontend directory
cd frontend

# Install Playwright browsers (first time only)
npx playwright install

# Run E2E tests
npx playwright test

# Run specific test suite
npx playwright test e2e/auth.spec.ts
npx playwright test e2e/invoice.spec.ts
npx playwright test e2e/playground.spec.ts

# Run tests in UI mode (interactive)
npx playwright test --ui

# Run tests in headed mode (see browser)
npx playwright test --headed

# Generate test report
npx playwright show-report
```

**E2E Test Coverage:**
- Authentication flows (5 tests)
- Invoice management (4 tests)
- API Playground (3 tests)
- Smoke tests for critical paths
- UI component testing with data-testids

**Frontend Test Commands:**

```bash
# Run all E2E tests
npm run test:e2e

# Run tests with UI mode (interactive)
npm run test:e2e:ui

# Run tests in headed mode (see browser)
npm run test:e2e:headed

# Run linter
npm run lint

# Build for production
npm run build
```

See [`docs/PLAYWRIGHT_E2E_ANALYSIS.md`](docs/PLAYWRIGHT_E2E_ANALYSIS.md) for detailed testing guide.
See [`docs/UI_IMPLEMENTATION_TEST_CHECKLIST.md`](docs/UI_IMPLEMENTATION_TEST_CHECKLIST.md) for comprehensive UI testing checklist.

### Smoke Tests

Quick smoke tests to verify application status:

```bash
# Check backend health
curl http://localhost:8000/api/v1/system/health

# Check backend with API key
curl -H "X-API-Key: test-key" http://localhost:8000/api/v1/tenants/me

# Check frontend
curl https://zat-pri.vercel.app/
```

See [`docs/SMOKE_TEST_COMMANDS.md`](docs/SMOKE_TEST_COMMANDS.md) for complete smoke test reference.

---

## 🔌 API Endpoints

### Core Invoice APIs

- `POST /api/v1/invoices` - Process invoice (Phase-1 or Phase-2) with full persistence
- `GET /api/v1/invoices` - List invoices with pagination and filtering
- `GET /api/v1/invoices/{invoice_id}` - Get invoice details (with full metadata)
- `GET /api/v1/invoices/{invoice_number}/status` - Get invoice status

### Reporting APIs

- `GET /api/v1/reports/invoices` - Invoice report with filtering (status, phase, date range)
- `GET /api/v1/reports/vat-summary` - VAT summary with period-based aggregation
- `GET /api/v1/reports/status-breakdown` - Invoice status breakdown and counts

### AI Intelligence APIs

- `POST /api/v1/ai/explain-zatca-error` - Explain ZATCA error codes (bilingual)
- `POST /api/v1/ai/predict-rejection` - Predict invoice rejection risk
- `POST /api/v1/ai/precheck-advisor` - Pre-check invoice for risks
- `POST /api/v1/ai/root-cause-analysis` - Analyze failure root causes
- `GET /api/v1/ai/readiness-score` - Get tenant compliance readiness score
- `GET /api/v1/ai/error-trends` - Get error trend analysis

### Subscription & Billing

- `GET /api/v1/plans/current` - Get current subscription plan
- `GET /api/v1/plans/usage` - Get usage statistics

### System & Health

- `GET /api/v1/health` - Health check endpoint
- `GET /api/v1/system/health` - Detailed system health

### Certificate Management

- `POST /api/v1/certificates/upload` - Upload certificate and private key (per tenant, per environment)
- `GET /api/v1/certificates` - List certificates for current tenant
- Certificate validation (format, expiry) on upload
- Automatic deactivation of old certificates on new upload

### API Playground

- `GET /api/v1/playground/templates` - Get request templates
- Interactive playground available at `/api-playground` route in frontend

**Authentication:** All endpoints (except health checks) require `X-API-Key` header.

---

## 🎮 API Playground

The platform includes an interactive API Playground (similar to Stripe and ClearTax) for testing endpoints:

- **Access:** Navigate to `/api-playground` in the frontend
- **Features:**
  - Select from categorized endpoints
  - Pre-filled request templates
  - Real-time request/response display
  - cURL command generation
  - Automatic API key injection
  - Formatted JSON responses

See [`docs/API_PLAYGROUND.md`](docs/API_PLAYGROUND.md) for detailed documentation.

---

## 📞 Support

For enterprise inquiries, compliance questions, or technical support, please contact our team.

---

---

## 🎯 Current Status

**FATURAIX** is production-ready with:

✅ **Phase-1 & Phase-2 Compliance** - Full ZATCA e-invoicing support  
✅ **Invoice Persistence** - Enterprise-grade invoice master table with audit trails  
✅ **Reporting APIs** - Invoice and VAT analytics  
✅ **Multi-Tenant Architecture** - Complete tenant isolation  
✅ **Production-Ready UI** - React + TypeScript dashboard  
✅ **Certificate Management** - Per-tenant, per-environment certificate handling  
✅ **Subscription System** - Plans, limits, usage tracking  
✅ **AI Intelligence** - Advisory-only AI features (optional)  
✅ **Comprehensive Testing** - Full test coverage with E2E tests  
✅ **ZATCA Approval Ready** - All compliance requirements implemented  

See [`docs/ZATCA_APPROVAL_GUIDE.md`](docs/ZATCA_APPROVAL_GUIDE.md) for complete ZATCA approval checklist.

---

**Built for Saudi Arabia. Designed for Enterprise. Powered by Responsible AI.**

**FATURAIX** - Your Complete ZATCA E-Invoicing Solution
