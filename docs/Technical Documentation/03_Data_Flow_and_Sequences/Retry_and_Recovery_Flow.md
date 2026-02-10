# Retry and Recovery Flow

## Retry Mechanism

The system provides retry capabilities for failed and rejected invoices with full audit trail support.

## Retry Eligibility

**Retryable States:**
- FAILED: System errors, network failures, timeouts
- REJECTED: ZATCA rejections, validation failures

**Non-Retryable States:**
- CLEARED: Successfully processed, immutable
- PROCESSING: Already in progress
- CREATED: Should use regular processing endpoint

## Retry Request Flow

### Endpoint

**POST** `/api/v1/invoices/{invoice_id}/retry`

**Authentication:** Required (API key)

**Authorization:**
- Invoice must belong to authenticated tenant
- Cross-tenant access returns 404

### Request Processing

1. **Invoice Lookup**
   - Fetch invoice by ID with tenant filter
   - Return 404 if not found or access denied

2. **Status Validation**
   - Verify status is FAILED or REJECTED
   - Return 400 if status invalid

3. **Request Reconstruction**
   - Fetch most recent InvoiceLog for invoice
   - Extract `request_payload` from log
   - Reconstruct `InvoiceRequest` object
   - Return 400 if payload missing

4. **Status Update**
   - Update invoice status to PROCESSING
   - Clear error_message field
   - Store previous status for audit

5. **Audit Log Creation**
   - Create InvoiceLog entry with action="RETRY"
   - Include previous_status in log
   - Store reconstructed request payload

6. **Processing Execution**
   - Execute normal invoice processing flow
   - Use reconstructed request payload
   - Same validation and processing logic

7. **Result Handling**
   - Update invoice with processing results
   - Create final InvoiceLog entry
   - Return InvoiceResponse

## Retry Status Flow

```
FAILED/REJECTED → PROCESSING → CLEARED/REJECTED/FAILED
```

**Previous Status Preservation:**
- Previous status stored in audit log
- Not stored in invoice record
- Used for audit trail only

## Error Handling

### Invoice Not Found

**Condition:** Invoice ID not found or access denied

**Response:** 404 Not Found

**Message:** "Invoice {invoice_id} not found or access denied"

### Invalid Status

**Condition:** Invoice status is not FAILED or REJECTED

**Response:** 400 Bad Request

**Message:** "Cannot retry invoice {invoice_number}: Status is {status}. Only FAILED or REJECTED invoices can be retried."

### Missing Request Payload

**Condition:** Original request payload not found in InvoiceLog

**Response:** 400 Bad Request

**Message:** "Cannot retry invoice {invoice_number}: Original request payload not found in audit logs."

### Processing Failure

**Condition:** Retry processing fails

**Response:** 500 Internal Server Error

**Behavior:**
- Invoice status set to FAILED
- Error message stored
- InvoiceLog entry created
- Exception re-raised

## Audit Trail

### RETRY Log Entry

**Created:** Before processing starts

**Fields:**
- `action`: "RETRY"
- `previous_status`: Original status (FAILED or REJECTED)
- `status`: "SUBMITTED"
- `request_payload`: Reconstructed request
- `submitted_at`: Current timestamp

### Processing Result Log Entry

**Created:** After processing completes

**Fields:**
- `action`: None (normal processing log)
- `status`: CLEARED, REJECTED, or ERROR
- `request_payload`: Reconstructed request
- `generated_xml`: Generated XML (Phase-2)
- `zatca_response`: ZATCA response
- `submitted_at`: Processing timestamp
- `cleared_at`: Timestamp if cleared

## Request Reconstruction

### Source Data

**Location:** Most recent InvoiceLog entry

**Field:** `request_payload` (JSON)

**Requirements:**
- Must exist in InvoiceLog
- Must be valid JSON
- Must contain all required invoice fields

### Reconstruction Process

1. Query InvoiceLog for invoice
2. Order by `created_at` descending
3. Take most recent entry
4. Extract `request_payload` field
5. Validate JSON structure
6. Create `InvoiceRequest` object
7. Ensure mode and environment match invoice

### Validation

**Mode Validation:**
- Request mode must match invoice phase
- Set from invoice.phase if mismatch

**Environment Validation:**
- Request environment must match invoice.environment
- Set from invoice.environment if mismatch

## Idempotency

**Invoice Record:**
- Same invoice record reused (no new invoice created)
- Invoice ID remains constant
- Status transitions within same record

**Audit Log:**
- New InvoiceLog entry created for each retry
- Multiple retry attempts tracked
- Full history maintained

## Recovery Scenarios

### Transient Network Failure

**Scenario:** ZATCA API timeout or network error

**Recovery:**
1. Invoice status: FAILED
2. Error message: Network error details
3. Retry: Reconstruct request, resubmit
4. Expected: Success on retry

### ZATCA Rejection (Correctable)

**Scenario:** Invoice rejected due to fixable issue

**Recovery:**
1. Invoice status: REJECTED
2. Error message: ZATCA error code
3. Fix: Correct invoice data in source system
4. Retry: Submit corrected invoice (new invoice_number)
5. Note: Cannot retry same invoice_number, must create new invoice

### Validation Failure

**Scenario:** Invoice fails validation before ZATCA submission

**Recovery:**
1. Invoice status: REJECTED
2. Error message: Validation error details
3. Fix: Correct validation errors
4. Retry: Reconstruct request, resubmit
5. Expected: Success if errors fixed

### System Error

**Scenario:** Application error during processing

**Recovery:**
1. Invoice status: FAILED
2. Error message: Exception details
3. Fix: Resolve system issue
4. Retry: Reconstruct request, resubmit
5. Expected: Success if issue resolved

## Current Implementation Status

All retry and recovery components are implemented:

- Retry endpoint with validation
- Request reconstruction from audit logs
- Status flow management
- Audit trail logging
- Error handling

Future considerations (not currently implemented):

- Automated retry scheduling
- Exponential backoff for retries
- Retry limit enforcement
- Retry notification webhooks

