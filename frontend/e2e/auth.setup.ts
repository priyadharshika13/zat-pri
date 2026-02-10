import { test as setup, expect } from '@playwright/test';

/**
 * Authentication setup for Playwright E2E tests.
 * 
 * This file runs once before all tests to authenticate and save the state.
 * All other tests will use the saved authenticated state automatically.
 * 
 * Strategy:
 * 1. Validates API key by calling backend directly with X-API-Key header
 * 2. Sets up frontend localStorage for frontend E2E tests
 * 3. Saves authenticated state for reuse across all tests
 * 
 * Authentication Method:
 * - Backend: API Key via X-API-Key header (no JWT, no Bearer token, no session)
 * - Frontend: Stores API key in localStorage for app to use
 * 
 * This approach:
 * - Validates authentication against real backend endpoint
 * - No UI interaction required for setup
 * - Works regardless of language, React rendering, or async health checks
 * - Deterministic and stable across environments
 */

const SEEDED_API_KEY = 'test-key'; // Matches backend seed: tenant_seed_service.py
const BACKEND_BASE_URL = 'http://localhost:8000';
const STORAGE_STATE_PATH = 'e2e/.auth/state.json';
const MAX_RETRIES = 20; // Maximum 20 seconds wait
const RETRY_DELAY_MS = 1000; // Retry every 1 second

/**
 * Waits for backend to be ready by retrying the authentication endpoint.
 * Exits immediately once a 200 response is received.
 * 
 * @param request Playwright request context
 * @returns Response object with 200 status
 * @throws Error if backend is still unavailable after max retries
 */
async function waitForBackendReady(request: any) {
  let lastError: Error | null = null;
  
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      const response = await request.get(`${BACKEND_BASE_URL}/api/v1/tenants/me`, {
        headers: {
          'X-API-Key': SEEDED_API_KEY,
        },
        timeout: 5000, // 5 second timeout per request
      });

      // If we get a 200 response, backend is ready
      if (response.ok() && response.status() === 200) {
        return response;
      }
      
      // If we get a non-200 but valid response, backend is up but auth might be wrong
      // This shouldn't happen with test-key, but log it
      lastError = new Error(
        `Backend responded with status ${response.status()}. Expected 200.`
      );
    } catch (error: any) {
      // Network errors, timeouts, etc. - backend might not be ready yet
      lastError = error;
    }

    // If not the last attempt, wait before retrying
    if (attempt < MAX_RETRIES) {
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY_MS));
    }
  }

  // If we've exhausted all retries, throw a clear error
  throw new Error(
    `Backend is not ready after ${MAX_RETRIES} attempts (${MAX_RETRIES} seconds). ` +
    `Last error: ${lastError?.message || 'Unknown error'}. ` +
    `Please ensure the backend is running at ${BACKEND_BASE_URL}`
  );
}

setup('authenticate', async ({ page, request }) => {
  // Step 1: Wait for backend to be ready, then validate API key
  // This ensures the backend is running and the key is valid
  // Retries every 1 second (up to 20 seconds) to handle startup delays
  const response = await waitForBackendReady(request);

  // Assert backend authentication is successful
  expect(response.ok()).toBe(true);
  expect(response.status()).toBe(200);

  const tenantData = await response.json();
  expect(tenantData).toHaveProperty('company_name');
  expect(tenantData).toHaveProperty('vat_number');
  expect(tenantData).toHaveProperty('environment');

  // Step 2: Set up frontend state for E2E tests
  // App uses HashRouter: routes are under #/ (e.g. #/dashboard, #/login)
  await page.goto('/');

  // Inject API key into localStorage (frontend app reads from here)
  await page.evaluate((apiKey) => {
    localStorage.setItem('api_key', apiKey);
  }, SEEDED_API_KEY);

  // Reload page so app picks up the auth state
  await page.reload();

  // Wait for app to recognize authentication and redirect (HashRouter: URL will contain #/dashboard or similar)
  await page.waitForURL(/#\/(dashboard|api-playground|invoices|billing)/, {
    timeout: 15000,
  });

  // Wait for an authenticated page root (React has mounted and rendered)
  await page.locator('[data-testid="dashboard-page"], [data-testid="invoices-page"], [data-testid="billing-page"], [data-testid="api-playground-page"]').first().waitFor({ state: 'visible', timeout: 10000 });

  // Verify API key is stored correctly in localStorage
  const storedApiKey = await page.evaluate(() => localStorage.getItem('api_key'));
  if (!storedApiKey || storedApiKey !== SEEDED_API_KEY) {
    throw new Error(
      `Authentication failed: API key not stored correctly. ` +
      `Expected: ${SEEDED_API_KEY}, Got: ${storedApiKey}`
    );
  }

  // Step 3: Save authenticated state for other tests
  // This includes localStorage (API key) and any cookies
  await page.context().storageState({ path: STORAGE_STATE_PATH });
});
