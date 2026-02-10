# Viewing Playwright Test Reports

## Quick Reference

After running E2E tests, you can view the HTML report in several ways:

### Method 1: Using npm script (if available)

```bash
cd frontend
npm run test:e2e:report
```

### Method 2: Direct Playwright command

```bash
cd frontend
npx playwright show-report
```

### Method 3: Open report file directly

The HTML report is generated in `frontend/playwright-report/index.html` after running tests.

In Codespaces, you can:
1. Right-click on `playwright-report/index.html` in the file explorer
2. Select "Open with Live Server" or "Preview"
3. Or use port forwarding to view it in your browser

## Report Location

After running tests, the report is saved to:
- **Path:** `frontend/playwright-report/`
- **Main file:** `index.html`
- **Screenshots:** `frontend/test-results/` (on failures)

## Generating Report

The report is automatically generated when you run:

```bash
npm run test:e2e
```

The `playwright.config.ts` is configured with:
```typescript
reporter: 'html'
```

This creates an HTML report after each test run.

## Troubleshooting

### Script not found

If `npm run test:e2e:report` doesn't work:

1. **Pull latest changes:**
   ```bash
   git pull origin main
   ```

2. **Or use direct command:**
   ```bash
   npx playwright show-report
   ```

3. **Or manually open:**
   - Navigate to `frontend/playwright-report/index.html`
   - Open in browser or use Codespaces port forwarding

### Report not found

If the report doesn't exist:

1. **Run tests first:**
   ```bash
   npm run test:e2e
   ```

2. **Check if report directory exists:**
   ```bash
   ls frontend/playwright-report/
   ```

3. **Report is only generated after tests complete**

## Port Forwarding in Codespaces

If you're in GitHub Codespaces:

1. The `playwright show-report` command will start a local server
2. Codespaces will automatically detect the port
3. Click "Open in Browser" when prompted
4. Or manually forward the port from the PORTS tab

## Report Features

The HTML report includes:
- ✅ Test results (passed/failed)
- 📸 Screenshots on failure
- 🎬 Video recordings (if configured)
- 📊 Test timeline
- 🔍 Detailed error messages
- 📝 Test execution logs

