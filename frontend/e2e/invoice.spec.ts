import { test, expect } from '@playwright/test';
import { route, waitForPageRoot } from './helpers';

/**
 * Invoice management E2E tests.
 *
 * Tests invoice list and navigation.
 * Assumes user is already authenticated via auth.setup.ts storageState.
 * Uses data-testid and page-root waits; no brittle heading/text or networkidle.
 */

test.describe('Invoice Management', () => {
  test('should load invoice list page', async ({ page }) => {
    await page.goto(route('/invoices'));
    await expect(page).toHaveURL(/#\/invoices/);
    await waitForPageRoot(page, 'invoices', { timeout: 10000 });
  });

  test('should display invoice list container', async ({ page }) => {
    await page.goto(route('/invoices'));
    await expect(page).toHaveURL(/#\/invoices/);

    // Wait for page root (React has mounted)
    await waitForPageRoot(page, 'invoices', { timeout: 10000 });

    // Invoice list container is always present (skeleton, table, or empty state)
    const invoiceList = page.locator('[data-testid="invoice-list"]');
    await expect(invoiceList).toBeVisible({ timeout: 15000 });

    // At least one of: empty state action, invoice table, or skeleton (loading)
    const emptyStateAction = page.locator('[data-testid="empty-state-action"]');
    const invoiceTable = page.locator('[data-testid="invoice-table"]');
    const skeleton = page.locator('[data-testid="invoice-list"] [class*="animate-pulse"]');

    const hasEmpty = await emptyStateAction.isVisible().catch(() => false);
    const hasTable = await invoiceTable.isVisible().catch(() => false);
    const hasSkeleton = await skeleton.first().isVisible().catch(() => false);

    expect(hasEmpty || hasTable || hasSkeleton).toBe(true);
  });
});
