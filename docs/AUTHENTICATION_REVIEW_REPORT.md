# Authentication & API Key Usage Review Report

**Date:** 2026-01-19  
**Scope:** Complete analysis of `test-key` and OpenRouter API key usage  
**Status:** Analysis Complete - Recommendations Provided

---

## Executive Summary

This report analyzes the authentication architecture, focusing on:
1. **`test-key`** - Development/test API key usage and safeguards
2. **OpenRouter API Key** - AI service authentication and exposure risks
3. **Test Authentication** - How tests authenticate (backend & Playwright)
4. **Environment Separation** - Dev/test vs production safeguards

**Key Finding:** The current implementation is **mostly correct** but has **one critical gap**: `test-key` could theoretically work in production if it exists in the database, as there's no explicit guard preventing its use in production environments.

---

## 1. `test-key` Usage Analysis

### 1.1 Where `test-key` is Seeded

**Location:** `backend/app/services/tenant_seed_service.py`

**Function:** `seed_default_tenant()`
- Creates default tenant: "Demo Tenant", VAT: "000000000000003"
- Creates API key: `"test-key"` (if not exists)
- Uses get-or-create pattern to avoid duplicates

**Trigger:** `seed_tenants_if_needed()` called from `backend/app/main.py` on application startup (line 66)

**Environment Guard:**
```python
# backend/app/services/tenant_seed_service.py:89
if environment.lower() not in ("local", "dev", "development"):
    logger.info(f"Skipping tenant seeding - not in local/dev environment (current: {environment})")
    return
```

**Status:** ✅ **CORRECT** - Seeding only occurs when `ENVIRONMENT_NAME` is "local", "dev", or "development"

### 1.2 Where `test-key` is Validated

**Primary Validation:** `backend/app/core/security.py`

**Function:** `verify_api_key_and_resolve_tenant()` (lines 20-96)
- Extracts `X-API-Key` header from request
- Queries database for matching `ApiKey` record
- Validates:
  - API key exists in database
  - API key is active (`is_active == True`)
  - Associated tenant exists and is active
- Updates `last_used_at` timestamp
- Returns `TenantContext` for downstream use

**Legacy Fallback:** `verify_api_key()` (lines 100-150)
- First checks database (new multi-tenant approach)
- Falls back to `settings.valid_api_keys` (legacy config-based)
- **Note:** Legacy fallback still exists but is deprecated

**Status:** ✅ **CORRECT** - Database-driven validation with proper tenant resolution

### 1.3 Environment Restrictions

**Seeding Restriction:** ✅ **ENFORCED**
- `seed_tenants_if_needed()` checks `environment_name`
- Only seeds in "local", "dev", "development"

**Runtime Restriction:** ⚠️ **NOT ENFORCED**
- If `test-key` exists in production database (e.g., manually inserted or migrated), it will work
- No runtime check preventing `test-key` from being used in production
- Validation only checks database existence, not key name or environment

**Status:** ⚠️ **GAP IDENTIFIED** - Seeding is restricted, but runtime usage is not

---

## 2. OpenRouter API Key Usage

### 2.1 Configuration Loading

**Location:** `backend/app/core/config.py` (line 81)
```python
openrouter_api_key: Optional[str] = None
```

**Source:** Environment variable `OPENROUTER_API_KEY`
- Loaded via Pydantic Settings from `.env` file
- No hardcoded values
- Optional (can be `None`)

**Status:** ✅ **CORRECT** - Only loaded from environment variables

### 2.2 Usage Location

**Service:** `backend/app/services/ai/openrouter_service.py`

**Initialization:** `OpenRouterService.__init__()` (lines 30-52)
- Loads key from `settings.openrouter_api_key`
- Sets `Authorization: Bearer {api_key}` header
- Initializes `httpx.AsyncClient` with authentication headers
- **Critical:** Key is stored in instance variable, not exposed

**Usage:** `call_openrouter()` (lines 54-188)
- Makes outbound HTTP requests to `https://openrouter.ai/api/v1/chat/completions`
- Key is sent in `Authorization` header only
- Never returned in responses
- Never logged in plaintext (only error messages logged)

**Status:** ✅ **CORRECT** - Used only for outbound AI requests

### 2.3 Frontend Exposure

**Search Results:** No matches found for `OPENROUTER` or `openrouter` in `frontend/` directory

**Status:** ✅ **CONFIRMED** - OpenRouter API key is NOT exposed to frontend

### 2.4 Test Exposure

**Mocking Strategy:** `tests/backend/conftest_enhanced.py` (lines 271-287)
- Tests use `mock_openrouter_service` fixture
- Mocks `get_openrouter_service()` to return fake instance
- Never calls real OpenRouter API
- Test key value: `"test-openrouter-key"` (fake, not real)

