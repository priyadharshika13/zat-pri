# Playwright E2E Test Troubleshooting Guide

## Common Issues and Solutions

### Issue: Tests Fail with "ECONNREFUSED" or "http proxy error"

**Symptoms:**
- Tests fail immediately (3-20ms)
- Error: `http proxy error: /api-playground`
- Error: `AggregateError [ECONNREFUSED]`
- 7 failed tests, 5 passed

**Root Cause:**
The backend API server is not running. The frontend dev server proxies `/api` requests to `http://localhost:8000`, but the backend isn't available.

**Solution:**

#### Option 1: Automatic (Recommended)
Playwright will automatically start the backend server. Just run:
```bash
cd frontend
npm run test:e2e
```

The config will start both frontend and backend servers automatically.

#### Option 2: Manual Start
If automatic startup fails, start the backend manually:

**Linux/Mac (Codespaces):**
```bash
cd backend
# Ensure PostgreSQL is running and database exists
createdb zatca_ai  # or: psql -U postgres -c "CREATE DATABASE zatca_ai;"
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/zatca_ai"
bash run_test_server.sh
```

**Windows:**
```bash
cd backend
# Ensure PostgreSQL is running and database exists
# Using psql: psql -U postgres -c "CREATE DATABASE zatca_ai;"
set DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/zatca_ai
run_test_server.bat
```

Then in another terminal:
```bash
cd frontend
npm run test:e2e
```

### Issue: Backend Server Fails to Start

**Symptoms:**
- `ModuleNotFoundError` when starting backend
- `DATABASE_URL not set` warnings
- Backend exits immediately

**Solutions:**

1. **Install Python Dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set DATABASE_URL (PostgreSQL):**
   ```bash
   # Linux/Mac
   export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/zatca_ai"
   
   # Windows PowerShell
   $env:DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/zatca_ai"
   
   # Windows CMD
   set DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/zatca_ai
   ```
   
   **Note:** Make sure PostgreSQL is running and the database exists:
   ```bash
   # Create database if needed
   createdb zatca_ai
   # Or using psql
   psql -U postgres -c "CREATE DATABASE zatca_ai;"
   ```

3. **Check Virtual Environment:**
   ```bash
   # Activate venv if using one
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

### Issue: Tests Timeout Waiting for Servers

**Symptoms:**
- Tests hang for 2+ minutes
- Timeout errors in Playwright output

**Solutions:**

1. **Increase Timeout (if needed):**
   Edit `frontend/playwright.config.ts`:
   ```typescript
   webServer: [
     {
       // ...
       timeout: 180 * 1000, // Increase from 120 to 180 seconds
     },
   ],
   ```

2. **Check Port Availability:**
   ```bash
   # Check if ports are in use
   lsof -i :8000  # Linux/Mac
   netstat -ano | findstr :8000  # Windows
   ```

3. **Kill Existing Processes:**
   ```bash
   # Linux/Mac
   kill -9 $(lsof -t -i:8000)
   kill -9 $(lsof -t -i:5173)
   
   # Windows
   taskkill /F /PID <process_id>
   ```

### Issue: Authentication Tests Fail

**Symptoms:**
- `should accept valid API key` fails
- `should reject invalid API key` fails
- Tests redirect to login unexpectedly

**Solutions:**

1. **Check API Key Mocking:**
   Tests use mocked API responses. Verify `auth.setup.ts` has correct mocks:
   ```typescript
   await page.route(`${API_BASE_URL}/api/v1/plans/usage`, async (route) => {
     // Should return 200 for valid key
   });
   ```

2. **Verify Storage State:**
   Check that `e2e/.auth/state.json` is created after setup:
   ```bash
   ls -la frontend/e2e/.auth/state.json
   ```

3. **Clear and Re-run Setup:**
   ```bash
   rm -rf frontend/e2e/.auth
   npm run test:e2e
   ```

### Issue: Playground Tests Fail

**Symptoms:**
- `should load playground page` fails
- `should display endpoint selector` fails
- Error: `http proxy error: /api-playground`

**Solutions:**

1. **Backend Must Be Running:**
   The playground makes real API calls. Ensure backend is running:
   ```bash
   # Check backend health
   curl http://localhost:8000/api/v1/system/health
   ```

2. **Check API Mocking:**
   Some tests mock API calls. Verify mocks are set up correctly in test files.

### Issue: Tests Pass Locally But Fail in CI

**Symptoms:**
- Tests work on your machine
- Fail in GitHub Actions or Codespaces

**Solutions:**

1. **Check Environment Variables:**
   CI might need explicit env vars:
   ```yaml
   # .github/workflows/e2e-tests.yml
   env:
     DATABASE_URL: postgresql+psycopg2://postgres:postgres@localhost:5432/zatca_ai
   ```

2. **Verify Server Startup:**
   CI might need longer timeouts or different commands.

3. **Check Browser Installation:**
   ```bash
   npx playwright install --with-deps chromium
   ```

## Quick Diagnostic Commands

### Check Backend Health
```bash
curl http://localhost:8000/api/v1/system/health
# Should return: {"status":"healthy",...}
```

### Check Frontend
```bash
curl https://zat-pri.vercel.app/
# Should return HTML
```

### Check Test Configuration
```bash
cd frontend
npx playwright test --list
# Should list all tests
```

### Run Single Test for Debugging
```bash
cd frontend
npx playwright test auth.spec.ts --headed
# Opens browser so you can see what's happening
```

## Expected Test Results

**When Everything Works:**
- ✅ Setup test passes (authenticates)
- ✅ 5-7 authentication tests pass
- ✅ 3-4 invoice tests pass
- ✅ 2-3 playground tests pass
- **Total: 10-12 tests passing**

**Common Failure Patterns:**
- **All tests fail immediately (3-20ms):** Backend not running
- **Auth tests fail:** API mocking issue or storage state problem
- **Playground tests fail:** Backend API not accessible
- **Tests timeout:** Server startup issue

## Getting Help

1. **Check Test Output:**
   ```bash
   npm run test:e2e > test-output.log 2>&1
   ```

2. **View HTML Report:**
   After tests run, open the HTML report:
   ```bash
   # Report is automatically opened, or:
   npx playwright show-report
   ```

3. **Check Screenshots:**
   Failed tests save screenshots in `frontend/test-results/`

4. **Enable Trace:**
   Edit `playwright.config.ts`:
   ```typescript
   use: {
     trace: 'on', // Always capture trace
   },
   ```

## Related Documentation

- [E2E Tests README](../frontend/e2e/README.md) - Test structure and usage
- [Playwright Auth Setup](./PLAYWRIGHT_AUTH_SETUP.md) - Authentication setup
- [Playwright Container Setup](./PLAYWRIGHT_CONTAINER_SETUP.md) - Running in containers

