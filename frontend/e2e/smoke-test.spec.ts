import { test, expect } from '@playwright/test';
import { route, waitForPageRoot, PAGE_ROOTS } from './helpers';

/**
 * End-to-End UI Smoke Test
 *
 * Tests application usability from a real user perspective.
 * Uses HashRouter (#/dashboard, #/invoices, etc.) and data-testid page roots.
 * No networkidle; stable waits on React-rendered roots.
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const TEST_API_KEY = 'test-key';

test.describe('E2E Smoke Test - User Perspective', () => {
  test('1. Application Startup Verification', async ({ page, request }) => {
    const backendHealth = await request.get(`${BACKEND_URL}/api/v1/system/health`, {
      timeout: 5000,
    });
    expect(backendHealth.ok()).toBe(true);

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    // Either login or dashboard should appear (depends on auth state)
    const loginRoot = page.locator('[data-testid="login-page"]');
    const dashboardRoot = page.locator('[data-testid="dashboard-page"]');
    await Promise.race([
      loginRoot.waitFor({ state: 'visible', timeout: 10000 }),
      dashboardRoot.waitFor({ state: 'visible', timeout: 10000 }),
    ]);
  });

  test('2. Authentication Flow - UI Perspective', async ({ page, request }) => {
    const response = await request.get(`${BACKEND_URL}/api/v1/tenants/me`, {
      headers: { 'X-API-Key': TEST_API_KEY },
      timeout: 10000,
    });
    expect(response.ok()).toBe(true);

    await page.goto('/');
    await page.evaluate((apiKey) => {
      localStorage.setItem('api_key', apiKey);
    }, TEST_API_KEY);
    await page.reload();

    // HashRouter: redirect to #/dashboard (or similar); wait for authenticated root
    await page.waitForURL(/#\/(dashboard|invoices|billing|api-playground)/, { timeout: 15000 });
    const root = page.locator(
      '[data-testid="dashboard-page"], [data-testid="invoices-page"], [data-testid="billing-page"], [data-testid="api-playground-page"]'
    ).first();
    await expect(root).toBeVisible({ timeout: 10000 });

    // Access protected routes (hash paths)
    const routes = ['/dashboard', '/invoices', '/api-playground', '/billing'] as const;
    for (const r of routes) {
      await page.goto(route(r));
      await waitForPageRoot(page, r.replace(/^\//, ''), { timeout: 10000 });
      await expect(page).toHaveURL(new RegExp(`#${r.replace('/', '\\/')}`));
    }
  });

  test('3. Core User Flows - Smoke Level', async ({ page }) => {
    await page.goto('/');
    await page.evaluate((apiKey: string) => localStorage.setItem('api_key', apiKey), TEST_API_KEY);
    await page.reload();
    await page.waitForURL(/#\/(dashboard|invoices|billing|api-playground)/, { timeout: 15000 }).catch(() => {});

    const pageTests: { path: string; testId: string }[] = [
      { path: '/dashboard', testId: PAGE_ROOTS.dashboard },
      { path: '/invoices', testId: PAGE_ROOTS.invoices },
      { path: '/api-playground', testId: PAGE_ROOTS['api-playground'] },
      { path: '/billing', testId: PAGE_ROOTS.billing },
    ];

    for (const { path, testId } of pageTests) {
      await page.goto(route(path));
      await expect(page.locator(`[data-testid="${testId}"]`)).toBeVisible({ timeout: 15000 });
    }

    // Playground: endpoint selector visible
    await page.goto(route('/api-playground'));
    await waitForPageRoot(page, 'api-playground', { timeout: 10000 });
    await expect(page.locator('[data-testid="endpoint-selector"]')).toBeVisible({ timeout: 5000 });
  });

  test('4. UI Health Checks', async ({ page }) => {
    await page.goto('/');
    await page.evaluate((apiKey: string) => localStorage.setItem('api_key', apiKey), TEST_API_KEY);
    await page.reload();
    await page.waitForURL(/#\/(dashboard|invoices|billing|api-playground)/, { timeout: 15000 }).catch(() => {});

    const routes = ['/dashboard', '/invoices', '/api-playground', '/billing'] as const;
    for (const r of routes) {
      const testId = PAGE_ROOTS[r.replace(/^\//, '') as keyof typeof PAGE_ROOTS];
      if (!testId) continue;
      await page.goto(route(r));
      await expect(page.locator(`[data-testid="${testId}"]`)).toBeVisible({ timeout: 15000 });
    }
  });

  test('5. API & UI Sync Check', async ({ page }) => {
    await page.goto('/');
    await page.evaluate((apiKey: string) => localStorage.setItem('api_key', apiKey), TEST_API_KEY);
    await page.reload();
    await page.waitForURL(/#\/(dashboard|invoices|billing|api-playground)/, { timeout: 15000 }).catch(() => {});

    const apiPages = ['/dashboard', '/invoices', '/billing'] as const;
    for (const r of apiPages) {
      const key = r.replace(/^\//, '') as keyof typeof PAGE_ROOTS;
      const testId = PAGE_ROOTS[key];
      if (!testId) continue;
      await page.goto(route(r));
      await expect(page.locator(`[data-testid="${testId}"]`)).toBeVisible({ timeout: 20000 });
    }
  });

  test('6. Navigation Flow', async ({ page }) => {
    await page.goto('/');
    await page.evaluate((apiKey: string) => localStorage.setItem('api_key', apiKey), TEST_API_KEY);
    await page.reload();
    await page.waitForURL(/#\/(dashboard|invoices|billing|api-playground)/, { timeout: 15000 }).catch(() => {});

    const routes = ['/dashboard', '/invoices', '/api-playground', '/billing'] as const;
    for (const r of routes) {
      await page.goto(route(r));
      await expect(page).toHaveURL(new RegExp(`#${r.replace('/', '\\/')}`));
      const testId = PAGE_ROOTS[r.replace(/^\//, '') as keyof typeof PAGE_ROOTS];
      if (testId) {
        await expect(page.locator(`[data-testid="${testId}"]`)).toBeVisible({ timeout: 10000 });
      }
    }
  });
});
