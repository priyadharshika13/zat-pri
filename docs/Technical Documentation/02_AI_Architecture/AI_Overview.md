# AI Overview

## AI Service Architecture

AI services provide advisory intelligence for ZATCA compliance operations. All AI operations are optional, non-blocking, and never interfere with compliance logic.

## AI Service Layer

**Location:** `app/ai/` and `app/services/ai/`

**Components:**
- OpenRouterService: Unified AI gateway interface
- ZATCAErrorExplainer: Error explanation service
- RejectionPredictor: Invoice rejection prediction
- PrecheckAdvisor: Pre-submission risk analysis
- RootCauseEngine: Failure root cause analysis
- ReadinessScorer: Compliance maturity scoring
- ErrorTrendAnalyzer: Trend analysis and anomaly detection

## Global AI Toggle

**Configuration:** `ENABLE_AI_EXPLANATION` environment variable

**Behavior:**
- When `false`: All AI services return disabled responses
- When `true`: AI services function normally
- Default: `false` (enterprise-safe default)

**Implementation:**
- Checked at service initialization
- All AI services respect global toggle
- Graceful fallback when disabled
- No exceptions raised when disabled

## AI Service Interface

All AI services follow consistent interface:

1. **Initialization Check**
   - Verify `ENABLE_AI_EXPLANATION` is true
   - Initialize OpenRouter service if enabled
   - Set `ai_enabled` flag

2. **Method Execution**
   - Check `ai_enabled` flag before processing
   - Return disabled response if AI not enabled
   - Call OpenRouter service if enabled

3. **Error Handling**
   - Catch OpenRouter exceptions
   - Return graceful fallback responses
   - Log errors without breaking compliance flow

## OpenRouter Integration

**Service:** `app/services/ai/openrouter_service.py`

**Configuration:**
- `OPENROUTER_API_KEY`: API key for authentication
- `OPENROUTER_BASE_URL`: Base URL (default: https://openrouter.ai/api/v1)
- `OPENROUTER_DEFAULT_MODEL`: Default model (default: openai/gpt-4o-mini)
- `OPENROUTER_TIMEOUT`: Request timeout (default: 60 seconds)

**Features:**
- Unified interface for all AI operations
- Token usage tracking
- Error handling and retries
- Timeout management

## AI Service Capabilities

### Error Explanation

**Service:** `ZATCAErrorExplainer`

**Functionality:**
- Translates ZATCA error codes to human-readable explanations
- Provides step-by-step fix guidance
- Bilingual support (English, Arabic)

**Input:**
- ZATCA error response dictionary
- Optional: Include Arabic explanation

**Output:**
- Plain English explanation
- Optional Arabic explanation
- Step-by-step fix guidance

### Rejection Prediction

**Service:** `RejectionPredictor`

**Functionality:**
- Predicts invoice rejection likelihood before submission
- Identifies likely rejection reasons
- Risk levels: LOW, MEDIUM, HIGH

**Input:**
- Invoice request payload

**Output:**
- Rejection risk level
- Likely rejection reasons
- Confidence score

### Pre-Check Advisor

**Service:** `PrecheckAdvisor`

**Functionality:**
- Field-level risk analysis
- Identifies risky patterns before submission
- Actionable warnings with JSONPath pointers

**Input:**
- Invoice request payload

**Output:**
- List of warnings with field pointers
- Risk level per warning
- Actionable recommendations

### Root Cause Analysis

**Service:** `RootCauseEngine`

**Functionality:**
- Analyzes historical invoice data
- Identifies primary and secondary causes
- Provides prevention checklists

**Input:**
- Historical invoice data (tenant-scoped)

**Output:**
- Primary root cause
- Secondary causes
- Prevention checklist

### Readiness Scoring

**Service:** `ReadinessScorer`

**Functionality:**
- Tenant-level compliance health score (0-100)
- Status classification: GREEN, AMBER, RED
- Risk factors and improvement suggestions

**Input:**
- Tenant context (implicit)

**Output:**
- Compliance score (0-100)
- Status classification
- Risk factors
- Improvement suggestions

### Error Trend Analysis

**Service:** `ErrorTrendAnalyzer`

**Functionality:**
- Time-based trend analysis
- Emerging risk detection
- Operational recommendations

**Input:**
- Time range (optional)
- Tenant scope (tenant or global)

**Output:**
- Trend analysis
- Emerging risks
- Operational recommendations

## AI Data Isolation

**Tenant Scoping:**
- All AI operations are tenant-scoped
- No cross-tenant data access
- Tenant context required for all operations

**Data Storage:**
- AI services do not store invoice data
- Only usage metrics tracked (token counts)
- No PII stored in AI systems

**Privacy:**
- Invoice data sent to OpenRouter for processing
- Data not stored by OpenRouter (per API contract)
- Tenant isolation enforced at API level

## AI Governance

**Global Toggle:**
- `ENABLE_AI_EXPLANATION` controls all AI services
- Can be disabled without code changes
- Enterprise-safe default (disabled)

**Subscription Limits:**
- Per-plan AI usage limits
- Token usage tracked per tenant
- Limits enforced before AI invocation

**Error Handling:**
- AI failures never break compliance flow
- Graceful fallback responses
- Errors logged but not exposed to clients

## Current Implementation Status

All AI services are implemented and production-ready:

- Error explanation with bilingual support
- Rejection prediction
- Pre-check advisor
- Root cause analysis
- Readiness scoring
- Error trend analysis
- Global AI toggle
- Subscription limits

Future considerations (not currently implemented):

- Custom AI model training
- On-premise AI deployment
- Advanced prompt engineering
- AI response caching

