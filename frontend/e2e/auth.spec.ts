import { test, expect } from '@playwright/test';
import { route, waitForPageRoot } from './helpers';

/**
 * Authentication E2E tests.
 *
 * Tests protected route access control.
 * Assumes user is already authenticated via auth.setup.ts storageState.
 * App uses HashRouter: URLs are like http://localhost:5173/#/dashboard
 */

test.describe('Authentication', () => {
  test('should load protected routes when authenticated', async ({ page }) => {
    // HashRouter: navigate to #/dashboard, #/invoices, etc.
    await page.goto(route('/dashboard'));
    await expect(page).toHaveURL(/#\/dashboard/);
    await waitForPageRoot(page, 'dashboard', { timeout: 10000 });

    await page.goto(route('/invoices'));
    await expect(page).toHaveURL(/#\/invoices/);
    await waitForPageRoot(page, 'invoices', { timeout: 10000 });

    await page.goto(route('/api-playground'));
    await expect(page).toHaveURL(/#\/api-playground/);
    await waitForPageRoot(page, 'api-playground', { timeout: 10000 });

    await page.goto(route('/billing'));
    await expect(page).toHaveURL(/#\/billing/);
    await waitForPageRoot(page, 'billing', { timeout: 10000 });
  });
});
