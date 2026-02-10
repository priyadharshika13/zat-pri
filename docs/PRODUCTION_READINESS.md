# Production Readiness Guide

**ZATCA Compliance API - Production Deployment Checklist**

This document is **mandatory** for production launch. Review all sections before deploying.

---

## Table of Contents

1. [Environment Variables Checklist](#environment-variables-checklist)
2. [Safety Rules Summary](#safety-rules-summary)
3. [Retention Policy](#retention-policy)
4. [Incident Handling Steps](#incident-handling-steps)
5. [Rollback Instructions](#rollback-instructions)
6. [Monitoring Pointers](#monitoring-pointers)

---

## Environment Variables Checklist

### Required for Production

```bash
# Application
ENVIRONMENT_NAME=production
DEBUG=false
ENABLE_DOCS=false  # Disable in production

# API Security
API_KEYS=<comma-separated-list-of-valid-api-keys>

# ZATCA Environment (CRITICAL)
ZATCA_ENV=PRODUCTION  # or SANDBOX for testing
ZATCA_SANDBOX_BASE_URL=https://gw-apic-gov.gazt.gov.sa/e-invoicing/developer-portal
ZATCA_PRODUCTION_BASE_URL=https://gw-apic-gov.gazt.gov.sa/e-invoicing/core
ZATCA_TIMEOUT=30
ZATCA_MAX_RETRIES=3

# Database
DATABASE_URL=<postgresql-connection-string>

# AI Services (Optional)
ENABLE_AI_EXPLANATION=true  # or false to disable globally
OPENROUTER_API_KEY=<openrouter-api-key>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_DEFAULT_MODEL=openai/gpt-4o-mini
OPENROUTER_TIMEOUT=60

# Phase 9: Internal Operations
INTERNAL_SECRET_KEY=<strong-random-secret-key>  # Required for /api/v1/internal/* endpoints

# Phase 9: Data Retention
RETENTION_DAYS=180  # Default: 180 days (6 months)
RETENTION_CLEANUP_MODE=anonymize  # or "purge"
```

### Security Checklist

- [ ] `INTERNAL_SECRET_KEY` is set and strong (min 32 characters)
- [ ] `API_KEYS` contains only valid, active keys
- [ ] `DATABASE_URL` uses SSL/TLS connection
- [ ] `OPENROUTER_API_KEY` is valid (if AI enabled)
- [ ] All secrets are stored in secure vault (not in code)
- [ ] `DEBUG=false` in production
- [ ] `ENABLE_DOCS=false` in production

---

## Safety Rules Summary

### Production Access Control

**CRITICAL**: Only paid plans can submit invoices to Production ZATCA.

- **Allowed Plans**: Starter, Pro, Enterprise
- **Restricted Plans**: Free Sandbox, Trial
- **Enforcement**: Server-side validation in `check_production_access()`

**Error Response**:
```json
{
  "error": "PRODUCTION_ACCESS_DENIED",
  "message": "Production access requires an active paid plan",
  "message_ar": "يتطلب الوصول إلى الإنتاج خطة مدفوعة نشطة",
  "reason": "restricted_plan"
}
```

### Production Confirmation Guard

**CRITICAL**: All Production invoice submissions require explicit confirmation.

- **Requirement**: `confirm_production=true` must be included in request
- **Purpose**: Prevents accidental legal submissions
- **Enforcement**: Server-side validation in `require_production_confirmation()`

**Error Response**:
```json
{
  "error": "PRODUCTION_CONFIRMATION_REQUIRED",
  "message": "Production submissions require explicit confirmation. Include 'confirm_production=true' in your request.",
  "message_ar": "تتطلب عمليات الإرسال إلى الإنتاج تأكيدًا صريحًا. قم بتضمين 'confirm_production=true' في طلبك.",
  "reason": "missing_confirmation"
}
```

### Write Action Restrictions

**CRITICAL**: Write actions are blocked for expired/suspended subscriptions.

- **Blocked Statuses**: EXPIRED, SUSPENDED
- **Allowed Statuses**: ACTIVE, TRIAL
- **Affected Actions**: Create invoice, Upload certificate, Generate API key

**Error Response**:
```json
{
  "error": "WRITE_ACTION_DENIED",
  "message": "Write actions are not allowed for expired subscriptions. Please renew your subscription.",
  "message_ar": "لا يُسمح بالإجراءات الكتابية للاشتراكات المنتهية. يرجى تجديد اشتراكك.",
  "reason": "expired_subscription"
}
```

---

## Retention Policy

### Default Retention Period

- **Artifacts Retained**: 180 days (6 months)
- **Configurable**: Via `RETENTION_DAYS` environment variable
- **Affected Fields**:
  - `request_payload` (JSON)
  - `generated_xml` (TEXT)
  - `zatca_response` (JSON)

### Cleanup Modes

1. **Anonymize** (default): Replaces artifacts with anonymized placeholders
   - `request_payload` → `{"retention_expired": true, "anonymized": true}`
   - `generated_xml` → `"<retention_expired>Anonymized</retention_expired>"`
   - `zatca_response` → `{"retention_expired": true, "anonymized": true}`

2. **Purge**: Removes artifacts completely (sets to NULL)

### Metadata Preserved

**CRITICAL**: Invoice metadata is NEVER deleted:
- Invoice ID
- Invoice number
- Status
- UUID, Hash
- Timestamps (created_at, submitted_at, cleared_at)
- ZATCA response code

### Running Cleanup

**Manual Cleanup** (via internal endpoint):
```bash
curl -X POST "https://api.example.com/api/v1/internal/retention/cleanup" \
  -H "X-Internal-Secret: <INTERNAL_SECRET_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false, "retention_days": 180}'
```

**Automated Cleanup** (recommended):
- Set up cron job or scheduled task
- Run daily/weekly depending on volume
- Use `dry_run=true` first to verify

---

## Incident Handling Steps

### ZATCA Downtime

**Symptoms**:
- 502 Bad Gateway errors
- 504 Gateway Timeout errors
- High failure rate on invoice submissions

**Response**:
1. Check ZATCA status page (if available)
2. Verify network connectivity
3. Review error logs for patterns
4. Enable retry logic (already configured: 3 retries with exponential backoff)
5. Notify customers if extended downtime (> 1 hour)

**Logging**: All ZATCA errors are logged with:
- Tenant ID
- Invoice number
- Error type (timeout, HTTP error, etc.)
- Timestamp

### AI Provider Failures

**Symptoms**:
- AI endpoints returning errors
- Timeout errors from OpenRouter
- Rate limit errors (429)

**Response**:
1. Check OpenRouter status
2. Verify `OPENROUTER_API_KEY` is valid
3. Review rate limits (check subscription limits)
4. AI failures are non-critical - system falls back to rule-based responses
5. Monitor AI usage counters

**Logging**: All AI errors are logged with:
- Tenant ID
- Error type
- Model used
- Timestamp

### Rate Limit Exhaustion

**Symptoms**:
- 429 Too Many Requests errors
- Subscription limit errors

**Response**:
1. Check tenant subscription limits
2. Verify rate limiting middleware is active
3. Review usage counters
4. Advise customer to upgrade plan if needed

**Logging**: Rate limit errors include:
- Tenant ID
- Limit type (INVOICE, AI, RATE_LIMIT)
- Current usage vs limit

### Subscription Limit Exceeded

**Symptoms**:
- 403 Forbidden errors
- "Limit exceeded" messages

**Response**:
1. Verify subscription status
2. Check usage counters
3. Advise customer to upgrade plan
4. Monitor for abuse patterns

---

## Rollback Instructions

### Database Rollback

**If migration fails**:
```bash
# Rollback to previous migration
alembic downgrade -1

# Or rollback to specific revision
alembic downgrade <revision_id>
```

**Phase 8 Migration** (005_extend_invoice_logs_observability):
```bash
# Rollback observability fields
alembic downgrade 004
```

### Code Rollback

1. **Git Rollback**:
   ```bash
   git checkout <previous-commit-hash>
   git push --force origin main  # Only if necessary
   ```

2. **Restart Application**:
   ```bash
   # Stop application
   systemctl stop zatca-api  # or your process manager
   
   # Pull previous code
   git pull
   
   # Restart
   systemctl start zatca-api
   ```

3. **Verify Rollback**:
   - Check application logs
   - Verify API endpoints respond
   - Test critical flows (invoice creation)

### Configuration Rollback

**If environment variables cause issues**:
1. Revert `.env` file to previous version
2. Restart application
3. Verify settings loaded correctly

---

## Monitoring Pointers

### Key Metrics to Monitor

1. **Invoice Processing**:
   - Success rate (CLEARED vs REJECTED)
   - Average processing time
   - ZATCA API response times
   - Error rates by type

2. **System Health**:
   - API response times
   - Database connection pool usage
   - Memory/CPU usage
   - Disk space (for certificate storage)

3. **Subscription & Usage**:
   - Active tenants
   - Plan distribution
   - Usage vs limits
   - Rate limit hits

4. **AI Services**:
   - AI request success rate
   - Token usage
   - Cost per request
   - Provider errors

### Internal Endpoints for Monitoring

**Metrics Endpoint**:
```bash
GET /api/v1/internal/metrics
Headers: X-Internal-Secret: <INTERNAL_SECRET_KEY>
```

**Tenant Summary**:
```bash
GET /api/v1/internal/tenants/summary?limit=100
Headers: X-Internal-Secret: <INTERNAL_SECRET_KEY>
```

### Logging Best Practices

1. **Structured Logging**: All logs use JSON format
2. **Context Fields**: Include tenant_id, invoice_number, error_type
3. **Error Levels**:
   - ERROR: System failures, ZATCA errors
   - WARNING: Rate limits, subscription issues
   - INFO: Normal operations, invoice processing
   - DEBUG: Detailed debugging (disable in production)

4. **Sensitive Data**: Never log:
   - API keys
   - Private keys
   - Full request payloads (use masking)

### Alerting Recommendations

Set up alerts for:
- [ ] ZATCA API error rate > 10%
- [ ] Invoice processing failure rate > 5%
- [ ] Database connection errors
- [ ] High memory/CPU usage (> 80%)
- [ ] Internal endpoint authentication failures
- [ ] Retention cleanup failures

---

## Pre-Launch Checklist

### Security
- [ ] All API keys rotated and secure
- [ ] `INTERNAL_SECRET_KEY` set and strong
- [ ] Database credentials secure
- [ ] SSL/TLS enabled for database
- [ ] CORS configured appropriately
- [ ] Rate limiting enabled
- [ ] Audit logging enabled

### Configuration
- [ ] `ZATCA_ENV` set correctly (PRODUCTION or SANDBOX)
- [ ] `DEBUG=false`
- [ ] `ENABLE_DOCS=false`
- [ ] Retention policy configured
- [ ] All required environment variables set

### Testing
- [ ] Production access guards tested
- [ ] Confirmation guard tested
- [ ] Write action restrictions tested
- [ ] Error handling tested (ZATCA downtime, AI failures)
- [ ] Retention cleanup tested (dry run)
- [ ] Internal endpoints tested

### Monitoring
- [ ] Logging configured
- [ ] Metrics collection set up
- [ ] Alerts configured
- [ ] Health checks configured

### Documentation
- [ ] API documentation updated
- [ ] Runbooks created
- [ ] Incident response procedures documented
- [ ] Team trained on procedures

---

## Support Contacts

- **Technical Issues**: [support@example.com]
- **ZATCA Integration**: [zatca-support@example.com]
- **Emergency**: [on-call-number]

---

## Version History

- **v1.0.0** (2025-01-17): Initial production readiness guide
- **Phase 9**: Production safety guards, retention policy, internal ops

---

**Last Updated**: 2025-01-17  
**Maintained By**: Platform Engineering Team

