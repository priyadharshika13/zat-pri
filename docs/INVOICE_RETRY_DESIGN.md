# Invoice Retry/Reprocess API - Design Documentation

## Overview

The Invoice Retry API allows clients to safely retry processing of FAILED or REJECTED invoices in a ZATCA-compliant, fully auditable manner. This feature enables recovery from transient failures and reprocessing of invoices that were rejected due to correctable issues.

## API Endpoint

```
POST /api/v1/invoices/{invoice_id}/retry
```

**Authentication:** Required (API key via `X-API-Key` header)

**Response:** `InvoiceResponse` (same as regular invoice processing)

## Design Principles

### 1. Safety First

- **Only FAILED or REJECTED invoices can be retried**
  - CLEARED invoices are immutable and cannot be retried
  - PROCESSING invoices are already in progress
  - CREATED invoices should use the regular processing endpoint

- **Tenant Isolation**
  - Invoice must belong to the authenticated tenant
  - Cross-tenant retry attempts return 404 (not found)

- **Idempotency**
  - Invoice master record is **reused** (no new invoice row created)
  - Same invoice ID is maintained throughout retry

### 2. Status Flow

The retry operation follows this status lifecycle:

```
FAILED/REJECTED → PROCESSING → CLEARED/REJECTED/FAILED
```

**Key Points:**
- Previous status is stored in audit log (`previous_status` field)
- Error message is cleared when status changes to PROCESSING
- Final status depends on processing result

### 3. Audit Trail

Every retry operation creates **two** audit log entries:

1. **RETRY Log Entry** (created before processing)
   - `action = "RETRY"`
   - `previous_status = "FAILED"` or `"REJECTED"`
   - `status = "SUBMITTED"`
   - Contains original request payload

2. **Processing Result Log Entry** (created after processing)
   - `action = None` (normal processing log)
   - `status = "CLEARED"`, `"REJECTED"`, or `"ERROR"`
   - Contains processing result and ZATCA response

### 4. Request Reconstruction

The retry operation reconstructs the original `InvoiceRequest` from the most recent `InvoiceLog.request_payload`. This ensures:

- Same invoice data is used for retry
- Phase and environment are preserved
- All line items and totals are maintained

**Requirements:**
- Original request payload must exist in `InvoiceLog`
- If payload is missing, retry fails with clear error message

## Implementation Details

### Service Method

```python
async def retry_invoice(
    self,
    db: Session,
    invoice_id: int,
    tenant_context: TenantContext
) -> InvoiceResponse
```

**Execution Flow:**

1. **Validation**
   - Get invoice by ID with tenant isolation
   - Verify status is FAILED or REJECTED
   - Raise ValueError if invalid

2. **Request Reconstruction**
   - Get most recent InvoiceLog for invoice
   - Extract `request_payload` from log
   - Reconstruct `InvoiceRequest` object
   - Ensure mode and environment match invoice

3. **Status Update**
   - Update invoice status to PROCESSING
   - Clear error_message field
   - Commit to database

4. **Audit Logging**
   - Create RETRY log entry with:
     - `action = "RETRY"`
     - `previous_status = invoice.status.value`
     - `status = InvoiceLogStatus.SUBMITTED`

5. **Processing**
   - Call `process_invoice()` (reuses existing logic)
   - No duplicate invoice creation (invoice already exists)

6. **Result Handling**
   - Update invoice with processing results
   - Create final processing log entry
   - Return `InvoiceResponse`

7. **Error Handling**
   - If processing fails, mark invoice as FAILED
   - Create error log entry
   - Re-raise exception

### Route Handler

```python
@router.post("/{invoice_id}/retry")
async def retry_invoice(
    invoice_id: int,
    tenant: TenantContext,
    service: InvoiceService,
    db: Session
) -> InvoiceResponse
```

**Error Handling:**

- **404 Not Found**: Invoice doesn't exist or doesn't belong to tenant
- **400 Bad Request**: Invoice status is CLEARED or invalid for retry
- **500 Internal Server Error**: Processing failure or system error

