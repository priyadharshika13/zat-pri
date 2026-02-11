import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E test configuration for ZATCA API Platform.
 * 
 * Run tests with: npx playwright test
 * Install browsers: npx playwright install
 * 
 * Authentication Setup:
 * - auth.setup.ts runs first to authenticate and save state
 * - All other tests use the saved authenticated state automatically
 */

// Detect if running in headless environment (Codespaces, CI, etc.)
// Note: --ui flag will override this, so UI mode won't work in Codespaces
const isHeadlessEnvironment = !!process.env.CODESPACES || !!process.env.CI || !process.env.DISPLAY;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://zat-pri.vercel.app/',
    // Force headless in Codespaces/CI environments (no X server available)
    // Note: --ui and --headed flags override this setting
    headless: isHeadlessEnvironment ? true : true, // Always headless by default
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    // Setup project: Authenticate once and save state
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    // Main test project: Uses authenticated state
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Use authenticated state from setup
        storageState: 'e2e/.auth/state.json',
      },
      dependencies: ['setup'],
    },
  ],

  // Start both frontend and backend servers for E2E tests
  webServer: [
    // Backend API server (must start first)
    {
      command: process.platform === 'win32' 
        ? 'cd ../backend && run_test_server.bat'
        : 'cd ../backend && bash run_test_server.sh',
      url: 'https://zat-pri.onrender.com/api/v1/system/health',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        // DATABASE_URL will be auto-resolved by backend if not set
        // Backend detects docker vs host automatically
        DATABASE_URL: process.env.DATABASE_URL,
        ENVIRONMENT: 'sandbox',
        ENVIRONMENT_NAME: 'local',
      },
    },
    // Frontend dev server
    {
      command: 'npm run dev',
      url: 'https://zat-pri.vercel.app/',
      reuseExistingServer: !process.env.CI,
      timeout: 120 * 1000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
});

