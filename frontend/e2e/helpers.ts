/**
 * E2E test helpers for stable, CI-ready Playwright tests.
 *
 * - Use data-testid and page-root selectors; avoid brittle role/text.
 * - HashRouter: all routes are under hash (#/dashboard, #/invoices, etc.).
 * - Wait for React mount via visible page roots, not networkidle.
 */

/** Base path for HashRouter (baseURL is origin, path is hash) */
export const HASH_BASE = '/#';

/** Navigate to an in-app route (HashRouter). e.g. route('/dashboard') => '/#/dashboard' */
export function route(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${HASH_BASE}${p}`;
}

/** Page root data-testids per route – wait for these instead of networkidle */
export const PAGE_ROOTS: Record<string, string> = {
  dashboard: 'dashboard-page',
  invoices: 'invoices-page',
  'invoices/create': 'invoice-create-page',
  'api-playground': 'api-playground-page',
  billing: 'billing-page',
  'ai-insights': 'ai-insights-page',
  webhooks: 'webhooks-page',
  reports: 'reports-page',
  'api-keys': 'api-keys-page',
  'zatca-setup': 'zatca-setup-page',
};

/** Get data-testid for a route (invoice detail uses dynamic id) */
export function getPageRootTestId(path: string): string | undefined {
  const normalized = path.replace(/^#?\//, '').replace(/\/$/, '');
  return PAGE_ROOTS[normalized];
}

/** Wait for a known page root to be visible (stable alternative to networkidle) */
export async function waitForPageRoot(
  page: import('@playwright/test').Page,
  pathOrTestId: string,
  options?: { timeout?: number }
): Promise<void> {
  const timeout = options?.timeout ?? 15000;
  const testId = getPageRootTestId(pathOrTestId) ?? pathOrTestId;
  await page.locator(`[data-testid="${testId}"]`).waitFor({ state: 'visible', timeout });
}
