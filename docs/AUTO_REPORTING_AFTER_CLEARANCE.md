# Automatic Reporting After Clearance

## Overview

When a Phase-2 invoice is successfully cleared by ZATCA (status = `CLEARED`), the system **automatically** calls the ZATCA Reporting API to report the invoice. This eliminates the need for a separate manual API call.

## Implementation Details

### Flow

```
POST /api/v1/invoices (Phase-2)
  ↓
1. Invoice Created ✅
  ↓
2. Validation ✅
  ↓
3. XML Generation ✅
  ↓
4. Hash Computation ✅
  ↓
5. XML Signing ✅
  ↓
6. Submit Clearance ✅
  ↓
7. If Clearance Status == "CLEARED":
     → Automatically call Reporting API ✅
     → Store reporting response ✅
  ↓
8. Return Response (with both clearance + reporting) ✅
```

### Code Location

**File:** `backend/app/services/invoice_service.py`

**Method:** `_process_phase2()` (lines ~586-627)

**Key Logic:**
```python
# After clearance submission
clearance_status = clearance.get("status", "REJECTED")

if clearance_status == "CLEARED":
    # Automatically report invoice
    try:
        reporting_result = await clearance_service.report(
            invoice_uuid=invoice_uuid_for_reporting,
            clearance_status=clearance_status  # Passed for headers
        )
        # Store reporting result in response
    except Exception as e:
        # CRITICAL: Do NOT fail invoice if reporting fails
        # Log warning and continue with clearance success
        logger.warning(f"Reporting failed: {e}. Clearance status remains CLEARED.")
```

### Reporting API Headers

The Reporting API call includes the following headers per ZATCA Developer Portal Manual:

- `Authorization: Bearer <oauth_token>` (automatic via OAuth service)
- `Content-Type: application/json`
- `Accept: application/json`
- `Clearance-Status: CLEARED` (when reporting after clearance)
- `Accept-Version: 1.0` (ZATCA API version)

**Implementation:** `backend/app/integrations/zatca/sandbox.py:report_invoice()` (lines ~239-393)

### Response Structure

The `POST /api/v1/invoices` response now includes a `reporting` field when automatic reporting occurs:

```json
{
  "success": true,
  "invoice_number": "INV-001",
  "mode": "PHASE_2",
  "environment": "SANDBOX",
  "clearance": {
    "clearance_status": "CLEARED",
    "clearance_uuid": "uuid-from-zatca",
    "qr_code": "qr-code-base64",
    "reporting_status": "REPORTED"
  },
  "reporting": {
    "status": "REPORTED",
    "message": "Invoice reported successfully",
    "reported_at": "2024-01-15T10:30:00"
  },
  "processed_at": "2024-01-15T10:30:00"
}
```

### Error Handling

**Critical Behavior:** If reporting fails, the invoice **still succeeds** (clearance was successful). The reporting error is captured in the response:

```json
{
  "success": true,
  "clearance": {
    "clearance_status": "CLEARED",
    ...
  },
  "reporting": {
    "status": "FAILED",
    "error": "Reporting API error: Connection timeout",
    "note": "Reporting failed but clearance was successful. Invoice is cleared."
  }
}
```

### Database Storage

The reporting response is stored in `Invoice.zatca_response` JSON field:

```json
{
  "clearance_status": "CLEARED",
  "clearance_uuid": "uuid-from-zatca",
  "reporting_status": "REPORTED",
  "reporting_response": {
    "status": "REPORTED",
    "message": "Invoice reported successfully",
    "reported_at": "2024-01-15T10:30:00"
  }
}
```

**Implementation:** `backend/app/services/invoice_service.py:_update_invoice_after_processing()` (lines ~899-919)

## When Reporting is NOT Called

Reporting is **NOT** automatically called if:

1. **Clearance status is NOT "CLEARED"** (e.g., "REJECTED")
2. **No UUID available** (neither from clearance response nor request)

## Testing

### Unit Tests

**File:** `tests/backend/test_auto_reporting_after_clearance.py`

**Test Cases:**
1. ✅ Reporting is automatically called when clearance status is CLEARED
2. ✅ Reporting is NOT called when clearance status is REJECTED
3. ✅ Reporting failure does NOT fail the invoice (clearance still succeeds)
4. ✅ Reporting API headers include Clearance-Status and Accept-Version

### Running Tests

```bash
# Run all automatic reporting tests
python -m pytest tests/backend/test_auto_reporting_after_clearance.py -v

# Run specific test
python -m pytest tests/backend/test_auto_reporting_after_clearance.py::test_auto_reporting_after_cleared_clearance -v
```

## API Usage

### Request

```bash
POST /api/v1/invoices
Content-Type: application/json
X-API-Key: your-api-key

{
  "mode": "PHASE_2",
  "environment": "SANDBOX",
  "invoice_number": "INV-001",
  "invoice_date": "2024-01-15T10:00:00",
  "seller_name": "Test Seller",
  "seller_tax_number": "123456789012345",
  "line_items": [
    {
      "name": "Item 1",
      "quantity": 1,
      "unit_price": 100.0,
      "tax_rate": 15.0,
      "tax_category": "S"
    }
  ],
  "total_tax_exclusive": 100.0,
  "total_tax_amount": 15.0,
  "total_amount": 115.0
}
```

### Response (Success with Automatic Reporting)

```json
{
  "success": true,
  "invoice_number": "INV-001",
  "mode": "PHASE_2",
  "environment": "SANDBOX",
  "xml_data": {
    "xml_content": "<Invoice>...</Invoice>",
    "xml_hash": "abc123...",
    "signed_xml": "<SignedInvoice>...</SignedInvoice>",
    "digital_signature": "signature..."
  },
  "clearance": {
    "clearance_status": "CLEARED",
    "clearance_uuid": "uuid-from-zatca",
    "qr_code": "qr-code-base64",
    "reporting_status": "REPORTED"
  },
  "reporting": {
    "status": "REPORTED",
    "message": "Invoice reported successfully",
    "reported_at": "2024-01-15T10:30:00"
  },
  "processed_at": "2024-01-15T10:30:00"
}
```

## Migration Notes

### No Database Migration Required

The `Invoice.zatca_response` field already exists as a JSON column, so no migration is needed. The reporting response is merged into the existing JSON structure.

### Backward Compatibility

- ✅ Existing API responses remain compatible
- ✅ `reporting` field is optional (only present when automatic reporting occurs)
- ✅ If reporting fails, invoice still succeeds (non-breaking)

## Related Files

- **Service Logic:** `backend/app/services/invoice_service.py`
- **Clearance Service:** `backend/app/services/phase2/clearance_service.py`
- **Sandbox Client:** `backend/app/integrations/zatca/sandbox.py`
- **Production Client:** `backend/app/integrations/zatca/production.py`
- **Response Schema:** `backend/app/schemas/invoice.py`
- **Tests:** `tests/backend/test_auto_reporting_after_clearance.py`

## Summary

✅ **Automatic reporting after clearance is fully implemented**

- Reporting is called automatically when clearance status is `CLEARED`
- Reporting response is stored in database and API response
- Reporting failures do NOT fail the invoice (clearance still succeeds)
- Proper headers are included per ZATCA Developer Portal Manual
- Comprehensive unit tests cover all scenarios

