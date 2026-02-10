# Playwright Authentication Setup - Implementation Guide

## Problem Solved

**Before:** All E2E tests failed immediately (3-20ms) because:
- Tests tried to access protected routes (`/dashboard`, `/invoices`, `/playground`)
- App redirected to `/login` because no API key was stored
- Tests failed before any UI interaction could happen

**After:** Tests use shared authenticated state:
- `auth.setup.ts` authenticates once before all tests
- All other tests use the saved authenticated state
- Tests can directly access protected routes
- Faster execution (no repeated logins)

## Solution Architecture

### 1. Authentication Setup (`auth.setup.ts`)

Runs once before all tests:

```typescript
setup('authenticate', async ({ page }) => {
  // Mock API endpoints
  await page.route(`${API_BASE_URL}/api/v1/plans/usage`, ...);
  
  // Navigate to login
  await page.goto('/login');
  
  // Fill API key and submit
  await page.locator('input#apiKey').fill(VALID_API_KEY);
  await page.getByRole('button', { name: /verify/i }).click();
  
  // Wait for redirect to dashboard
  await page.waitForURL('**/dashboard');
  
  // Save authenticated state
  await page.context().storageState({
    path: 'e2e/.auth/state.json',
  });
});
```

**What it does:**
- Authenticates with a test API key
- Saves localStorage (API key) and cookies to `state.json`
- This state is reused by all other tests

### 2. Playwright Configuration (`playwright.config.ts`)

```typescript
projects: [
  {
    name: 'setup',
    testMatch: /.*\.setup\.ts/,
  },
  {
    name: 'chromium',
    use: { 
      storageState: 'e2e/.auth/state.json', // Use saved state
    },
    dependencies: ['setup'], // Run setup first
  },
]
```

**What it does:**
- Defines a `setup` project that runs `auth.setup.ts`
- Main test project depends on setup (runs after)
- All tests in main project use the saved authenticated state

### 3. Updated Test Files

**Before (❌ Wrong):**
```typescript
test.beforeEach(async ({ page }) => {
  // Manually setting localStorage (doesn't work)
  await page.goto('/login');
  await page.evaluate(() => {
    localStorage.setItem('api_key', 'test-key');
  });
});

test('should load dashboard', async ({ page }) => {
  await page.goto('/dashboard'); // ❌ Redirects to /login
});
```

**After (✅ Correct):**
```typescript
// No beforeEach needed - authenticated state is automatic

test('should load dashboard', async ({ page }) => {
  await page.goto('/dashboard'); // ✅ Works! Already authenticated
  await expect(page.getByText('Dashboard')).toBeVisible();
});
```

## Test Categories

### 1. Protected Route Tests (Use Authenticated State)

**Files:** `invoice.spec.ts`, `playground.spec.ts`

- ✅ Use authenticated state automatically
- ✅ Can directly access protected routes
- ✅ No login logic needed

**Example:**
```typescript
test('should navigate to invoice creation', async ({ page }) => {
  await page.goto('/invoices/create'); // ✅ Works
  await expect(page).toHaveURL(/.*\/invoices\/create/);
});
```

### 2. Authentication Flow Tests (Use Fresh Context)

**File:** `auth.spec.ts`

- ✅ Uses fresh context (no authenticated state)
- ✅ Tests login flow itself
- ✅ Tests route protection

**Example:**
```typescript
test.use({ storageState: { cookies: [], origins: [] } });

test('should redirect to login when not authenticated', async ({ page }) => {
  await page.goto('/dashboard'); // ✅ Should redirect
  await expect(page).toHaveURL(/.*\/login/);
});
```

## File Changes Summary

### Created Files

1. **`frontend/e2e/auth.setup.ts`**
   - Authentication setup script
   - Runs once before all tests
   - Saves authenticated state

### Modified Files

1. **`frontend/playwright.config.ts`**
   - Added setup project
   - Added `storageState` to main project
   - Added project dependencies

