# UI Implementation Test Checklist

## ✅ Implementation Complete - Testing Guide

This document provides a comprehensive testing checklist for the newly implemented UI features.

---

## 🧪 Automated Tests

### Run Playwright Tests

```bash
cd frontend
npm run test:e2e
```

Or with UI mode:
```bash
npm run test:e2e:ui
```

### Test Files to Run

1. **smoke-test.spec.ts** - Core functionality smoke tests
2. **invoice.spec.ts** - Invoice-specific tests
3. **playground.spec.ts** - API Playground tests
4. **auth.spec.ts** - Authentication flow tests

---

## 📋 Manual Testing Checklist

### Phase 1: Invoice Creation Form

#### ✅ Test InvoiceCreate Page (`/invoices/create`)

- [ ] **Page Loads**
  - Navigate to `/invoices/create`
  - Verify page loads without errors
  - Check for skeleton loader during tenant info fetch

- [ ] **Seller Information**
  - Verify seller name is auto-populated from tenant (readonly)
  - Verify seller tax number is auto-populated (readonly)
  - Verify seller address field is editable

- [ ] **Buyer Information**
  - Enter buyer name
  - Enter buyer tax number (15 digits)
  - Verify validation works

- [ ] **Invoice Metadata**
  - Enter invoice number
  - Select invoice date (datetime-local)
  - Enter invoice type (default: 388)
  - Verify required field validation

- [ ] **Line Items**
  - Click "Add Item" button
  - Add multiple line items
  - Fill in: name, quantity, unit price, tax rate, category, discount
  - Remove a line item (should keep at least one)
  - Verify line item totals calculate correctly
  - Verify form validation for each field

- [ ] **Tax & Totals Calculation**
  - Verify subtotal (tax-exclusive) calculates correctly
  - Verify tax amount calculates correctly
  - Verify total amount calculates correctly
  - Verify totals update when line items change

- [ ] **Form Validation**
  - Try submitting with empty required fields
  - Verify error messages appear
  - Try invalid tax number (not 15 digits)
  - Try negative quantities/prices
  - Try tax rate > 100%

- [ ] **Save Draft Button**
  - Click "Save Draft" button
  - Verify draft saved message appears (UI placeholder)

- [ ] **Submit to ZATCA**
  - Fill form completely
  - Click "Submit to ZATCA"
  - Verify loading state shows
  - Verify success/error handling
  - Verify result display with invoice details

- [ ] **Success Flow**
  - After successful submission, verify result card shows
  - Verify "Create Another" button works
  - Verify "View All Invoices" button navigates correctly

- [ ] **Data Test IDs**
  - Verify all form elements have `data-testid` attributes
  - Check: `invoice-create-page`, `invoice-create-form`, `phase-select`, `environment-select`, etc.

---

### Phase 2: Invoice Detail Page

#### ✅ Test InvoiceDetail Page (`/invoices/:invoiceId`)

- [ ] **Page Loads**
  - Navigate to an invoice detail page
  - Verify skeleton loader shows during load
  - Verify page renders without errors

- [ ] **Not Found State**
  - Navigate to `/invoices/99999` (non-existent ID)
  - Verify friendly error message appears
  - Verify "Back to Invoices" button works

- [ ] **Tabs Navigation**
  - Click through all tabs: Summary, Request JSON, XML, Response, Troubleshooting
  - Verify tab content loads correctly
  - Verify active tab highlighting

- [ ] **Summary Tab**
  - Verify invoice number displays
  - Verify status badge shows correctly
  - Verify phase and environment display
  - Verify UUID and Hash display (if available)
  - Verify QR code displays (if available)
  - Verify copy buttons work

- [ ] **Request JSON Tab**
  - Verify JSON displays with syntax highlighting
  - Verify download button works
  - Verify copy button works

- [ ] **XML Tab**
  - Verify XML displays (if available)
  - Verify download button works
  - Verify empty state if XML not available

- [ ] **Response Tab**
  - Verify ZATCA response displays
  - Verify download button works

- [ ] **Troubleshooting Tab**
  - Verify error explanation button works (if rejected)
  - Verify rejection prediction button works
  - Verify status timeline displays

- [ ] **Data Test IDs**
  - Verify: `invoice-detail-page`, `invoice-detail-tabs`, `back-button`

---

### Phase 3: Invoice List Page

#### ✅ Test Invoices Page (`/invoices`)

- [ ] **Page Loads**
  - Navigate to `/invoices`
  - Verify skeleton loader shows during initial load
  - Verify page renders without errors

- [ ] **Empty State**
  - With no invoices, verify friendly empty state appears
  - Verify "Create Invoice" CTA button works
  - Verify icon and message are user-friendly

