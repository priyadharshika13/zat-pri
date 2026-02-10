# Invoice Lifecycle

## Status Flow

Invoices progress through a defined status lifecycle from creation to final state.

## Status States

**CREATED:**
- Invoice record created in database
- No processing has occurred
- Initial state after invoice creation

**PROCESSING:**
- Invoice is being processed
- Validation or ZATCA submission in progress
- Intermediate state during processing

**CLEARED:**
- Invoice successfully cleared by ZATCA
- Final state for successful Phase-2 invoices
- Phase-1 invoices also marked as CLEARED

**REJECTED:**
- Invoice rejected by ZATCA or validation
- Final state for rejected invoices
- Can be retried if correctable

**FAILED:**
- Processing failed due to system error
- Final state for failed invoices
- Can be retried after fixing system issues

## Lifecycle Transitions

### Normal Flow (Phase-1)

1. **CREATED** → Invoice record created
2. **PROCESSING** → Validation and QR generation
3. **CLEARED** → QR code generated successfully

### Normal Flow (Phase-2)

1. **CREATED** → Invoice record created
2. **PROCESSING** → Validation, XML generation, signing, clearance
3. **CLEARED** → ZATCA clearance successful

### Validation Failure Flow

1. **CREATED** → Invoice record created
2. **REJECTED** → Validation failed, invoice rejected

### ZATCA Rejection Flow

1. **CREATED** → Invoice record created
2. **PROCESSING** → Submitted to ZATCA
3. **REJECTED** → ZATCA rejected invoice

### System Error Flow

1. **CREATED** → Invoice record created
2. **PROCESSING** → Processing started
3. **FAILED** → System error occurred

### Retry Flow

1. **FAILED/REJECTED** → Invoice in retryable state
2. **PROCESSING** → Retry processing started
3. **CLEARED/REJECTED/FAILED** → Final state after retry

## State Transitions Rules

**Allowed Transitions:**
- CREATED → PROCESSING (normal processing)
- CREATED → REJECTED (validation failure)
- PROCESSING → CLEARED (success)
- PROCESSING → REJECTED (ZATCA rejection)
- PROCESSING → FAILED (system error)
- FAILED → PROCESSING (retry)
- REJECTED → PROCESSING (retry)

**Immutable States:**
- CLEARED invoices cannot transition to other states
- CLEARED invoices cannot be retried

**Retry Restrictions:**
- Only FAILED or REJECTED invoices can be retried
- CREATED invoices should use regular processing endpoint
- PROCESSING invoices cannot be retried (already in progress)

## Invoice Creation

**Trigger:** `POST /api/v1/invoices`

**Process:**
1. Request validated (schema, subscription limits)
2. Invoice record created (status: CREATED)
3. Idempotency check (tenant_id + invoice_number)
4. Duplicate detection (raises error if exists)

**Database Operations:**
- INSERT into `invoices` table
- Status set to CREATED
- Timestamps set (created_at, updated_at)

## Invoice Processing

**Trigger:** Automatic after creation (same request)

**Process:**
1. Status updated to PROCESSING
2. Phase-specific validation executed
3. If validation fails: status → REJECTED, return
4. Policy Check: Clearance Allowed? (Phase-2 only)
   - Validates environment and invoice-type policy
   - Rejects if policy violation detected
   - Policy rules enforced before ZATCA API calls
5. If validation passes: continue processing
6. Phase-specific processing:
   - Phase-1: QR code generation
   - Phase-2: XML generation, signing, ZATCA clearance
7. Policy Check: Reporting Allowed? (after clearance, Phase-2 only)
   - Validates automatic reporting is allowed
   - Skips reporting if policy blocks (non-blocking)
   - Clearance success preserved even if reporting blocked
8. Status updated based on result

**Database Operations:**
- UPDATE invoice status to PROCESSING
- UPDATE invoice with results (status, UUID, hash, XML, response)
- INSERT into `invoice_logs` table

## Invoice Completion

**Success Path:**
- Status: CLEARED
- UUID, hash, XML stored (Phase-2)
- ZATCA response stored
- InvoiceLog entry created

**Rejection Path:**
- Status: REJECTED
- Error message stored
- ZATCA error code stored
- InvoiceLog entry created

**Failure Path:**
- Status: FAILED
- Error message stored
- Exception details logged
- InvoiceLog entry created

## Retry Processing

**Trigger:** `POST /api/v1/invoices/{invoice_id}/retry`

**Process:**
1. Invoice fetched with tenant isolation
2. Status validated (must be FAILED or REJECTED)
3. Original request reconstructed from InvoiceLog
4. RETRY audit log entry created
5. Status updated to PROCESSING
6. Normal processing flow executed
7. Status updated based on result

**Database Operations:**
- SELECT invoice (with tenant filter)
- UPDATE invoice status to PROCESSING
- INSERT InvoiceLog (action: RETRY)
- UPDATE invoice with results
- INSERT InvoiceLog (processing result)

## Idempotency

**Enforcement:**
- Unique constraint: (tenant_id, invoice_number)
- Duplicate submissions rejected
- Existing invoice returned if already exists

**Behavior:**
- First submission: creates new invoice
- Duplicate submission: raises ValueError
- Status check: CLEARED/PROCESSING invoices cannot be resubmitted

## Audit Trail

**InvoiceLog Entries:**
- Created for every processing attempt
- Includes request payload, generated XML, ZATCA response
- Status tracked per log entry
- Action field indicates retry operations

**Log Lifecycle:**
- SUBMITTED: Processing started
- CLEARED: Successfully cleared
- REJECTED: Rejected by ZATCA
- ERROR: System error occurred

## Current Implementation Status

All lifecycle components are implemented:

- Status flow with all transitions
- Invoice creation and processing
- Retry operations
- Idempotency enforcement
- Audit trail logging

Future considerations (not currently implemented):

- Status change webhooks
- Automated retry scheduling
- Status change notifications
- Bulk status updates

