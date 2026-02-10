# API Playground Documentation

## Overview

The API Playground provides an interactive interface for testing ZATCA AI API endpoints. It's designed for developers, ERP teams, and enterprise clients who need to test API integrations before implementing them in production.

## Features

### 1. Interactive API Testing
- Select from available endpoints (Invoices, AI, Plans, Health, System)
- Configure request parameters (body, query params)
- Execute requests using your API key (automatically injected)
- View formatted responses with status codes, headers, and latency

### 2. Request Templates
Pre-filled templates for common operations:
- Phase 1 Invoice (Sandbox)
- Phase 2 Invoice (Sandbox)
- Phase 2 Invoice (Production - requires confirmation)
- AI Readiness Score
- AI Error Explanation
- Usage & Subscription endpoints

### 3. Security & Compliance
- **API Key Auto-injection**: Your API key is automatically attached to requests
- **Subscription Limits**: Enforced for all requests (invoice limits, AI limits)
- **Rate Limits**: Enforced per subscription plan
- **Environment Restrictions**: Production access requires subscription upgrade
- **Production Confirmation**: Write operations to production require explicit checkbox confirmation
- **Sensitive Field Masking**: VAT numbers, certificates, and signatures are masked in responses

### 4. Audit Logging
All playground executions are logged with:
- `source = "api_playground"`
- Request details (endpoint, method, body)
- Response status and latency
- Tenant ID and timestamp

### 5. Developer Tools
- **cURL Command Generation**: Automatically generates curl commands for requests
- **Copy Request/Response**: One-click copy for request and response data
- **JSON Editor**: Syntax-highlighted JSON editor with validation
- **Response Viewer**: Formatted JSON response viewer with status indicators

## Usage

### Accessing the Playground
1. Navigate to `/api-playground` in the web interface
2. Ensure you're logged in (API key is required)

### Using Templates
1. Click "Show Templates" to view available templates
2. Select a template to auto-fill the request
3. Modify the request body/params as needed
4. Click "Execute Request"

### Manual Endpoint Selection
1. Select an endpoint from the dropdown
2. Choose HTTP method (GET, POST, PUT, DELETE)
3. For GET requests: Add query parameters (optional)
4. For POST/PUT/PATCH: Add request body (JSON)
5. For production write operations: Check confirmation checkbox
6. Click "Execute Request"

### Viewing Responses
- Status code with color-coded badges (green=success, red=error, yellow=warning)
- Response latency in milliseconds
- Response headers
- Formatted JSON response body
- Copy button for easy sharing

## Security Rules

### Read Operations
- All read operations (GET) are allowed
- No confirmation required
- Subscription limits still apply (rate limits)

### Write Operations (Sandbox)
- POST/PUT/PATCH/DELETE to sandbox are allowed
- Subscription limits enforced (invoice count, AI request count)
- No confirmation required

### Write Operations (Production)
- **CRITICAL**: Production write operations require:
  1. Active subscription with `production_access` feature
  2. Explicit confirmation checkbox
  3. `confirm_production: true` in request body
- Trial plans are blocked from production writes
- All production writes are logged for audit

## Endpoint Categories

### Invoices
- `POST /api/v1/invoices` - Process invoice (Phase 1 or Phase 2)
- `GET /api/v1/invoices` - List invoices

### AI
- `GET /api/v1/ai/readiness-score` - Get compliance readiness score
- `POST /api/v1/ai/explain-zatca-error` - Get error explanation
- `POST /api/v1/ai/precheck-advisor` - Get pre-check analysis

### Plans & Usage
- `GET /api/v1/plans/current` - Get current subscription
- `GET /api/v1/plans/usage` - Get usage statistics

### System
- `GET /api/v1/health` - Health check

## Request Templates

Templates are dynamically generated based on:
- Tenant subscription plan
- Environment access (sandbox vs production)
- Current tenant context (VAT number, company name)

### Template Structure
```json
{
  "name": "Template Name",
  "description": "What this template does",
  "endpoint": "/api/v1/endpoint",
  "method": "POST",
  "body": { /* request body */ },
  "query_params": { /* query params */ },
  "requires_production_confirmation": false
}
```

## cURL Command Generation

The playground automatically generates curl commands for all requests. This is useful for:
- Testing in terminal
- Integration documentation
- CI/CD pipeline testing
- Debugging

Example generated curl:
```bash
curl -X POST "http://localhost:8000/api/v1/invoices" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"mode": "PHASE_1", ...}'
```

## Error Handling

The playground handles errors gracefully:
- **400 Bad Request**: Invalid request format or missing required fields
- **401 Unauthorized**: Invalid or missing API key
- **403 Forbidden**: 
  - Subscription limit exceeded
  - Production access denied
  - Trial plan attempting production write
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error

All errors are displayed in the response viewer with clear messages.

## Best Practices

1. **Start with Templates**: Use templates to understand request structure
2. **Test in Sandbox First**: Always test in sandbox before production
3. **Check Limits**: Monitor your usage to avoid hitting limits
4. **Review Responses**: Check response structure before implementing
5. **Use cURL for Automation**: Copy curl commands for scripted testing
6. **Respect Production**: Only use production when necessary and confirmed

## Architecture

### Backend
- **Endpoint**: `/api/v1/playground/templates` - Get request templates
- **Endpoint**: `/api/v1/playground/execute` - Execute request (validation only)
- **Actual Execution**: Frontend calls real API endpoints directly

### Frontend
- **Page**: `frontend/src/pages/Playground.tsx`
- **Components**: 
  - `EndpointSelector` - Endpoint selection
  - `TemplateSelector` - Template selection
  - `JsonEditor` - JSON editing
  - `ResponseViewer` - Response display
- **API Client**: `frontend/src/lib/playgroundApi.ts`

## Future Enhancements

- [ ] Request history (save/load previous requests)
- [ ] Response comparison (compare multiple responses)
- [ ] Environment variable substitution
- [ ] Custom headers support
- [ ] Request/response validation against OpenAPI schema
- [ ] Export/import request collections
- [ ] RTL (Arabic) UI support
- [ ] Dark mode support

## Developer Notes

### Adding New Templates
Templates are generated in `backend/app/api/v1/routes/playground.py` in the `get_templates()` function. Add new templates by creating `RequestTemplate` objects.

### Adding New Endpoints
Add endpoints to `frontend/src/components/playground/EndpointSelector.tsx` in the `AVAILABLE_ENDPOINTS` array.

### Customizing Response Masking
Sensitive field masking is handled in `backend/app/utils/data_masking.py`. Modify `mask_sensitive_fields()` to add new fields to mask.

### Audit Logging
Playground executions are logged through the standard audit middleware. All requests include `source="api_playground"` in logs.

## Support

For issues or questions:
- Check API documentation at `/docs` (Swagger UI)
- Review subscription limits in Billing page
- Contact support for production access requests