## Database Schema Changes

### InvoiceLog Model

Added two optional fields for retry tracking:

```python
action = Column(String(20), nullable=True, comment="Action type (e.g., 'RETRY', 'SUBMIT')")
previous_status = Column(String(20), nullable=True, comment="Previous invoice status before action")
```

**Migration:** `008_add_retry_tracking_to_invoice_logs.py`

## Usage Examples

### Retry a FAILED Invoice

```bash
curl -X POST "https://api.example.com/api/v1/invoices/123/retry" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "success": true,
  "invoice_number": "INV-2024-001",
  "mode": "PHASE_2",
  "environment": "SANDBOX",
  "clearance": {
    "clearance_status": "CLEARED",
    "clearance_uuid": "550e8400-e29b-41d4-a716-446655440000"
  },
  "processed_at": "2025-01-18T14:30:00Z"
}
```

### Retry a REJECTED Invoice

Same endpoint, same response format. The system automatically:
- Reconstructs the original request
- Processes with the same phase (Phase-1 or Phase-2)
- Updates status based on ZATCA response

### Error: Cannot Retry CLEARED Invoice

```bash
curl -X POST "https://api.example.com/api/v1/invoices/456/retry" \
  -H "X-API-Key: your-api-key"
```

**Response (400 Bad Request):**
```json
{
  "detail": "Cannot retry invoice INV-2024-002: Status is CLEARED. Only FAILED or REJECTED invoices can be retried."
}
```

## Testing

Comprehensive test coverage in `tests/backend/test_invoice_retry.py`:

- ✅ Retry FAILED invoice → success
- ✅ Retry REJECTED invoice → success
- ✅ Retry CLEARED invoice → rejected (400)
- ✅ Cross-tenant retry → forbidden (404)
- ✅ Audit log created on retry
- ✅ Status flow verification
- ✅ Processing failure handling
- ✅ Missing request payload handling

## ZATCA Compliance

The retry operation maintains full ZATCA compliance:

1. **No Duplicate Submissions**
   - Same invoice master record is reused
   - Idempotency is maintained via `(tenant_id, invoice_number)` uniqueness

2. **Full Audit Trail**
   - Every retry attempt is logged
   - Previous status is preserved
   - Processing results are stored

3. **Status Integrity**
   - Status transitions are atomic
   - No intermediate states are exposed
   - Error messages are preserved for debugging

4. **Request Fidelity**
   - Original request payload is used (no modifications)
   - Phase and environment are preserved
   - All invoice data is maintained

## Best Practices

### When to Use Retry

✅ **Good Use Cases:**
- Transient network failures
- ZATCA API temporary unavailability
- Correctable validation errors (after fixing data)
- System errors that don't affect invoice data

❌ **Bad Use Cases:**
- Changing invoice data (use new invoice submission)
- Retrying CLEARED invoices (they're final)
- Bypassing validation (fix data first)

### Retry Limits

Currently, there are **no built-in retry limits**. However, consider:

- Each retry creates audit log entries
- Excessive retries may indicate data quality issues
- Monitor retry patterns for anomalies

### Monitoring

Track retry operations via:

- `InvoiceLog` entries with `action = "RETRY"`
- Invoice status transitions
- Error message patterns
- Retry frequency per tenant

## Future Enhancements

Potential improvements:

1. **Retry Limits**
   - Maximum retries per invoice
   - Rate limiting per tenant

2. **Retry Policies**
   - Automatic retry with exponential backoff
   - Scheduled retry for specific error codes

3. **Retry Analytics**
   - Retry success rate metrics
   - Common failure patterns
   - Tenant-specific retry trends

## Summary

The Invoice Retry API provides a safe, auditable way to reprocess failed or rejected invoices while maintaining:

- ✅ ZATCA compliance
- ✅ Tenant isolation
- ✅ Full audit trail
- ✅ Status integrity
- ✅ Request fidelity

All retry operations are fully logged and traceable, ensuring compliance and enabling debugging when needed.