**Status:** ✅ **CONFIRMED** - Tests mock OpenRouter, never call it directly

---

## 3. Test Authentication Patterns

### 3.1 Backend Tests (pytest)

**Fixture:** `tests/backend/conftest.py` (lines 316-336, 372-381)

**Pattern:**
1. `test_api_key` fixture creates `test-key` in test database
2. `headers` fixture provides `{"X-API-Key": "test-key"}`
3. Tests use `headers` fixture in API calls

**Example:**
```python
def test_tenant_resolution(client, headers):
    res = client.get("/api/v1/tenants/me", headers=headers)
    assert res.status_code == 200
```

**Status:** ✅ **CORRECT** - Tests use internal `test-key` via `X-API-Key` header

### 3.2 Playwright E2E Tests

**Setup:** `frontend/e2e/auth.setup.ts`

**Pattern:**
1. Injects `test-key` directly into `localStorage.setItem('api_key', 'test-key')`
2. Reloads page to trigger app authentication check
3. Waits for redirect to authenticated route
4. Saves authenticated state to `e2e/.auth/state.json`
5. All other tests use saved state automatically

**Configuration:** `frontend/playwright.config.ts` (lines 29-44)
- Setup project runs `auth.setup.ts` first
- Main test project depends on setup
- All tests use `storageState: 'e2e/.auth/state.json'`

**Backend Server:** `playwright.config.ts` (lines 48-66)
- Starts backend with `ENVIRONMENT_NAME=local` (line 64)
- Ensures seeding runs and `test-key` is created

**Status:** ✅ **CORRECT** - Tests authenticate using internal `test-key`, never call OpenRouter

---

## 4. Environment Separation

### 4.1 Development/Test Behavior

**Seeding:**
- ✅ Runs when `ENVIRONMENT_NAME=local` (default in `config.py:49`)
- ✅ Creates `test-key` in database
- ✅ Used by all tests (backend & Playwright)

**Login Endpoint:** `backend/app/api/v1/routes/auth.py`
- ✅ Disabled in non-local environments (line 54)
- ✅ Returns 404 if `ENVIRONMENT_NAME != "local"`
- ✅ Logs security warning when accessed

**Status:** ✅ **CORRECT** - Dev/test properly isolated

### 4.2 Production Safeguards

**Seeding:** ✅ **ENFORCED**
- `seed_tenants_if_needed()` skips if `environment_name` not in ("local", "dev", "development")

**Runtime Usage:** ⚠️ **NOT ENFORCED**
- No check preventing `test-key` from working in production if it exists in DB
- Could be manually inserted or migrated from dev database
- No validation that rejects `test-key` specifically in production

**Recommendation:** Add runtime guard to reject `test-key` in production environments

**Status:** ⚠️ **GAP IDENTIFIED** - Seeding is protected, but runtime usage is not

---

## 5. Risk Assessment

### 5.1 High Risk Issues

**None Identified** - Current implementation is secure for normal operations

### 5.2 Medium Risk Issues

**1. `test-key` Could Work in Production**
- **Risk:** If `test-key` exists in production database, it will authenticate
- **Likelihood:** Low (requires manual DB insertion or migration error)
- **Impact:** Medium (unauthorized access if key is known)
- **Mitigation:** Add runtime guard (see recommendations)

### 5.3 Low Risk Issues

**1. Legacy API Key Fallback**
- `verify_api_key()` still supports config-based keys
- Deprecated but not removed
- **Impact:** Low (only used if database lookup fails)

**2. OpenRouter Key in Logs**
- Error messages may include partial key info
- **Impact:** Low (only in error scenarios, not normal operation)

---

## 6. Architecture Summary

### Current Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Client Request                       │
│              (X-API-Key: test-key)                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         verify_api_key_and_resolve_tenant()              │
│  • Extracts X-API-Key header                             │
│  • Queries ApiKey table in database                      │
│  • Validates key exists and is active                    │
│  • Resolves tenant context                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Protected Endpoint                           │
│  • Uses TenantContext for tenant isolation               │
│  • May call OpenRouterService for AI features            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         OpenRouterService.call_openrouter()              │
│  • Uses OPENROUTER_API_KEY from environment               │
│  • Makes outbound request to OpenRouter                  │
│  • Never exposes key to client                           │
└─────────────────────────────────────────────────────────┘
```

### Key Components

1. **Authentication:** Database-driven, multi-tenant
2. **API Keys:** Stored in `ApiKey` table, validated per request
3. **OpenRouter:** Isolated service, environment-based config
4. **Tests:** Use `test-key` via fixtures/state injection

---

## 7. Recommendations

### 7.1 Critical: Add Production Guard for `test-key`

**Issue:** `test-key` could work in production if it exists in database

**Recommendation:** Add runtime validation in `verify_api_key_and_resolve_tenant()`:

```python
# After validating API key exists in database
if api_key_obj.api_key == "test-key":
    settings = get_settings()
    if settings.environment_name.lower() in ("production", "prod"):
        logger.warning(
            f"SECURITY: test-key attempted in production environment. "
            f"Tenant: {tenant_context.tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test API keys are not allowed in production"
        )
