import { test, expect } from '@playwright/test';
import { route, waitForPageRoot } from './helpers';

/**
 * API Playground E2E tests.
 *
 * Tests playground page functionality.
 * Assumes user is already authenticated via auth.setup.ts storageState.
 * Uses data-testid and page-root; no heading text or networkidle.
 */

test.describe('API Playground', () => {
  test('should load playground page', async ({ page }) => {
    await page.goto(route('/api-playground'));
    await expect(page).toHaveURL(/#\/api-playground/);
    await waitForPageRoot(page, 'api-playground', { timeout: 10000 });
  });

  test('should display endpoint selector', async ({ page }) => {
    await page.goto(route('/api-playground'));
    await expect(page).toHaveURL(/#\/api-playground/);

    // Wait for page root then endpoint selector (stable, no networkidle)
    await waitForPageRoot(page, 'api-playground', { timeout: 10000 });

    const endpointSelector = page.locator('[data-testid="endpoint-selector"]');
    await expect(endpointSelector).toBeVisible({ timeout: 10000 });

    // EndpointSelector has a category select; wait for it and options
    const categorySelect = endpointSelector.locator('select');
    await expect(categorySelect).toBeVisible({ timeout: 5000 });
    const optionCount = await categorySelect.locator('option').count();
    expect(optionCount).toBeGreaterThan(0);
  });
});
