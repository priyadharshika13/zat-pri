# AI Governance Statement

## AI Governance Framework

The system implements strict governance controls for AI usage to ensure regulatory compliance and responsible AI practices.

## AI Decision Boundaries

### Compliance Operations

**AI Exclusion:**
- All ZATCA-critical operations are AI-free
- Invoice validation: Rule-based only
- XML generation: Rule-based only
- Cryptographic signing: Rule-based only
- ZATCA API communication: Rule-based only
- VAT calculations: Rule-based only

**Guarantee:**
- AI never modifies invoice data
- AI never generates or alters XML
- AI never calculates VAT
- AI never changes hashes, UUIDs, PIH, or signatures
- AI never submits invoices to ZATCA
- AI never overrides ZATCA validation logic

### Advisory Intelligence

**AI Inclusion:**
- Error explanation: Advisory only
- Rejection prediction: Advisory only
- Pre-check advisor: Advisory only
- Root cause analysis: Advisory only
- Readiness scoring: Advisory only
- Trend analysis: Advisory only

**Guarantee:**
- AI outputs are read-only
- AI outputs are non-blocking
- AI outputs are explainable
- AI outputs are tenant-scoped
- AI outputs are fully optional

## AI Governance Controls

### Global Toggle

**Configuration:**
- `ENABLE_AI_EXPLANATION` environment variable
- Default: `false` (enterprise-safe default)
- Can be disabled without code changes
- All AI services respect global toggle

**Behavior:**
- When `false`: All AI services return disabled responses
- When `true`: AI services function normally
- Graceful fallback when disabled
- No exceptions raised when disabled

### Subscription Limits

**Per-Plan Limits:**
- AI usage limits per subscription plan
- Token usage tracked per tenant
- Limits enforced before AI invocation
- Usage tracked for billing

**Enforcement:**
- Limits checked before AI service calls
- 403 Forbidden on limit exceeded
- Usage tracked per tenant
- Limits reset per billing period

### Data Privacy

**Tenant Isolation:**
- All AI operations are tenant-scoped
- No cross-tenant data access
- Tenant context required for all operations
- Data isolation enforced

**Data Storage:**
- AI services do not store invoice data
- Only usage metrics tracked
- No PII stored in AI systems
- Data sent to OpenRouter for processing only

## Regulatory Compliance

### ZATCA Compliance

**Compliance Guarantee:**
- Final compliance decisions always follow ZATCA rules
- AI never overrides ZATCA decisions
- AI never modifies compliance operations
- All compliance operations are deterministic

**Decision Flow:**
1. Invoice validated using rule-based logic
2. Invoice processed using rule-based logic
3. ZATCA response determines final status
4. AI provides advisory information (optional)

### Audit and Traceability

**AI Usage Logging:**
- AI service calls logged
- Token usage tracked
- No invoice data in AI logs
- Tenant context in all logs

**Compliance Logging:**
- All compliance operations logged
- Full audit trail maintained
- AI operations separate from compliance
- Traceability for regulatory review

## Responsible AI Practices

### Transparency

**Explainability:**
- AI outputs are explainable
- AI recommendations include reasoning
- AI errors are logged and handled
- AI usage is transparent to clients

### Accountability

**Human Oversight:**
- AI outputs are advisory only
- Human decision-making required
- AI cannot make autonomous decisions
- Human review of AI recommendations

### Safety

**Error Handling:**
- AI failures never break compliance flow
- Graceful fallback when AI disabled
- AI errors logged but not exposed
- Compliance operations continue on AI failure

## Current Implementation Status

All AI governance components are implemented:

- Global AI toggle
- Subscription limits
- Data privacy controls
- Regulatory compliance
- Audit and traceability
- Responsible AI practices

Future considerations (not currently implemented):

- Advanced AI governance controls
- AI usage analytics
- AI performance monitoring
- AI bias detection
- AI explainability enhancements
- AI compliance certifications

