# API Key and Rate Limits

## API Key Management

API keys provide authentication and map to tenant contexts for multi-tenant isolation.

## API Key Model

**Database Entity:** `api_keys` table

**Fields:**
- `id`: Primary key
- `api_key`: API key string (hashed in storage)
- `tenant_id`: Foreign key to tenants
- `is_active`: Active status flag
- `last_used_at`: Last usage timestamp
- `created_at`: Creation timestamp

**Relationship:**
- One-to-many: Tenant to API keys
- Each API key belongs to one tenant
- Tenant can have multiple API keys

## API Key Authentication

**Header:** `X-API-Key`

**Validation Process:**
1. API key extracted from header
2. API key looked up in database
3. API key must be active
4. Tenant must be active
5. Tenant context created
6. `last_used_at` updated

**Invalid API Key:**
- 401 Unauthorized response
- Error logged (without exposing key)
- No tenant context created
- Request rejected

## Rate Limiting

### Token Bucket Algorithm

**Implementation:**
- In-memory token buckets per tenant
- Tokens refilled at fixed rate
- Request consumes one token
- Request rejected if no tokens available

**Configuration:**
- Rate limit retrieved from subscription plan
- Default rate limit: 60 requests/minute
- Configurable per plan
- Limits enforced per tenant

### Rate Limit Enforcement

**Middleware:** RateLimitMiddleware

**Process:**
1. Request received
2. Tenant context resolved (from authentication)
3. Rate limit retrieved from subscription
4. Token bucket checked for tenant
5. Token consumed if available
6. 429 Too Many Requests if no tokens

**Response Headers:**
- `X-RateLimit-Limit`: Rate limit per period
- `X-RateLimit-Remaining`: Remaining tokens
- `X-RateLimit-Reset`: Reset timestamp
- `Retry-After`: Seconds until retry allowed

## Subscription Plans and Limits

### Plan Configuration

**Database Entity:** `subscription_plans` table

**Fields:**
- `id`: Primary key
- `name`: Plan name
- `rate_limit`: Requests per minute
- `invoice_limit`: Invoices per month
- `ai_limit`: AI requests per month
- `production_access`: Boolean flag

**Plans:**
- Free: Limited rate, no production access
- Basic: Higher rate, sandbox only
- Professional: Higher rate, production access
- Enterprise: Custom limits, production access

### Limit Enforcement

**Rate Limits:**
- Enforced by RateLimitMiddleware
- Checked before request processing
- 429 response on limit exceeded
- Limits reset per time period

**Invoice Limits:**
- Enforced before invoice creation
- Checked by SubscriptionService
- 403 response on limit exceeded
- Limits tracked per billing period

**AI Limits:**
- Enforced before AI service calls
- Checked by SubscriptionService
- 403 response on limit exceeded
- Token usage tracked per tenant

## Usage Tracking

### Rate Limit Usage

**Tracking:**
- Token consumption per request
- Tokens refilled at fixed intervals
- Usage not persisted (in-memory only)
- Reset on application restart

### Invoice Usage

**Tracking:**
- Invoice count per tenant per month
- Stored in database
- Reset at billing period start
- Used for limit enforcement

### AI Usage

**Tracking:**
- Token usage per tenant
- Stored in database
- Aggregated per billing period
- Used for limit enforcement and billing

## Current Implementation Status

All API key and rate limiting components are implemented:

- API key authentication
- Token bucket rate limiting
- Subscription plan limits
- Usage tracking
- Limit enforcement

Future considerations (not currently implemented):

- API key rotation
- API key expiration
- Shared rate limiting (Redis)
- Advanced rate limiting strategies
- Usage analytics and reporting
- Custom rate limits per API key