- [ ] **Invoice Table**
  - Verify table displays when invoices exist
  - Verify columns: Invoice Number, Phase, Status, Date, Environment
  - Verify status badges display correctly
  - Click on invoice row - verify navigation to detail page

- [ ] **Pagination**
  - If multiple pages exist, verify pagination controls
  - Click "Previous" and "Next" buttons
  - Verify page numbers update correctly

- [ ] **Create Invoice Button**
  - Verify "Create Invoice" button in header
  - Click button - verify navigation to create page

- [ ] **Error State**
  - Simulate API error
  - Verify friendly error message with retry button

- [ ] **Data Test IDs**
  - Verify: `invoices-page`, `invoice-list`, `invoice-table`, `create-invoice-button`, `pagination`

---

### Phase 4: API Playground

#### ✅ Test Playground Page (`/api-playground`)

- [ ] **Page Loads**
  - Navigate to `/api-playground`
  - Verify page loads without errors

- [ ] **Empty State**
  - Before selecting endpoint, verify friendly empty state
  - Verify message guides user to select endpoint

- [ ] **Endpoint Selection**
  - Click endpoint selector
  - Select an endpoint
  - Verify endpoint details display

- [ ] **Templates**
  - Toggle templates visibility
  - Select a template
  - Verify template populates request

- [ ] **Request Configuration**
  - For GET requests: Enter query parameters
  - For POST/PUT: Enter request body
  - Verify JSON editor works
  - Verify JSON validation

- [ ] **Production Warning**
  - Select production environment with write operation
  - Verify confirmation checkbox appears
  - Verify execute button disabled until confirmed

- [ ] **Execute Request**
  - Click "Execute Request"
  - Verify loading state
  - Verify response displays in right panel

- [ ] **Response Viewer**
  - Verify status code badge displays
  - Verify latency and timestamp display
  - Verify headers display (if available)
  - Verify response body with syntax highlighting
  - Click "Copy Response" - verify copy works

- [ ] **cURL Command**
  - Verify cURL command generates
  - Click "Copy" - verify copy works

- [ ] **Data Test IDs**
  - Verify: `api-playground-page`, `endpoint-selector`, `execute-request-button`, `copy-curl-button`, `response-viewer`

---

### Phase 5: Billing Page

#### ✅ Test Billing Page (`/billing`)

- [ ] **Page Loads**
  - Navigate to `/billing`
  - Verify skeleton loader shows during load
  - Verify page renders without errors

- [ ] **Empty State**
  - With no subscription, verify friendly empty state
  - Verify "View Plans" CTA button works

- [ ] **Current Subscription**
  - Verify subscription card displays
  - Verify plan name displays
  - Verify status badge (Active/Trial/Expired)
  - Verify trial days remaining (if applicable)

- [ ] **Usage Meters**
  - Verify invoice usage meter displays
  - Verify AI usage meter displays
  - Verify progress bars work correctly
  - Verify exceeded state (if applicable)

- [ ] **Plan Change Modal**
  - Click "View Plans" button
  - Verify confirmation modal appears
  - Click "Cancel" - verify modal closes
  - Click "Continue" - verify navigation to plans page

- [ ] **Error State**
  - Simulate API error
  - Verify friendly error message with retry button

- [ ] **Data Test IDs**
  - Verify: `billing-page`, `current-subscription-card`, `plan-name`, `subscription-status`, `usage-meters`, `view-plans-button`

---

### Phase 6: Dashboard

#### ✅ Test Dashboard Page (`/dashboard`)

- [ ] **Page Loads**
  - Navigate to `/dashboard`
  - Verify page loads without errors
  - Verify all stat cards display

- [ ] **Stats Grid**
  - Verify 4 stat cards display
  - Verify icons and values display
  - Verify trend indicators (if applicable)

- [ ] **System Status & API Usage**
  - Verify system status card displays
  - Verify API usage card displays

- [ ] **Chart & Insights**
  - Verify chart placeholder displays
  - Verify AI insights display

- [ ] **Recent Invoices**
  - Verify invoice table displays
  - Verify table is clickable

- [ ] **Data Test IDs**
  - Verify: `dashboard-page`, `dashboard-stats`

---

### Phase 7: Global UX Elements

#### ✅ Test Empty States

- [ ] **No Invoices**
  - Navigate to `/invoices` with empty database
  - Verify friendly empty state with icon
  - Verify CTA button works

- [ ] **No Subscription**
  - Navigate to `/billing` with no subscription
  - Verify friendly empty state
  - Verify CTA button works

- [ ] **No Endpoint Selected**
  - Navigate to `/api-playground`
  - Verify empty state before selection