2. **`frontend/e2e/invoice.spec.ts`**
   - Removed manual localStorage setting
   - Removed login logic from `beforeEach`
   - Tests now assume authenticated state

3. **`frontend/e2e/playground.spec.ts`**
   - Removed manual localStorage setting
   - Removed login logic from `beforeEach`
   - Tests now assume authenticated state

4. **`frontend/e2e/auth.spec.ts`**
   - Added `test.use({ storageState: { cookies: [], origins: [] } })`
   - Tests use fresh context to test login flow

5. **`frontend/.gitignore`**
   - Added `e2e/.auth/` to ignore authenticated state file

## Running Tests

### First Run

```bash
npm run test:e2e
```

**What happens:**
1. Playwright runs `auth.setup.ts` (setup project)
2. Authentication happens, state saved to `e2e/.auth/state.json`
3. Playwright runs all other tests (main project)
4. Each test uses the saved authenticated state

### Subsequent Runs

```bash
npm run test:e2e
```

**What happens:**
1. Playwright checks if `state.json` exists
2. If exists and valid, uses it
3. If missing or invalid, runs setup again
4. Runs all tests with authenticated state

## Verification

### ✅ Success Indicators

1. **Setup test passes:**
   ```
   ✓ [setup] auth.setup.ts:3:1 › authenticate (5.2s)
   ```

2. **Other tests pass:**
   ```
   ✓ [chromium] invoice.spec.ts:44:1 › Invoice Management › should navigate to invoice creation page (2.1s)
   ✓ [chromium] playground.spec.ts:45:1 › API Playground › should load playground page (1.8s)
   ```

3. **No redirects to login:**
   - Tests access protected routes directly
   - No "redirected to /login" errors

### ❌ Failure Indicators

1. **All tests fail immediately (3-20ms):**
   - Setup didn't run or failed
   - Check `auth.setup.ts` execution

2. **Tests redirect to login:**
   - `storageState` not configured
   - Check `playwright.config.ts`

3. **"Missing state.json" error:**
   - Setup project didn't run
   - Check project dependencies

## Troubleshooting

### Issue: Tests Still Fail Immediately

**Check:**
1. Is `auth.setup.ts` running? Look for `[setup]` in test output
2. Is `state.json` created? Check `frontend/e2e/.auth/state.json`
3. Is `storageState` configured? Check `playwright.config.ts`

**Fix:**
```bash
# Delete state and re-run
rm -rf frontend/e2e/.auth
npm run test:e2e
```

### Issue: Tests Redirect to Login

**Check:**
1. Is `storageState` path correct? Should be `e2e/.auth/state.json`
2. Is state file valid JSON? Check file contents
3. Is setup project dependency set? Should have `dependencies: ['setup']`

**Fix:**
```typescript
// In playwright.config.ts
projects: [
  {
    name: 'chromium',
    use: { 
      storageState: 'e2e/.auth/state.json', // ✅ Correct path
    },
    dependencies: ['setup'], // ✅ Must have this
  },
]
```

### Issue: Auth Tests Fail (Expected to Test Login)

**Check:**
1. Are auth tests using fresh context? Should have `test.use({ storageState: { cookies: [], origins: [] } })`

**Fix:**
```typescript
// In auth.spec.ts
test.use({ storageState: { cookies: [], origins: [] } }); // ✅ Fresh context
```

## Best Practices

1. **One Setup File:** Only one `*.setup.ts` file per test suite
2. **Shared State:** All protected route tests use the same authenticated state
3. **Fresh Context for Auth Tests:** Authentication flow tests use fresh context
4. **Mock API Calls:** Use `page.route()` to mock backend responses
5. **Don't Clear State:** Don't clear localStorage in protected route tests

## Related Documentation

- [E2E Tests README](../frontend/e2e/README.md) - Test structure and usage
- [Playwright Container Setup](./PLAYWRIGHT_CONTAINER_SETUP.md) - Running in containers
- [Playwright Quick Reference](./PLAYWRIGHT_QUICK_REFERENCE.md) - Common questions

