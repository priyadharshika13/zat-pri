# PostgreSQL E2E Configuration Verification Report

**Date:** 2026-01-19  
**Status:** ⚠️ **BLOCKERS IDENTIFIED - DO NOT PROCEED WITHOUT FIXES**

---

## 1. Backend Configuration Analysis

### ✅ DATABASE_URL Loading Mechanism

**Location:** `backend/app/db/session.py` (lines 28-56)

**Priority Order:**
1. `DATABASE_URL` environment variable (checked first)
2. `settings.database_url` from Pydantic Settings
3. Raises `ValueError` if neither is set (unless in pytest mode)

**Current State:**
- ✅ Correctly configured to read from environment
- ✅ No hardcoded fallbacks (except pytest detection)
- ✅ PostgreSQL connection string format expected

### ❌ Current Database Usage

**Normal Dev:**
- **Expected:** PostgreSQL (via `DATABASE_URL` env var)
- **Reality:** ⚠️ **UNKNOWN** - Depends on user setting `DATABASE_URL`
- **Default:** ❌ **NONE** - Will raise `ValueError` if not set

**E2E Tests:**
- **Expected:** PostgreSQL (per recent changes)
- **Configured in:** 
  - `backend/run_test_server.sh` (line 11): `postgresql+psycopg2://postgres:postgres@localhost:5432/zatca_ai`
  - `backend/run_test_server.bat` (line 11): Same
  - `frontend/playwright.config.ts` (line 60): Same default
- **Reality:** ⚠️ **WILL FAIL** - PostgreSQL service not available in Codespaces/CI

### ⚠️ Seeding Logic

**Location:** `backend/app/services/tenant_seed_service.py` (lines 80-104)

**Critical Finding:**
```python
if environment.lower() not in ("local", "dev", "development"):
    logger.info(f"Skipping tenant seeding - not in local/dev environment (current: {environment})")
    return
```

**Current Configuration:**
- `ENVIRONMENT=sandbox` (set in test scripts)
- `environment_name="local"` (default in `config.py` line 35)
- **Seeding will run** if `environment_name` is "local", "dev", or "development"
- **Seeding creates:** `test-key` API key (required for E2E auth)

**Risk:** If `ENVIRONMENT_NAME` is not set to "local"/"dev"/"development", seeding will be skipped and E2E tests will fail (no `test-key`).

---

## 2. Frontend E2E Setup Analysis

### ✅ Playwright Configuration

**File:** `frontend/playwright.config.ts`

**Backend Server Startup:**
- ✅ Uses `run_test_server.sh` / `run_test_server.bat`
- ✅ Sets `DATABASE_URL` in `webServer.env` (line 60)
- ✅ Sets `ENVIRONMENT=sandbox` (line 61)
- ⚠️ **MISSING:** `ENVIRONMENT_NAME` not set (seeding may fail)

**Default DATABASE_URL:**
```typescript
DATABASE_URL: process.env.DATABASE_URL || 'postgresql+psycopg2://postgres:postgres@localhost:5432/zatca_ai'
```

**Issue:** Assumes PostgreSQL is running on `localhost:5432` with default credentials.

### ❌ E2E Test Expectations

**Auth Setup:** `frontend/e2e/auth.setup.ts`
- ✅ Uses `test-key` API key (matches backend seed)
- ✅ Assumes backend is running and seeded
- ⚠️ **Will fail** if:
  - PostgreSQL not running
  - Database not created
  - Seeding didn't run (no `test-key` exists)

---

## 3. Codespaces Setup Analysis

### ❌ Missing PostgreSQL Service

**Findings:**
- ❌ No `docker-compose.yml` in root (only in `infra/` for production)
- ❌ No `.devcontainer.json` or `devcontainer.json`
- ❌ No PostgreSQL service definition for development
- ❌ No database initialization scripts

**Current `infra/docker-compose.yml`:**
- Only defines `zatca-api` service
- Uses SQLite volume mount (`zatca.db`)
- **NOT suitable for E2E tests**

### ⚠️ GitHub Actions CI

**File:** `.github/workflows/e2e-tests.yml`

**Critical Issues:**
- ❌ **No PostgreSQL service setup**
- ❌ **No DATABASE_URL environment variable**
- ❌ **No database creation/migration steps**
- ❌ **Tests will fail** when backend tries to connect to PostgreSQL

**Current Steps:**
1. Checkout code
2. Setup Node.js
3. Install dependencies
4. Install Playwright
5. Build frontend
6. Run E2E tests ← **WILL FAIL HERE**

