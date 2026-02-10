# Invoice Domain Refactoring - Enterprise Architecture

## Overview

This document describes the comprehensive refactoring of the invoice domain to follow enterprise-grade architecture principles and ZATCA compliance requirements.

## Problem Statement

### Previous Architecture Issues

1. **No Invoice Master Entity**: Only `InvoiceLog` existed, which is an event log, not master data
2. **No Persistence Before Processing**: Invoices were not persisted until AFTER ZATCA processing completed
3. **No Idempotency**: Duplicate invoice submissions were possible
4. **Inconsistent Status Management**: Status updates happened in routes, not service layer
5. **Missing Error Handling**: Failed invoices were not persisted
6. **Incomplete Logging**: InvoiceLog was not always written (especially on failures)

## Solution Architecture

### STEP 1: Analysis

**Current State:**
- Routes: `/api/v1/invoices` (POST, GET, GET /{id}, GET /{invoice_number}/status)
- Models: `InvoiceLog` (event log), legacy `Invoice` (unused)
- Services: `InvoiceService` (orchestration), `InvoiceLogService` (logging), `InvoiceHistoryService` (queries)
- Data Flow: Request → Process → Create Log (only on success)

**Gaps Identified:**
1. No master invoice entity
2. Invoice not persisted before processing
3. No idempotency enforcement
4. Status updates in routes, not service
5. Error handling doesn't persist failed invoices
6. InvoiceLog not always written

### STEP 2: Invoice Master Entity

**New Model: `Invoice`** (`backend/app/models/invoice.py`)

```python
class Invoice(Base):
    __tablename__ = "invoices"
    
    # Primary key
    id: int
    
    # Tenant isolation (CRITICAL)
    tenant_id: int  # ForeignKey to tenants.id
    
    # Invoice identification
    invoice_number: str  # Unique per tenant
    
    # ZATCA compliance fields
    phase: InvoiceMode  # PHASE_1 or PHASE_2
    status: InvoiceStatus  # CREATED, PROCESSING, CLEARED, REJECTED, FAILED
    environment: Environment  # SANDBOX or PRODUCTION
    
    # Financial totals
    total_amount: float
    tax_amount: float
    
    # ZATCA Phase-2 fields (nullable)
    hash: str | None  # XML hash
    uuid: str | None  # Invoice UUID from ZATCA
    
    # XML content (nullable for Phase-1)
    xml_content: str | None
    
    # ZATCA response (full JSON)
    zatca_response: dict | None
    
    # Error tracking
    error_message: str | None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    # Unique constraint: (tenant_id, invoice_number)
    __table_args__ = (
        UniqueConstraint('tenant_id', 'invoice_number', name='uq_invoices_tenant_invoice_number'),
        Index('ix_invoices_tenant_status', 'tenant_id', 'status'),
        Index('ix_invoices_tenant_created', 'tenant_id', 'created_at'),
    )
```

**Key Features:**
- Tenant-scoped with strict isolation
- Idempotency via unique constraint
- Status tracking throughout lifecycle
- Full ZATCA response storage
- Error message persistence

### STEP 3: Database Migration

**Migration: `006_create_invoices_master_table.py`**

- Creates `invoices` table with all required fields
- Adds unique constraint for idempotency: `(tenant_id, invoice_number)`
- Creates indexes for performance:
  - `ix_invoices_tenant_id`
  - `ix_invoices_invoice_number`
  - `ix_invoices_status`
  - `ix_invoices_hash`
  - `ix_invoices_uuid`
  - `ix_invoices_tenant_status` (composite)
  - `ix_invoices_tenant_created` (composite)
- SQLite and PostgreSQL compatible

### STEP 4: Service Layer Refactor

**New Method: `process_invoice_with_persistence()`**

This is the new enterprise-grade entry point that:

1. **Checks Idempotency**: Verifies no duplicate `(tenant_id, invoice_number)`
2. **Creates Invoice**: Persists invoice with status `CREATED` BEFORE processing
3. **Updates Status**: Changes to `PROCESSING` during processing
4. **Processes Invoice**: Calls existing `process_invoice()` method
5. **Updates Results**: Updates invoice with UUID, hash, XML, ZATCA response
6. **Creates InvoiceLog**: Always writes log entry (success and failure)
7. **Handles Errors**: Marks invoice as `FAILED` on exception

**Helper Methods Added:**

