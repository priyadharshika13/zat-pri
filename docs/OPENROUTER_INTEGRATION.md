# OpenRouter Integration Documentation

## Overview

All AI-powered endpoints in the ZATCA Compliance API now use **OpenRouter** as the unified AI gateway. OpenRouter provides access to multiple AI models through a single API, enabling flexibility, cost optimization, and simplified management.

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# OpenRouter Configuration
OPENROUTER_API_KEY=sk-or-v1-...          # Your OpenRouter API key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1  # Default, can be overridden
OPENROUTER_DEFAULT_MODEL=openai/gpt-4o-mini       # Default model for all endpoints
OPENROUTER_TIMEOUT=60                            # Request timeout in seconds
```

### Settings

The following settings are available in `app/core/config.py`:

- `openrouter_api_key`: OpenRouter API key (required)
- `openrouter_base_url`: Base URL (default: `https://openrouter.ai/api/v1`)
- `openrouter_default_model`: Default model (default: `openai/gpt-4o-mini`)
- `openrouter_timeout`: Request timeout in seconds (default: 60)

## Architecture

### Service Layer

**File:** `app/services/ai/openrouter_service.py`

The `OpenRouterService` provides a unified interface for all AI calls:

```python
async def call_openrouter(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    response_format: Optional[Dict[str, str]] = None
) -> Dict[str, Any]
```

**Features:**
- Automatic authentication with required headers
- Timeout handling
- Error handling and logging
- Token usage tracking
- Response parsing

### AI Service Updates

All AI services have been updated to use OpenRouter:

1. `app/ai/zatca_explainer.py` - Error explanation
2. `app/ai/rejection_predictor.py` - Rejection prediction
3. `app/ai/precheck_advisor.py` - Pre-check advisor
4. `app/ai/root_cause_engine.py` - Root cause analysis
5. `app/ai/readiness_scorer.py` - Readiness scoring
6. `app/ai/error_trend_analyzer.py` - Error trend analysis

**Changes:**
- Removed direct OpenAI client initialization
- Replaced with OpenRouter service singleton
- Maintained all existing behavior and fallback logic
- Added token usage logging

## Prompt Strategy

### 1. Error Explanation (`/api/v1/ai/explain-zatca-error`)

**Purpose:** Provide clear, business-friendly explanations of ZATCA errors in English and Arabic.

**System Prompt:**
- Enforces explanation-only behavior
- Prohibits any data modification
- Emphasizes clarity and user-friendliness

**User Prompt Structure:**
1. Error code and message
2. Rule-based error information (as context)
3. Request for:
   - Plain English explanation
   - Arabic explanation (if requested)
   - Step-by-step fix guidance

**Output Format:**
- Plain text or JSON
- Parsed into structured response with English/Arabic explanations and fix steps

**Key Design Decisions:**
- Uses rule-based catalog as context (not replacement)
- Focuses on SME-friendly language (non-technical)
- Provides actionable fix steps
- Bilingual support for Saudi market

### 2. Rejection Prediction (`/api/v1/ai/predict-rejection`)

**Purpose:** Predict invoice rejection likelihood before submission.

**System Prompt:**
- Enforces prediction-only behavior
- Requires JSON response format
- Prohibits data modification

**User Prompt Structure:**
1. Invoice payload (read-only, for analysis)
2. Historical context (tenant rejection patterns)
3. Rule-based precheck signals
4. Target environment
5. Common ZATCA rejection causes (reference)

**Output Format:**
- **Required:** JSON with exact structure:
  ```json
  {
    "risk_level": "LOW" | "MEDIUM" | "HIGH",
    "confidence": 0.0-1.0,
    "likely_reasons": ["reason1", "reason2"],
    "advisory_note": "Short message"
  }
  ```

**Key Design Decisions:**
- Combines rule-based signals with AI analysis
- Considers historical tenant patterns
- Provides actionable advisory notes
- Uses lower temperature (0.2) for consistency

### 3. Pre-Check Advisor (`/api/v1/ai/precheck-advisor`)

**Purpose:** Identify risky fields and patterns before submission.

**System Prompt:**
- Enforces advisory-only behavior
- Requires JSON response format
- Emphasizes machine-readable output

**User Prompt Structure:**
1. Invoice payload (read-only)
2. Rule-based precheck signals
3. Target environment
4. ZATCA compliance requirements (reference)

**Output Format:**
- **Required:** JSON with:
  ```json
  {
    "warnings": ["warning1", "warning2"],
    "risk_fields": ["field1", "field2"],
    "advisory_notes": "Summary",
    "risk_score": "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN"
  }
  ```

**Key Design Decisions:**
- JSONPath-like pointers for risk fields
- Machine-readable for integration
- Combines rule-based and AI analysis
- Focuses on actionable warnings

### 4. Root Cause Analysis (`/api/v1/ai/root-cause-analysis`)

**Purpose:** Identify WHY failures occur, not just WHAT failed.

**System Prompt:**
- Enforces analysis-only behavior
- Requires JSON response format
- Emphasizes systemic root cause identification

**User Prompt Structure:**
1. Error code and message
2. Rule-based explanation (as context)
3. Historical context (tenant error patterns)
4. Target environment

**Output Format:**
- **Required:** JSON with:
  ```json
  {
    "primary_cause": "Main root cause",
    "secondary_causes": ["factor1", "factor2"],
    "prevention_checklist": ["step1", "step2"],
    "confidence": 0.0-1.0
  }
  ```

