# E2E Tests - Playwright

## Overview

End-to-end tests for the ZATCA API Platform using Playwright. Tests are organized by feature area and use a shared authentication setup.

## Test Structure

```
e2e/
├── auth.setup.ts      # Authentication setup (runs once before all tests)
├── auth.spec.ts       # Authentication flow tests (login, logout, etc.)
├── invoice.spec.ts    # Invoice management tests
── playground.spec.ts  # API Playground tests
└── .auth/
    └── state.json     # Saved authenticated state (auto-generated)
```

## Authentication Setup

**Key Concept:** Tests use a shared authenticated state to avoid repetitive login.

1. **`auth.setup.ts`** runs first (setup project)
   - Authenticates with a test API key
   - Saves state to `e2e/.auth/state.json`
   - Runs once before all other tests

2. **All other tests** use the saved authenticated state
   - No need to log in for each test
   - Tests can directly access protected routes
   - Faster test execution

3. **`auth.spec.ts`** tests the login flow itself
   - Uses a fresh context (no authenticated state)
   - Tests login with valid/invalid API keys
   - Tests route protection

## Running Tests

### Prerequisites

1. Install dependencies:
   ```bash
   npm install
   ```

2. Install Playwright browsers:
   ```bash
   npx playwright install chromium
   ```

3. **Backend Server (Required):**
   The backend API must be running for E2E tests. Playwright will automatically start it, but you can also start it manually:
   
   ```bash
   # From project root
   cd backend
   python run_dev.py
   # Or on Linux/Mac:
   ./run_dev.sh
   ```
   
   **Note:** The backend needs `DATABASE_URL` environment variable set. For local testing:
   ```bash
   export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/zatca_ai"  # Linux/Mac
   # Or
   $env:DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/zatca_ai"    # PowerShell
   ```
   
   **Important:** Make sure PostgreSQL is running and the database exists:
   ```bash
   # Create database if it doesn't exist
   createdb zatca_ai
   # Or using psql
   psql -U postgres -c "CREATE DATABASE zatca_ai;"
   ```

### Run All Tests

```bash
npm run test:e2e
```

This will:
1. Run `auth.setup.ts` to authenticate
2. Run all other test files using the authenticated state

### Run Specific Test File

```bash
npx playwright test auth.spec.ts
npx playwright test invoice.spec.ts
npx playwright test playground.spec.ts
```

### Run in UI Mode (Interactive)

```bash
npm run test:e2e:ui
```

**⚠️ Note:** UI mode requires a display server (X server). It will **not work** in:
- GitHub Codespaces
- CI/CD environments
- Headless Linux servers

In these environments, use regular test mode: `npm run test:e2e`

### Run in Headed Mode (See Browser)

```bash
npm run test:e2e:headed
```

**⚠️ Note:** Headed mode also requires a display server. Use regular test mode in headless environments.

### View Test Report

After running tests, view the HTML report:

```bash
npm run test:e2e:report
```

This opens the test report in your browser (works in Codespaces via port forwarding).

## Test Configuration

Configuration is in `playwright.config.ts`:

- **Base URL:** `http://localhost:5173` (Vite dev server)
- **Headless:** `true` by default
- **Retries:** 2 retries in CI, 0 locally
- **Workers:** 1 in CI, parallel locally

## Environment Variables

Set these if needed:

- `TEST_API_KEY`: API key for authentication (default: `test-api-key-valid`)
- `API_BASE_URL`: Backend API URL (default: `http://localhost:8000`)
- `PLAYWRIGHT_BASE_URL`: Frontend URL (default: `http://localhost:5173`)

## Writing New Tests

### HashRouter and helpers

The app uses **HashRouter**. In-app URLs are under hash: `/#/dashboard`, `/#/invoices`, etc. Use the e2e helpers so tests are stable in CI:

```typescript
import { route, waitForPageRoot } from './helpers';

test('should load dashboard', async ({ page }) => {
  await page.goto(route('/dashboard'));  // goes to /#/dashboard
  await expect(page).toHaveURL(/#\/dashboard/);
  await waitForPageRoot(page, 'dashboard');  // waits for [data-testid="dashboard-page"]
});
```

- **Do not** use `waitForLoadState('networkidle')`; use `waitForPageRoot` or visibility of a `data-testid` element.
- **Do not** rely on heading text or translated strings; prefer `data-testid` selectors.

### For Protected Routes

Tests automatically use authenticated state. Use `route()` and `waitForPageRoot()`:

```typescript
import { route, waitForPageRoot } from './helpers';

test('should load dashboard', async ({ page }) => {
  await page.goto(route('/dashboard'));
  await waitForPageRoot(page, 'dashboard');
  await expect(page.locator('[data-testid="dashboard-stats"]')).toBeVisible();
});
```

### For Authentication Tests

Use a fresh context (no authenticated state):

```typescript
test.use({ storageState: { cookies: [], origins: [] } });

test('should reject invalid API key', async ({ page }) => {
  await page.goto('/login');
  // ... test login flow
});
```

## Troubleshooting

### Tests Fail Immediately (3-20ms)

**Symptom:** All tests fail instantly, no UI interaction happens.

**Cause:** Tests are trying to access protected routes without authentication.

**Fix:** Ensure `auth.setup.ts` runs first and `storageState` is configured in `playwright.config.ts`.

### Authentication State Not Found

**Symptom:** Error about missing `e2e/.auth/state.json`.

**Cause:** Setup test didn't run or failed.

**Fix:** 
1. Check that `auth.setup.ts` exists and runs successfully
2. Verify `playwright.config.ts` has the setup project configured
3. Run tests again: `npm run test:e2e`

### Tests Redirect to Login

**Symptom:** Tests navigate to protected routes but get redirected to `/login`.

**Cause:** Authenticated state is not being loaded.

**Fix:**
1. Check `playwright.config.ts` has `storageState: 'e2e/.auth/state.json'`
2. Verify the setup project has `dependencies: ['setup']`
3. Ensure `auth.setup.ts` completes successfully

## CI/CD

Tests run automatically in GitHub Actions (`.github/workflows/e2e-tests.yml`):

- Runs on push/PR to `main` or `develop`
- Installs browsers with system dependencies
- Runs all E2E tests
- Uploads test reports and videos

## Best Practices

1. **Don't log in for each test** - Use the shared authenticated state
2. **Mock API responses** - Use `page.route()` to mock backend calls
3. **Use data-testid** - Prefer stable selectors over CSS classes
4. **Wait for navigation** - Use `waitForURL()` after actions that navigate
5. **Clean up** - Clear localStorage/cookies only when testing logout

## Related Documentation

- [Playwright Container Setup](../../docs/PLAYWRIGHT_CONTAINER_SETUP.md) - Running in Codespaces/containers
- [Playwright Quick Reference](../../docs/PLAYWRIGHT_QUICK_REFERENCE.md) - Common questions

