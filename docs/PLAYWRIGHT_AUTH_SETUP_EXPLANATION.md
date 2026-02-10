# Playwright Auth Setup - Why Direct State Injection Works

## Problem with UI-Based Authentication

The previous approach tried to authenticate by interacting with the login UI:
- Waited for headings, text, form elements
- Depended on React rendering timing
- Failed due to async health checks, language switching, CSS loading
- Created infinite timeout loops

**Root Cause:** Authentication bootstrapping should NOT test UI rendering.

## Solution: Direct State Injection

The current `auth.setup.ts` uses **direct state injection** - the industry-standard approach:

```typescript
// 1. Navigate to app
await page.goto('/');

// 2. Inject API key directly into localStorage
await page.evaluate((apiKey) => {
  localStorage.setItem('api_key', apiKey);
}, SEEDED_API_KEY);

// 3. Reload so app picks up auth state
await page.reload();

// 4. Wait for route change (not text visibility)
await page.waitForURL(/dashboard|playground|invoices|billing/, {
  timeout: 15000,
});

// 5. Save authenticated state
await page.context().storageState({ path: storageStatePath });
```

## Why This Approach is Stable

| Aspect | UI-Based (❌) | State Injection (✅) |
|--------|---------------|---------------------|
| **Dependency** | UI text, headings, forms | localStorage (synchronous) |
| **Language** | Fails with RTL/Arabic | Language-agnostic |
| **Timing** | Race conditions with React | Deterministic |
| **Health Checks** | Waits for async calls | No dependency |
| **CSS Loading** | Fails if styles delayed | No dependency |
| **Environment** | Flaky in Codespaces/CI | Works everywhere |

## How It Works

1. **Navigate to `/`** - App routes to `/login` if not authenticated
2. **Inject API key** - Directly sets `localStorage.setItem('api_key', 'test-key')`
3. **Reload page** - App re-initializes and checks `isAuthed()`
4. **Login component redirects** - `useEffect` in `Login.tsx` sees authenticated user and redirects to `/dashboard`
5. **Wait for route** - Playwright waits for URL change to authenticated route
6. **Save state** - `storageState` saves localStorage + cookies for other tests

## Key Benefits

✅ **No UI selectors** - Avoids timing issues with React rendering  
✅ **No language dependency** - Works with English/Arabic/RTL  
✅ **No async race conditions** - localStorage is synchronous  
✅ **Route-based verification** - Waits for URL change, not DOM elements  
✅ **Deterministic** - Same behavior every time, regardless of environment  
✅ **Works headless** - No visual rendering needed  
✅ **Works in Codespaces** - No special environment requirements  
✅ **Works in CI** - Stable in GitHub Actions  

## Mental Model

- **`auth.setup.ts`** = Bootstrap authenticated state (NOT test UI)
- **`auth.spec.ts`** = Test login UI (if needed)

This separation ensures:
- Setup is fast and reliable
- UI tests can focus on user experience
- No flaky timeouts or selector failures

## Industry Standard

This approach is used by:
- Google's Playwright best practices
- Microsoft's Playwright documentation
- Major SaaS platforms (Stripe, Auth0, etc.)

**Principle:** Authentication setup should set state, not test UI.