**Key Design Decisions:**
- Focuses on systemic causes, not symptoms
- Provides prevention strategies
- Considers historical patterns
- Actionable prevention checklist

### 5. Readiness Score (`/api/v1/ai/readiness-score`)

**Purpose:** Provide tenant-level compliance health score (0-100).

**System Prompt:**
- Enforces scoring-only behavior
- Requires JSON response format
- Emphasizes explainable scoring

**User Prompt Structure:**
1. Aggregated tenant metrics:
   - Rejection rate trend
   - Error diversity
   - Recurring errors
   - Improvement/deterioration
2. Analysis period (30d, 90d, all)

**Output Format:**
- **Required:** JSON with:
  ```json
  {
    "readiness_score": 0-100,
    "status": "GREEN" | "AMBER" | "RED" | "UNKNOWN",
    "risk_factors": ["factor1", "factor2"],
    "improvement_suggestions": ["suggestion1", "suggestion2"],
    "confidence": 0.0-1.0
  }
  ```

**Key Design Decisions:**
- Single explainable score (0-100)
- Status classification for dashboards
- Actionable improvement suggestions
- Rule-based heuristics + AI synthesis

### 6. Error Trends (`/api/v1/ai/error-trends`)

**Purpose:** Analyze time-based error trends and emerging risks.

**System Prompt:**
- Enforces insight-only behavior
- Requires JSON response format
- Emphasizes trend-level intelligence

**User Prompt Structure:**
1. Error statistics (aggregated, anonymized)
2. Time period comparison (current vs previous)
3. Analysis period and scope (tenant or global)

**Output Format:**
- **Required:** JSON with:
  ```json
  {
    "top_errors": [
      {
        "error_code": "ZATCA-2001",
        "trend": "INCREASING" | "STABLE" | "DECREASING",
        "count": 10
      }
    ],
    "emerging_risks": ["risk1", "risk2"],
    "trend_summary": "Narrative summary",
    "recommended_actions": ["action1", "action2"],
    "confidence": 0.0-1.0
  }
  ```

**Key Design Decisions:**
- Trend-level intelligence (not transaction-level)
- Detects statistically meaningful changes (>10%)
- Operational recommendations
- Supports tenant and global scope

## Token Usage Tracking

All OpenRouter calls log token usage for monitoring:

```python
logger.debug(
    f"OpenRouter token usage: prompt={usage.get('prompt_tokens', 0)}, "
    f"completion={usage.get('completion_tokens', 0)}, total={usage.get('total_tokens', 0)}"
)
```

**Note:** Token usage is logged but not stored in the database per requirements. This can be extended for billing/analytics if needed.

## Error Handling

The OpenRouter service handles:

1. **Timeouts:** Returns clear error message
2. **HTTP Errors:** Extracts and logs error details
3. **Connection Errors:** Graceful fallback
4. **Invalid Responses:** Fallback to rule-based logic

All errors are logged but never expose internal details to users.

## Fallback Behavior

When OpenRouter is unavailable or AI is disabled:

1. **Error Explanation:** Falls back to rule-based error catalog
2. **Rejection Prediction:** Falls back to rule-based precheck signals
3. **Pre-Check Advisor:** Falls back to rule-based warnings
4. **Root Cause Analysis:** Returns disabled message
5. **Readiness Score:** Returns UNKNOWN status
6. **Error Trends:** Returns disabled message

**Critical:** All fallbacks maintain API contract and never break compliance operations.

## Model Selection

**Default Model:** `openai/gpt-4o-mini`

**Rationale:**
- Cost-effective for high-volume usage
- Good balance of quality and speed
- Supports JSON response format
- Available through OpenRouter

**Future Override:**
- Models can be overridden per endpoint (not yet implemented)
- Configuration allows easy model switching
- OpenRouter supports 100+ models

## Security & Privacy

**No Secrets in Logs:**
- API keys never logged
- Invoice payloads never logged
- Only error codes and metadata logged

**No Raw Prompts in DB:**
- Prompts are constructed at runtime
- No prompt storage or retrieval
- Only aggregated metrics stored

**Tenant Isolation:**
- All AI calls scoped to tenant context
- Historical data filtered by tenant_id
- No cross-tenant data leakage

## Testing

### Manual Testing

1. Set `OPENROUTER_API_KEY` in `.env`
2. Set `ENABLE_AI_EXPLANATION=true`
3. Test each endpoint with sample data
4. Verify token usage in logs
5. Test fallback behavior (disable AI toggle)

### Integration Testing

- Test with invalid API key
- Test with timeout scenarios
- Test with malformed responses
- Verify fallback behavior

## Migration Notes

**Breaking Changes:** None

**Backward Compatibility:**
- All existing endpoints unchanged
- All response formats unchanged
- All error handling unchanged

**Configuration Migration:**
- Old `OPENAI_API_KEY` still supported (for backward compatibility)
- New `OPENROUTER_API_KEY` takes precedence
- Default model changed from `gpt-4o` to `openai/gpt-4o-mini`

## Future Enhancements

1. **Per-Endpoint Model Override:** Allow different models per endpoint
2. **Token Usage Storage:** Store token usage for billing/analytics
3. **Model Performance Tracking:** Track accuracy per model
4. **Cost Optimization:** Auto-select models based on cost/quality tradeoff
5. **Response Caching:** Cache common queries to reduce API calls

## Support

For issues or questions:
- Check OpenRouter documentation: https://openrouter.ai/docs
- Review logs for token usage and errors
- Verify API key and configuration
- Test with fallback behavior disabled