- `_create_or_get_invoice()`: Creates invoice or returns existing (idempotency)
- `_update_invoice_status()`: Updates invoice status
- `_update_invoice_after_processing()`: Updates invoice with processing results
- `_create_invoice_log()`: Ensures InvoiceLog is always written

**Backward Compatibility:**

- Original `process_invoice()` method still exists
- Routes can use either method (new code uses persistence method)

### STEP 5: Logging Fix

**InvoiceLog Always Written:**

- Success: Log created with status `SUBMITTED`, `CLEARED`, or `REJECTED`
- Failure: Log created with status `ERROR`
- Linked to invoice via `invoice_id` (implicit via invoice_number)

**Logging Flow:**
1. Invoice created → Status: CREATED
2. Processing starts → Status: PROCESSING
3. Processing completes → Status: CLEARED/REJECTED/FAILED
4. InvoiceLog created → Status: SUBMITTED/CLEARED/REJECTED/ERROR

### STEP 6: Failure Handling

**Error Handling Flow:**

1. Exception caught in `process_invoice_with_persistence()`
2. Invoice status updated to `FAILED`
3. Error message stored in `invoice.error_message`
4. InvoiceLog created with status `ERROR`
5. Exception re-raised for route handling

**Status Progression:**
```
CREATED → PROCESSING → CLEARED (success)
                      REJECTED (ZATCA rejection)
                      FAILED (exception)
```

### STEP 7: Idempotency

**Enforcement:**

- Database unique constraint: `(tenant_id, invoice_number)`
- Service-level check before processing
- Returns existing invoice if duplicate detected
- Raises `ValueError` if invoice already processed

**Idempotency Rules:**

- Same `(tenant_id, invoice_number)` → Returns existing invoice
- If status is `CLEARED` or `PROCESSING` → Raises error (duplicate submission)
- If status is `CREATED` or `FAILED` → Can be retried

### STEP 8: Testing

**Unit Tests:** `tests/backend/test_invoice_persistence.py`

1. **Successful Invoice**: Verifies creation, status updates, log creation
2. **Rejected Invoice**: Verifies REJECTED status and log
3. **Duplicate Invoice**: Verifies idempotency enforcement
4. **Failed Invoice**: Verifies FAILED status and error message
5. **Status Progression**: Verifies status changes during processing

## API Changes

### No Breaking Changes

- All existing endpoints remain unchanged
- Response schemas unchanged
- Backward compatible with existing clients

### Internal Changes

- Routes now use `process_invoice_with_persistence()` instead of `process_invoice()`
- InvoiceService constructor accepts optional `db` and `tenant_context`
- New dependency injection in routes

## Migration Guide

### For Developers

1. **Run Migration**: `alembic upgrade head`
2. **Update Code**: No changes required (backward compatible)
3. **New Features**: Use `process_invoice_with_persistence()` for new code

### For Database Administrators

1. **Backup Database**: Before running migration
2. **Run Migration**: `alembic upgrade head`
3. **Verify**: Check `invoices` table exists with correct schema
4. **Monitor**: Watch for any constraint violations

## Benefits

1. **Data Integrity**: Invoice always persisted, even on failure
2. **Idempotency**: Prevents duplicate submissions
3. **Audit Trail**: Complete history via Invoice + InvoiceLog
4. **Error Recovery**: Failed invoices can be retried
5. **Status Tracking**: Clear status progression
6. **ZATCA Compliance**: Full response storage for audit

## Performance Considerations

- **Indexes**: Optimized for tenant-scoped queries
- **Transactions**: Proper DB transaction handling
- **Race Conditions**: Handled via unique constraint
- **Query Performance**: Composite indexes for common queries

## Future Enhancements

1. **Invoice Retry**: Automatic retry for FAILED invoices
2. **Status Webhooks**: Notify on status changes
3. **Bulk Operations**: Batch invoice processing
4. **Invoice Versioning**: Track invoice revisions
5. **Advanced Filtering**: More query options

## Conclusion

This refactoring transforms the invoice domain from an event-log-only architecture to a proper master-data architecture with:

- ✅ Invoice master entity
- ✅ Persistence before processing
- ✅ Idempotency enforcement
- ✅ Complete error handling
- ✅ Always-written logs
- ✅ Enterprise-grade architecture

The refactoring maintains backward compatibility while providing a solid foundation for future enhancements.

