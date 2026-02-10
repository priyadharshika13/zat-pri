# AI Decision Boundaries

## Regulatory Separation

AI services operate with strict boundaries that prevent interference with ZATCA compliance operations.

## Compliance Operations (AI-Free Zone)

The following operations never use AI and are 100% rule-based:

**Invoice Validation:**
- Phase-1 validation (Phase1Validator)
- Phase-2 validation (Phase2Validator)
- Field type checking, value ranges, required fields
- ZATCA specification compliance checks

**XML Generation:**
- UBL 2.1 XML structure generation (XMLGenerator)
- Namespace handling, element ordering
- XML canonicalization for hashing

**Cryptographic Operations:**
- XML hashing (SHA-256)
- Digital signature generation (XMLDSig, RSA-SHA256)
- Certificate loading and validation

**VAT Calculations:**
- Tax amount calculations from line items
- Total amount computations
- Tax rate validation (must be 15.00)

**ZATCA API Communication:**
- Clearance submission (ClearanceService)
- Invoice reporting
- Error response parsing

**Invoice Persistence:**
- Database operations (Invoice, InvoiceLog)
- Status updates, audit logging
- Idempotency enforcement

## AI Operations (Advisory-Only Zone)

AI services only provide advisory intelligence:

**Error Explanation:**
- Reads ZATCA error codes
- Generates human-readable explanations
- Does not modify error responses

**Rejection Prediction:**
- Analyzes invoice payload
- Predicts rejection likelihood
- Does not prevent submission

**Pre-Check Advisor:**
- Identifies risky fields
- Provides warnings
- Does not modify invoice data

**Root Cause Analysis:**
- Analyzes historical data
- Identifies patterns
- Does not modify invoices

**Readiness Scoring:**
- Calculates compliance health
- Provides recommendations
- Does not enforce changes

**Trend Analysis:**
- Detects emerging risks
- Provides insights
- Does not modify operations

## Decision Flow Boundaries

### Invoice Processing Flow

1. **Validation (Rule-Based)**
   - Phase-specific validator executes
   - No AI involvement
   - Validation result determines next step

2. **Processing (Rule-Based)**
   - Phase-1: QR code generation (rule-based)
   - Phase-2: XML generation, signing, clearance (rule-based)
   - No AI involvement in processing

3. **AI Advisory (Optional)**
   - AI services can be called after processing
   - AI provides explanations, predictions, analysis
   - AI output does not affect invoice status

### Error Handling Flow

1. **Error Detection (Rule-Based)**
   - ZATCA returns error response
   - Error code extracted (rule-based)
   - Error catalog maps code to message (rule-based)

2. **AI Explanation (Optional)**
   - AI service called with error code
   - AI generates explanation
   - Explanation added to response (non-blocking)

3. **Error Response (Rule-Based)**
   - Invoice status set to REJECTED (rule-based)
   - Error message included (rule-based)
   - AI explanation included (advisory only)

## Code-Level Boundaries

### Service Layer Separation

**Compliance Services:**
- No AI imports
- No AI method calls
- Pure rule-based logic

**AI Services:**
- No compliance logic
- No invoice modification
- Read-only operations

**Orchestration:**
- InvoiceService coordinates both layers
- Clear separation in method calls
- AI services called after compliance operations

### Data Flow Boundaries

**Compliance Data Flow:**
- InvoiceRequest → Validator → Processor → ZATCA → Response
- No AI in this flow
- Deterministic operations only

**AI Data Flow:**
- InvoiceRequest/ErrorResponse → AI Service → Explanation
- Separate from compliance flow
- Advisory output only

## Enforcement Mechanisms

### Configuration Enforcement

**Global Toggle:**
- `ENABLE_AI_EXPLANATION=false` disables all AI
- Compliance operations unaffected
- Graceful fallback when disabled

### Code Enforcement

**Service Initialization:**
- AI services check global toggle
- Return disabled state if toggle false
- No exceptions raised

**Method Execution:**
- AI methods check `ai_enabled` flag
- Return disabled response if not enabled
- Compliance flow continues normally

### Testing Enforcement

**Unit Tests:**
- Compliance services tested without AI
- AI services tested in isolation
- Integration tests verify separation

## Current Implementation Status

All decision boundaries are implemented and enforced:

- Clear separation between compliance and AI
- No AI in compliance operations
- AI services are advisory-only
- Global toggle for AI enable/disable
- Graceful fallback when AI disabled

Future considerations (not currently implemented):

- Runtime verification of AI boundaries
- Automated testing of separation
- Code analysis tools for boundary enforcement