**Missing Steps:**
- Setup PostgreSQL service
- Create database
- Run migrations
- Set DATABASE_URL

---

## 4. Identified Blockers

### 🔴 CRITICAL BLOCKERS

#### Blocker #1: PostgreSQL Service Not Available
**Location:** Codespaces, GitHub Actions CI  
**Impact:** Backend cannot start, E2E tests fail immediately  
**Evidence:**
- No PostgreSQL container/service defined
- No database initialization
- Tests assume `localhost:5432` PostgreSQL exists

#### Blocker #2: Database Not Created
**Location:** All environments  
**Impact:** Migrations fail, seeding fails, API key verification fails  
**Evidence:**
- `run_test_server.sh` runs `alembic upgrade head` but database may not exist
- No `createdb` or `CREATE DATABASE` step in scripts

#### Blocker #3: ENVIRONMENT_NAME Not Set for Seeding
**Location:** `frontend/playwright.config.ts`  
**Impact:** Tenant seeding skipped, `test-key` not created, auth fails  
**Evidence:**
- `seed_tenants_if_needed()` checks `environment_name`
- Default is "local" but not explicitly set in E2E config
- If environment_name is "sandbox" or other, seeding is skipped

#### Blocker #4: Wrong Host in Codespaces
**Location:** Codespaces environment  
**Impact:** Cannot connect to PostgreSQL  
**Evidence:**
- Connection string uses `localhost:5432`
- In Codespaces, PostgreSQL might be on different host
- No service discovery mechanism

### ⚠️ MEDIUM RISKS

#### Risk #1: Credentials Hardcoded
**Location:** Test scripts  
**Impact:** Security risk, may not match actual PostgreSQL setup  
**Evidence:**
- Default: `postgres:postgres@localhost:5432`
- May not match user's PostgreSQL configuration

#### Risk #2: Migration Failure Handling
**Location:** `run_test_server.sh` (line 24)  
**Impact:** Server starts with broken database state  
**Evidence:**
- `|| echo "Warning: Migrations may have failed, continuing anyway..."`
- Non-blocking migration failures can cause silent issues

---

## 5. Current State Summary

### ✅ What Works Now

1. **Backend Configuration:**
   - ✅ Correctly reads `DATABASE_URL` from environment
   - ✅ Supports PostgreSQL connection strings
   - ✅ Proper error handling for missing DATABASE_URL

2. **Test Scripts:**
   - ✅ Default to PostgreSQL connection string
   - ✅ Can be overridden via `DATABASE_URL` env var
   - ✅ Run migrations before starting server

3. **Seeding Logic:**
   - ✅ Creates `test-key` API key when environment is "local"/"dev"
   - ✅ Non-blocking (logs warning if fails)

### ❌ What Doesn't Work

1. **PostgreSQL Service:**
   - ❌ Not available in Codespaces
   - ❌ Not available in GitHub Actions CI
   - ❌ No setup/installation steps

2. **Database Initialization:**
   - ❌ Database may not exist
   - ❌ No `CREATE DATABASE` step
   - ❌ Migrations assume database exists

3. **Environment Configuration:**
   - ❌ `ENVIRONMENT_NAME` not set in E2E config
   - ❌ Seeding may be skipped
   - ❌ `test-key` may not be created

4. **CI/CD Pipeline:**
   - ❌ No PostgreSQL service in GitHub Actions
   - ❌ No database setup steps
   - ❌ Tests will fail immediately

---

## 6. Risks if Proceeding Without Fixes

### 🔴 Immediate Failures

1. **E2E Tests Will Fail:**
   - Backend cannot start (no PostgreSQL connection)
   - Error: `ValueError: DATABASE_URL must be set` OR connection refused
   - Tests timeout waiting for backend health check

