# Running Playwright Tests in GitHub Codespaces

## Issue: UI Mode Not Available

When running `npm run test:e2e:ui` in GitHub Codespaces, you may encounter:

```
ProtocolError: Protocol error (Browser.getVersion): Internal server error, session closed.
Looks like you launched a headed browser without having a XServer running.
```

## Why This Happens

GitHub Codespaces is a **headless Linux environment** without an X server (display server). Playwright's UI mode (`--ui`) and headed mode (`--headed`) require a display server to show the browser window.

## Solutions

### ✅ Solution 1: Use Regular Test Mode (Recommended)

Run tests in headless mode (default):

```bash
cd frontend
npm run test:e2e
```

This runs all tests without requiring a display server.

### ✅ Solution 2: View Test Report

After running tests, view the HTML report:

```bash
npm run test:e2e:report
```

The report will be available via port forwarding in Codespaces. You can view it in your browser.

### ✅ Solution 3: Use Port Forwarding for UI (Advanced)

If you need the interactive UI, you can set up X11 forwarding, but this is complex and not recommended. Instead, use the HTML report.

## Configuration

The Playwright config automatically detects Codespaces and forces headless mode:

```typescript
// playwright.config.ts
const isHeadlessEnvironment = !!process.env.CODESPACES || !!process.env.CI;
headless: isHeadlessEnvironment || true
```

## Available Test Commands

| Command | Description | Works in Codespaces? |
|---------|-------------|---------------------|
| `npm run test:e2e` | Run all tests (headless) | ✅ Yes |
| `npm run test:e2e:ui` | Interactive UI mode | ❌ No (requires X server) |
| `npm run test:e2e:headed` | See browser window | ❌ No (requires X server) |
| `npm run test:e2e:report` | View HTML report | ✅ Yes (via port forwarding) |

## Best Practice for Codespaces

1. **Run tests in headless mode:**
   ```bash
   npm run test:e2e
   ```

2. **View results in HTML report:**
   ```bash
   npm run test:e2e:report
   ```

3. **Check test output in terminal:**
   - Tests show pass/fail status
   - Screenshots saved on failure
   - Trace files available for debugging

## Debugging Failed Tests

Even in headless mode, you can debug:

1. **Screenshots:** Automatically saved on failure in `test-results/`
2. **Traces:** Available for failed tests (configured in `playwright.config.ts`)
3. **HTML Report:** Shows detailed test results with screenshots and traces

## Local Development (with Display)

If you're running locally (not in Codespaces) and have a display server:

- ✅ `npm run test:e2e:ui` - Works (interactive UI)
- ✅ `npm run test:e2e:headed` - Works (see browser)

## Summary

- **Codespaces:** Use `npm run test:e2e` + `npm run test:e2e:report`
- **Local (with display):** All modes work
- **CI/CD:** Use `npm run test:e2e` (headless)

The configuration automatically handles this, so you don't need to change anything - just use the appropriate command for your environment.