```

**Priority:** High  
**Effort:** Low (single validation check)

### 7.2 Medium: Remove Legacy API Key Fallback

**Issue:** `verify_api_key()` still supports config-based keys

**Recommendation:** 
1. Audit all endpoint dependencies
2. Replace `verify_api_key()` with `verify_api_key_and_resolve_tenant()`
3. Remove `verify_api_key()` function
4. Remove `settings.valid_api_keys` property

**Priority:** Medium  
**Effort:** Medium (requires endpoint audit)

### 7.3 Low: Add API Key Naming Convention

**Issue:** No validation for API key naming patterns

**Recommendation:** Add validation to reject keys matching test patterns:
- `test-*` keys in production
- `dev-*` keys in production
- Enforce naming conventions for production keys

**Priority:** Low  
**Effort:** Low

### 7.4 Low: Enhanced Logging

**Issue:** Limited visibility into API key usage patterns

**Recommendation:** Add structured logging for:
- API key usage by environment
- Failed authentication attempts
- OpenRouter API call metrics

**Priority:** Low  
**Effort:** Medium

---

## 8. Confirmation of Current Behavior

### ✅ Correct Behaviors

1. **`test-key` Seeding:** Only occurs in local/dev environments ✅
2. **OpenRouter Key Loading:** Only from environment variables ✅
3. **OpenRouter Usage:** Only for outbound AI requests ✅
4. **Frontend Exposure:** OpenRouter key never exposed ✅
5. **Test Authentication:** Tests use internal `test-key` ✅
6. **Test Isolation:** Tests mock OpenRouter, never call it ✅
7. **Login Endpoint:** Disabled in non-local environments ✅

### ⚠️ Gaps Identified

1. **Runtime Production Guard:** `test-key` could work in production if it exists in DB ⚠️
2. **Legacy Fallback:** Config-based API keys still supported (deprecated) ⚠️

---

## 9. Best Practice Gaps

### Current Gaps

1. **No explicit production guard for test keys**
   - Industry standard: Reject test keys in production
   - Current: Only seeding is restricted

2. **Legacy code still present**
   - `verify_api_key()` should be removed
   - Config-based keys should be deprecated

3. **No API key naming validation**
   - Should enforce naming conventions
   - Should reject test patterns in production

### Strengths

1. ✅ Database-driven authentication (scalable)
2. ✅ Multi-tenant isolation (secure)
3. ✅ Environment-based configuration (flexible)
4. ✅ Proper test mocking (no external calls)
5. ✅ OpenRouter properly isolated (no exposure)

---

## 10. Conclusion

The current authentication architecture is **well-designed and mostly secure**. The primary gap is the lack of a runtime guard preventing `test-key` from working in production if it exists in the database.

**Overall Assessment:** ✅ **GOOD** with minor improvements needed

**Recommended Actions:**
1. **Immediate:** Add production guard for `test-key` (High priority, Low effort)
2. **Short-term:** Remove legacy API key fallback (Medium priority, Medium effort)
3. **Long-term:** Add API key naming validation (Low priority, Low effort)

**Security Status:** ✅ **SECURE** for normal operations, with recommended hardening for edge cases

---

## Appendix: File References

### Key Files Analyzed

- `backend/app/services/tenant_seed_service.py` - Seeding logic
- `backend/app/core/security.py` - Authentication validation
- `backend/app/core/config.py` - Configuration management
- `backend/app/services/ai/openrouter_service.py` - OpenRouter integration
- `backend/app/main.py` - Application startup (seeding trigger)
- `tests/backend/conftest.py` - Backend test fixtures
- `frontend/e2e/auth.setup.ts` - Playwright authentication setup
- `frontend/playwright.config.ts` - Playwright configuration

### Search Patterns Used

- `grep -i "test-key"` - Found 35 matches
- `grep -i "openrouter"` - Found 13 matches
- `grep -i "verify_api_key"` - Found 31 matches in API routes

---

**Report Generated:** 2026-01-19  
**Next Review:** After implementing recommendations