2. **Auth Setup Will Fail:**
   - No `test-key` API key (seeding didn't run or failed)
   - `auth.setup.ts` cannot authenticate
   - All other tests skipped

3. **CI Pipeline Will Fail:**
   - GitHub Actions has no PostgreSQL service
   - All E2E test runs will fail
   - No way to pass CI checks

### ⚠️ Silent Issues

1. **Wrong Database:**
   - If SQLite fallback somehow works, tests run against wrong DB
   - Inconsistent behavior between environments
   - Production issues not caught

2. **Missing Data:**
   - Seeding skipped → no test data
   - Tests may pass but don't test real scenarios
   - False confidence in test coverage

---

## 7. Recommendations

### ❌ **CANNOT PROCEED AS-IS**

The current configuration **will fail** in:
- ✅ Local (if PostgreSQL not installed/running)
- ❌ Codespaces (PostgreSQL not available)
- ❌ GitHub Actions CI (PostgreSQL not available)

### ✅ **REQUIRED FIXES BEFORE ENABLING POSTGRESQL FOR E2E**

#### Fix #1: Add PostgreSQL Service to Codespaces
**Priority:** 🔴 CRITICAL  
**Action:** Create `.devcontainer.json` or add PostgreSQL to docker-compose

**Options:**
- **Option A:** Add PostgreSQL service to `docker-compose.yml`
- **Option B:** Create `.devcontainer.json` with PostgreSQL service
- **Option C:** Document manual PostgreSQL installation in Codespaces

#### Fix #2: Add PostgreSQL Service to GitHub Actions
**Priority:** 🔴 CRITICAL  
**Action:** Add PostgreSQL service container to `.github/workflows/e2e-tests.yml`

**Required:**
```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: zatca_ai
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
    ports:
      - 5432:5432
```

#### Fix #3: Add Database Creation Step
**Priority:** 🔴 CRITICAL  
**Action:** Add `CREATE DATABASE` step before migrations

**Location:** `backend/run_test_server.sh` and `.bat`

**Required:**
```bash
# Create database if it doesn't exist
psql -U postgres -h localhost -c "CREATE DATABASE zatca_ai;" || true
```

#### Fix #4: Set ENVIRONMENT_NAME for Seeding
**Priority:** 🟡 HIGH  
**Action:** Add `ENVIRONMENT_NAME=local` to E2E config

**Location:** `frontend/playwright.config.ts` (line 59-62)

**Required:**
```typescript
env: {
  DATABASE_URL: process.env.DATABASE_URL || 'postgresql+psycopg2://postgres:postgres@localhost:5432/zatca_ai',
  ENVIRONMENT: 'sandbox',
  ENVIRONMENT_NAME: 'local', // ← ADD THIS
},
```

#### Fix #5: Update GitHub Actions Workflow
**Priority:** 🔴 CRITICAL  
**Action:** Add PostgreSQL service and database setup

**Required Steps:**
1. Add `services.postgres` section
2. Set `DATABASE_URL` environment variable
3. Wait for PostgreSQL to be ready
4. Create database
5. Run migrations

---

## 8. Implementation Order

### Phase 1: Local Development (Can Test Immediately)
1. ✅ Verify PostgreSQL is installed locally
2. ✅ Create database: `createdb zatca_ai`
3. ✅ Set `DATABASE_URL` environment variable
4. ✅ Run migrations: `alembic upgrade head`
5. ✅ Test E2E locally

### Phase 2: Codespaces (Required for Development)
1. ❌ Add PostgreSQL service (docker-compose or devcontainer)
2. ❌ Add database creation step to test scripts
3. ❌ Set `ENVIRONMENT_NAME=local` in Playwright config
4. ✅ Test in Codespaces

### Phase 3: CI/CD (Required for Production)
1. ❌ Add PostgreSQL service to GitHub Actions
2. ❌ Add database setup steps
3. ❌ Set all required environment variables
4. ✅ Verify CI pipeline passes

---

## 9. Verification Checklist

Before enabling PostgreSQL for E2E, verify:

- [ ] PostgreSQL service available in Codespaces
- [ ] PostgreSQL service available in GitHub Actions
- [ ] Database creation step in test scripts
- [ ] `ENVIRONMENT_NAME=local` set in E2E config
- [ ] Migrations run successfully
- [ ] Seeding creates `test-key` API key
- [ ] Backend health check passes
- [ ] `auth.setup.ts` completes successfully
- [ ] All E2E tests pass in local environment
- [ ] All E2E tests pass in Codespaces
- [ ] All E2E tests pass in GitHub Actions CI

---

## 10. Conclusion

**Current Status:** ⚠️ **NOT READY FOR POSTGRESQL E2E**

**Blockers:** 4 critical issues preventing successful E2E tests with PostgreSQL

**Recommendation:** **DO NOT PROCEED** until all critical blockers are resolved.

**Next Steps:**
1. Implement Fix #1 (PostgreSQL service in Codespaces)
2. Implement Fix #2 (PostgreSQL service in GitHub Actions)
3. Implement Fix #3 (Database creation step)
4. Implement Fix #4 (ENVIRONMENT_NAME for seeding)
5. Implement Fix #5 (Update GitHub Actions workflow)
6. Test in all environments
7. Verify all checklist items

**Estimated Effort:** 2-4 hours for all fixes

**Risk Level:** 🔴 **HIGH** - Tests will fail immediately without fixes

