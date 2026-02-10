# Playwright E2E Selector Audit

**Date:** 2026-02-03  
**Scope:** Audit and update Playwright E2E tests to match current React + HashRouter frontend. Ensure CI-stable, non-flaky, future-proof tests.

---

## 1. UI Reality Check

### Routing (HashRouter)

- **Reality:** App uses `HashRouter`. All in-app routes are under hash: `http://localhost:5173/#/dashboard`, `/#/invoices`, `/#/login`, etc.
- **Impact:** Tests that used `page.goto('/dashboard')` without the hash never matched the real URL and could be flaky depending on how the app resolves paths.

### Authentication

- **Reality:** Login stores API key in `localStorage` key `api_key`. No session cookie. Root `/` redirects to `#/dashboard` if authed, else `#/login`.
- **Impact:** Auth setup must inject into localStorage and wait for URL to contain `#/dashboard` (or similar), not `/dashboard`.

### Async / Conditional Rendering

- **Reality:** Dashboard, Invoices, Billing, Reports load data from API; they show skeletons then content or empty state. Playground loads templates; EndpointSelector is always mounted.
- **Impact:** Waiting for `networkidle` is brittle (APIs may be slow or polling). Prefer waiting for a stable page root `[data-testid="...-page"]` to be visible.

---

## 2. Selector Audit (Before → After)

### auth.setup.ts

| Before | After |
|--------|--------|
| `page.waitForURL(/dashboard\|playground|invoices\|billing/)` | `page.waitForURL(/#\/(dashboard\|api-playground|invoices\|billing)/)` |
| (none) | Wait for one of `[data-testid="dashboard-page"]`, `invoices-page`, `billing-page`, `api-playground-page` |

### auth.spec.ts

| Before | After |
|--------|--------|
| `page.goto('/dashboard')` | `page.goto(route('/dashboard'))` → `/#/dashboard` |
| `expect(page).toHaveURL(/.*\/dashboard/)` | `expect(page).toHaveURL(/#\/dashboard/)` |
| (no wait for content) | `waitForPageRoot(page, 'dashboard')` → `[data-testid="dashboard-page"]` |

### invoice.spec.ts

| Before | After |
|--------|--------|
| `page.goto('/invoices')` | `page.goto(route('/invoices'))` |
| `page.waitForLoadState('networkidle')` | **Removed.** Use `waitForPageRoot(page, 'invoices')` |
| `page.getByRole('heading', { name: /invoices/i })` | **Removed.** Use `[data-testid="invoices-page"]` and `[data-testid="invoice-list"]` |
| `page.getByText(/no invoices/i)`, `getByText(/invoice number/i)`, skeleton class | `[data-testid="empty-state-action"]`, `[data-testid="invoice-table"]`, or skeleton inside `[data-testid="invoice-list"]` |

### playground.spec.ts

| Before | After |
|--------|--------|
| `page.goto('/api-playground')` | `page.goto(route('/api-playground'))` |
| `page.getByRole('heading', { name: /api playground/i })` | **Removed.** Use `waitForPageRoot(page, 'api-playground')` |
| `page.waitForLoadState('networkidle')` | **Removed.** Use page root + `[data-testid="endpoint-selector"]` |
| `endpointSelector.locator('select')` | Same (still stable) |

### smoke-test.spec.ts

| Before | After |
|--------|--------|
| `page.goto(FRONTEND_URL)` then `page.reload()` | Same; then wait for `[data-testid="login-page"]` or `[data-testid="dashboard-page"]` |
| `page.waitForLoadState('networkidle', …)` | **Removed.** Wait for page roots by `data-testid` |
| `page.goto(\`${FRONTEND_URL}${route}\`)` (no hash) | `page.goto(route(r))` so path is `/#/dashboard` etc. |
| `page.getByText(...)`, body text checks | Use `[data-testid="invoices-page"]`, `[data-testid="endpoint-selector"]`, etc. |
| `page.waitForTimeout(2000)` | **Removed** where possible; use visibility of page roots |

---

## 3. Timing & Load Strategy

| Avoid | Prefer |
|-------|--------|
| `waitForLoadState('networkidle')` | `waitForPageRoot(page, 'dashboard')` → `[data-testid="dashboard-page"]` |
| `waitForTimeout(2000)` for “let API finish” | Wait for specific element (e2e list, table, or empty state) |
| Expecting “no loader after 2s” | Rely on page root visible; optional check for skeleton then content |

---

## 4. New data-testid Added (UI)

| Location | data-testid |
|----------|-------------|
| `Login.tsx` (root div) | `login-page` |
| `ZatcaSetup.tsx` (root div) | `zatca-setup-page` |

All other pages already had a root `data-testid` (e.g. `dashboard-page`, `invoices-page`, `api-playground-page`, `billing-page`).

---

## 5. New Files

| File | Purpose |
|------|---------|
| `e2e/helpers.ts` | `route()`, `PAGE_ROOTS`, `waitForPageRoot()` for HashRouter and stable waits |

---

## 6. Confirmation Checklist

- **CI-stable:** Tests wait on DOM elements (page roots / data-testid), not network idle or fixed timeouts.
- **Non-flaky:** No reliance on heading text or i18n; URL assertions use hash routes; selectors use data-testid.
- **Future-proof:** New pages should add a root `data-testid="<name>-page"` and optionally add to `PAGE_ROOTS` in `helpers.ts`.

---

## 7. Running E2E Tests

```bash
cd frontend
npx playwright install chromium
npm run test:e2e
```

Setup runs first (auth), then all specs with saved storage state. Use hash URLs and page-root waits throughout.