- [ ] **Invoice Not Found**
  - Navigate to non-existent invoice
  - Verify friendly error state

#### ✅ Test Loading States

- [ ] **Skeleton Loaders**
  - Verify skeleton loaders show during:
    - Dashboard initial load
    - Invoice list initial load
    - Invoice detail initial load
    - Billing page initial load

- [ ] **No Blank Screens**
  - Verify no blank screens appear
  - Verify loaders show immediately

#### ✅ Test Error States

- [ ] **API Errors**
  - Simulate network errors
  - Verify friendly error messages
  - Verify retry buttons work

- [ ] **Form Validation Errors**
  - Submit invalid forms
  - Verify inline error messages
  - Verify error highlighting

---

### Phase 8: Navigation & User Flows

#### ✅ Test Complete User Flows

- [ ] **Login → Dashboard**
  - Login with API key
  - Verify redirect to dashboard
  - Verify dashboard loads

- [ ] **Dashboard → Invoices → Create**
  - Navigate from dashboard to invoices
  - Click "Create Invoice" button
  - Verify create page loads

- [ ] **Invoice List → Detail**
  - Click on invoice in list
  - Verify detail page loads
  - Verify back button works

- [ ] **Dashboard → API Playground**
  - Navigate to playground
  - Execute a request
  - Verify response displays

- [ ] **Dashboard → Billing**
  - Navigate to billing
  - Click "View Plans"
  - Verify modal and navigation work

---

### Phase 9: Responsive Design

#### ✅ Test Mobile/Tablet Views

- [ ] **Mobile View (< 768px)**
  - Test all pages on mobile viewport
  - Verify forms stack correctly
  - Verify tables scroll horizontally
  - Verify modals fit screen

- [ ] **Tablet View (768px - 1024px)**
  - Test all pages on tablet viewport
  - Verify grid layouts adapt
  - Verify navigation works

- [ ] **Desktop View (> 1024px)**
  - Test all pages on desktop viewport
  - Verify optimal layout
  - Verify side-by-side panels work

---

### Phase 10: RTL Support

#### ✅ Test Arabic/RTL Mode

- [ ] **Language Toggle**
  - Toggle to Arabic
  - Verify all text switches
  - Verify layout flips (RTL)

- [ ] **RTL Layout**
  - Verify forms align right
  - Verify navigation flips
  - Verify icons position correctly

---

## 🐛 Known Issues to Watch For

1. **Tenant Info Loading**
   - If tenant API fails, form should still work with manual entry
   - Verify error handling doesn't break form

2. **Line Item Calculations**
   - Verify calculations are accurate
   - Test edge cases: zero values, large numbers, decimals

3. **Form State Management**
   - Verify form resets correctly after submission
   - Verify draft saving (UI placeholder) works

4. **API Error Handling**
   - Verify all API errors show friendly messages
   - Verify retry buttons actually retry

---

## 📊 Test Results Template

```
Date: ___________
Tester: ___________

### Phase 1: Invoice Creation
- [ ] All tests passed
- [ ] Issues found: ___________

### Phase 2: Invoice Detail
- [ ] All tests passed
- [ ] Issues found: ___________

### Phase 3: Invoice List
- [ ] All tests passed
- [ ] Issues found: ___________

### Phase 4: API Playground
- [ ] All tests passed
- [ ] Issues found: ___________

### Phase 5: Billing
- [ ] All tests passed
- [ ] Issues found: ___________

### Phase 6: Dashboard
- [ ] All tests passed
- [ ] Issues found: ___________

### Phase 7: Global UX
- [ ] All tests passed
- [ ] Issues found: ___________

### Phase 8: Navigation
- [ ] All tests passed
- [ ] Issues found: ___________

### Phase 9: Responsive
- [ ] All tests passed
- [ ] Issues found: ___________

### Phase 10: RTL
- [ ] All tests passed
- [ ] Issues found: ___________

## Overall Status
- [ ] All tests passed
- [ ] Ready for production
- [ ] Issues need to be fixed: ___________
```

---

## 🚀 Quick Test Commands

```bash
# Start development server
cd frontend
npm run dev

# Run linter
npm run lint

# Run Playwright tests
npm run test:e2e

# Run tests with UI
npm run test:e2e:ui

# Run tests in headed mode
npm run test:e2e:headed
```

---

## 📝 Notes

- All new components have been created with proper TypeScript types
- All forms include comprehensive validation
- All pages include skeleton loaders and empty states
- All interactive elements have data-testid attributes for testing
- RTL support is maintained throughout
- No breaking changes to existing functionality

---

**Last Updated:** After UI implementation completion
**Status:** ✅ Ready for Testing

