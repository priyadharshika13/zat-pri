# API Key Authentication & Security

**ZATCA e-Invoicing Compliance API** — Production-grade API Key (X-API-Key) authentication for machine-to-machine SaaS integrations (ERP, POS, accounting systems). No human users; no JWT or session-based auth in production.

---

## 1. Authentication Strategy

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| **Mechanism** | **X-API-Key** (header) | Single header, no token expiry, easy for M2M and Swagger. |
| **Scope** | Per tenant | Each key maps to one tenant; all data and limits are tenant-scoped. |
| **Enforcement** | Dependency on every protected route | `verify_api_key_and_resolve_tenant` → 401 if missing/invalid. |
| **Public endpoints** | `/`, `/api/v1/health`, `/api/v1/system/health`, `/api/v1/auth/login` (dev only) | No API key required. |
| **Production** | No login; no API key minting via API | Keys are issued via dashboard/support; login disabled when `ENVIRONMENT_NAME != local`. |

- **All protected endpoints** require `X-API-Key`.
- **Requests without a valid key** return **401 Unauthorized** with `{"detail": "API key is required"}` or `{"detail": "Invalid or inactive API key"}`.
- **API keys are validated per tenant**: key → `ApiKey` → `Tenant`; tenant must be active.

---

## 2. FastAPI Configuration

### 2.1 OpenAPI / Swagger

- **Authorize button**: Shown in Swagger UI via custom OpenAPI schema that registers security scheme `ApiKeyAuth` (type `apiKey`, in `header`, name `X-API-Key`).
- **Usage**: Click **Authorize**, enter your API key once; it is sent with every request from Swagger.
- **Implementation**: `_register_openapi_security(application)` in `main.py` adds `components.securitySchemes.ApiKeyAuth` and `security: [{"ApiKeyAuth": []}]` to the generated OpenAPI schema.

### 2.2 Protected Endpoints

Every protected route uses the same dependency:

```python
from fastapi import APIRouter, Depends
from typing import Annotated
from app.core.security import verify_api_key_and_resolve_tenant
from app.schemas.auth import TenantContext

router = APIRouter()

@router.post("/invoices")
async def create_invoice(
    tenant: Annotated[TenantContext, Depends(verify_api_key_and_resolve_tenant)],
    body: InvoiceRequest,
):
    # tenant.tenant_id, tenant.company_name, tenant.vat_number, tenant.environment
    ...
```

- **401** is raised inside `verify_api_key_and_resolve_tenant` when the key is missing, invalid, or tenant inactive.
- **Tenant context** is attached to `request.state.tenant` for use in services.

### 2.3 Public Endpoints (No API Key)

- `GET /` — API info
- `GET /api/v1/health` — Health check
- `GET /api/v1/system/health` — System health
- `POST /api/v1/auth/login` — **Local dev only**; returns 404 in production

---

## 3. /auth/login — Local Development & Swagger Only

- **Purpose**: Obtain an API key for local testing and Swagger; not for production.
- **Production**: Endpoint returns **404** when `ENVIRONMENT_NAME` is not `local`. No API keys are minted via login in production.
- **Behaviour**:
  - `ENVIRONMENT_NAME=local` → login enabled; returns first active API key for an active tenant (simplified MVP).
  - `ENVIRONMENT_NAME=dev` or `production` → **404**; no key issuance.

```python
# auth.py (already implemented)
if settings.environment_name.lower() != "local":
    raise HTTPException(status_code=404, detail="Endpoint not found")
```

---

## 4. Best Practices (Stripe-, OpenAI-, ZATCA-style)

### 4.1 API Key Rotation Readiness

- Keys are stored in `api_keys` with `is_active`. Rotate by creating a new key, switching clients to it, then deactivating the old key.
- `last_used_at` is updated on each use to support usage monitoring and safe retirement of old keys.
- No expiry field required for static M2M keys; optional expiry can be added later without changing the auth flow.

### 4.2 Rate Limiting per API Key

- **RateLimitMiddleware** enforces limits **per tenant** (each API key maps to one tenant). Limits come from subscription plan (e.g. requests per minute). Effectively **rate limiting per API key**.

### 4.3 Audit Logging per Key

- **AuditMiddleware** logs every request/response and, after the route runs, logs **tenant_id** when `request.state.tenant` is set (i.e. when the request was authenticated by API key). So every authenticated call is audited with `tenant_id` (per key/tenant).

---

## 5. Security Rationale: API Key vs JWT

| Criterion | API Key (X-API-Key) | JWT |
|-----------|---------------------|-----|
| **Use case** | M2M, server-to-server, fixed clients | Often used for user sessions, short-lived tokens |
| **Complexity** | Single header; no refresh flow | Issuer, expiry, refresh, key distribution |
| **Revocation** | Revoke key in DB; immediate effect | Blacklist or short expiry; more moving parts |
| **ZATCA / compliance** | Simple audit: one key = one tenant | Token lifecycle and claims add complexity |
| **Stripe / OpenAI** | Primary auth for API access | Not used for core API auth |
| **Leak impact** | Key can be rotated; scope limited to one tenant | Token can be replayed until expiry |

**Why API Key for this API:**

- **Machine-to-machine**: Callers are ERPs, POS, accounting systems — not browsers with cookies. A long-lived API key per tenant is standard.
- **Operational simplicity**: No token endpoint, no refresh, no clock skew issues; easier to run and debug.
- **Compliance and audit**: One key per tenant; rate limits and audit logs are naturally per tenant/key.
- **Industry alignment**: Stripe, OpenAI, Twilio, and many ZATCA-style compliance APIs use API keys as the primary auth for API access.

---

## 6. Example: Calling the API

### 6.1 cURL

```bash
curl -X POST "https://api.example.com/api/v1/invoices" \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"mode": "PHASE_2", "environment": "sandbox", ...}'
```

### 6.2 Swagger UI

1. Open `/docs` (when enabled).
2. Click **Authorize**.
3. Enter your API key in **X-API-Key**.
4. Click **Authorize**, then **Close**.
5. All subsequent requests from Swagger include the key.

### 6.3 401 Responses

- Missing key: `{"detail": "API key is required"}`  
- Invalid or inactive key: `{"detail": "Invalid or inactive API key"}`  
- Inactive tenant: `{"detail": "Tenant associated with API key is inactive"}`  

---

## 7. Summary

- **Auth**: X-API-Key only; validated per tenant via `verify_api_key_and_resolve_tenant`.
- **Swagger**: Authorize button and single key entry via OpenAPI security scheme.
- **Login**: Dev-only; disabled in production; no key minting in production.
- **Rotation**: Supported by active/inactive keys and `last_used_at`.
- **Rate limiting**: Per tenant (per API key) via subscription plans.
- **Audit**: Per request/response with `tenant_id` when authenticated.

This keeps the API simple, secure, and suitable for ZATCA-style compliance and production SaaS use.
