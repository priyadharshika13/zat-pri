# Phase-2 Invoice Validation Guide

## Overview

The `/api/v1/invoices` endpoint enforces strict validation for Phase-2 invoices to ensure ZATCA compliance. This guide explains the validation rules and how to properly submit Phase-2 invoices.

## Mandatory Fields for Phase-2

When `mode: "PHASE_2"`, the following fields are **MANDATORY**:

1. **`seller_tax_number`** (string, 15 characters)
   - Seller VAT registration number
   - Example: `"310123456700003"`

2. **`invoice_type`** (string)
   - Invoice type code (typically `"388"` for standard invoices)
   - Default: `"388"` (but still validated for Phase-2)

3. **`uuid`** (string)
   - Invoice UUID for Phase-2 chain validation
   - Example: `"9f1c1f26-8a2e-4c5d-bb6a-1a7a5f12b001"`

4. **`previous_invoice_hash`** (string, 64 characters)
   - SHA-256 hash of the previous invoice in the chain
   - For the first invoice, use: `"0000000000000000000000000000000000000000000000000000000000000000"`
   - Example: `"abc123def456..."` (64 hex characters)

## Canonical Field Names

The API enforces canonical field names. **Do NOT use** alternative names:

### ✅ Correct Field Names

- `line_items` (NOT `items`)
- `tax_rate` (NOT `vat_rate`)
- `seller_tax_number` (NOT `seller_vat_number`)

### ❌ Invalid Field Names

- `items` → Use `line_items`
- `vat_rate` → Use `tax_rate`
- `seller_vat_number` → Use `seller_tax_number`

## Validation Errors

### Phase-2 Mandatory Field Missing

**Error Response:**
```json
{
  "error": "PHASE2_VALIDATION_ERROR",
  "message": "Phase-2 invoices require the following mandatory fields: uuid, previous_invoice_hash. Please provide all required fields for Phase-2 compliance.",
  "message_ar": "خطأ في التحقق من صحة فاتورة المرحلة الثانية: ...",
  "hint": "Phase-2 invoices require: seller_tax_number, invoice_type, uuid, previous_invoice_hash. See sample_phase2_payload.json for correct format."
}
```

**Status Code:** `422 Unprocessable Entity`

### Invalid JSON Format

**Error Response:**
```json
{
  "error": "INVALID_JSON",
  "message": "Invalid JSON format: Expecting ',' delimiter: line 5 column 10 (char 45). Please ensure your request body is valid JSON.",
  "hint": "For PowerShell: Use Invoke-RestMethod with -Body (Get-Content -Raw file.json). For curl: Use --data-binary @file.json instead of inline -d strings."
}
```

**Status Code:** `400 Bad Request`

## Correct Usage Examples

### PowerShell (Recommended)

```powershell
$headers = @{
  "X-API-Key" = "your-api-key"
  "Content-Type" = "application/json"
}

$body = Get-Content -Raw -Path ".\sample_phase2_payload.json"

Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/invoices" `
  -Method POST `
  -Headers $headers `
  -Body $body
```

### curl (Recommended)

```bash
curl -X POST "http://localhost:8000/api/v1/invoices" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  --data-binary @sample_phase2_payload.json
```

### ❌ Incorrect Usage (DO NOT USE)

```bash
# DO NOT use inline JSON strings with curl
curl -X POST "http://localhost:8000/api/v1/invoices" \
  -H "X-API-Key: your-api-key" \
  -d '{"mode": "PHASE_2", ...}'
```

**Why?** PowerShell and shell escaping can corrupt JSON strings, leading to parsing errors.

## Sample Phase-2 Payload

See `sample_phase2_payload.json` in the project root for a complete, validated Phase-2 invoice payload.

**Key Points:**
- ✅ All mandatory fields present
- ✅ Canonical field names (`line_items`, `tax_rate`)
- ✅ Valid UUID format
- ✅ Valid previous_invoice_hash (64 hex characters)
- ✅ Proper JSON formatting

## Validation Flow

```
1. JSON Parsing
   ↓ (if invalid JSON)
   → 400 Bad Request: INVALID_JSON

2. Pydantic Schema Validation
   ↓ (if missing required fields)
   → 422 Unprocessable Entity: RequestValidationError

3. Phase-2 Mandatory Field Check (model_post_init)
   ↓ (if mode=PHASE_2 and mandatory fields missing)
   → 422 Unprocessable Entity: PHASE2_VALIDATION_ERROR

4. Business Logic Validation
   ↓ (if validation fails)
   → 400 Bad Request: ValidationError
```

## Troubleshooting

### Error: "Phase-2 invoices require the following mandatory fields: uuid"

**Solution:** Add the `uuid` field to your request:
```json
{
  "mode": "PHASE_2",
  "uuid": "9f1c1f26-8a2e-4c5d-bb6a-1a7a5f12b001",
  ...
}
```

### Error: "Invalid JSON format"

**Solution:** Use file-based requests instead of inline JSON:
- PowerShell: `Get-Content -Raw file.json`
- curl: `--data-binary @file.json`

### Error: "Field 'items' is not defined"

**Solution:** Use canonical field name `line_items` instead of `items`.

## Related Files

- **Schema:** `backend/app/schemas/invoice.py`
- **Endpoint:** `backend/app/api/v1/routes/invoices.py`
- **Exception Handlers:** `backend/app/main.py`
- **Sample Payload:** `sample_phase2_payload.json`

