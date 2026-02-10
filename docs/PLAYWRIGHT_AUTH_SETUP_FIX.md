# Playwright Auth Setup Fix - Explanation

## Problem Summary

The original `auth.setup.ts` was failing because it relied on:
- DOM structure assumptions (`<form>` tag)
- Element IDs (`input#apiKey`)
- `waitForFunction` checking React internals

These selectors are brittle because:
1. React may not have rendered yet
2. Async effects (server health check) delay UI rendering
3. DOM structure can change without breaking user experience

## Solution Approach

### ✅ What We Changed

1. **User-Visible Selectors Only**
   - `getByRole('heading', { name: /login/i })` - Waits for visible "Login" heading
   - `getByPlaceholder(/sk-/i)` - Uses placeholder text (user-visible)
   - `getByRole('button', { name: /verify.*login/i })` - Uses button text (user-visible)

2. **No DOM Structure Dependencies**
   - Removed `waitForSelector('form')`
   - Removed `input#apiKey` selector
   - Removed `waitForFunction` checking DOM internals

3. **Proper API Key**
   - Uses seeded API key: `"test-key"` (matches backend seed)
   - Matches what backend actually creates in `tenant_seed_service.py`

4. **Better Waiting Strategy**
   - Waits for heading first (ensures React rendered)
   - Then waits for input placeholder (ensures form is ready)
   - Uses `expect().toBeVisible()` and `expect().toBeEnabled()` (Playwright best practices)

### ✅ Why This Works

1. **Accessible Selectors Are Stable**
   - Text content ("Login", "Verify & Login") is user-facing and unlikely to change
   - Placeholder text is part of the UI contract
   - Role-based selectors (`getByRole`) are recommended by Playwright

2. **Waits for Real User Experience**
   - Heading appears when React has rendered
   - Input appears when form is ready
   - Button appears when form is interactive
   - This matches what a real user sees

3. **No Race Conditions**
   - Doesn't assume DOM structure exists immediately
   - Waits for actual user-visible elements
   - Handles async server health check gracefully

4. **Production-Grade**
   - Uses Playwright's recommended `getByRole` and `getByPlaceholder`
   - Follows accessibility-first testing principles
   - Works across different rendering speeds (local, Codespaces, CI)

## Key Improvements

| Before | After |
|--------|-------|
| `waitForSelector('form')` | `getByRole('heading', { name: /login/i })` |
| `page.locator('input#apiKey')` | `getByPlaceholder(/sk-/i)` |
| `waitForFunction(() => document.querySelector('input#apiKey'))` | `expect().toBeVisible()` |
| `'test-api-key-valid'` | `'test-key'` (matches backend seed) |
| Complex fallback logic | Simple, direct selectors |

## Result

- ✅ Stable across environments (local, Codespaces, CI)
- ✅ No brittle DOM dependencies
- ✅ Uses real seeded API key
- ✅ Follows Playwright best practices
- ✅ Production-grade reliability

