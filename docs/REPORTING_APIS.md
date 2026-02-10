# Reporting APIs Documentation

## Overview

The Reporting APIs provide read-only endpoints for invoice and VAT analytics. All reports are tenant-scoped and require authentication via API key.

## Base URL

All reporting endpoints are available under:

```
/api/v1/reports
```

## Authentication

All endpoints require authentication via API key in the `X-API-Key` header:

```
X-API-Key: your-api-key-here
```

## Tenant Isolation

**CRITICAL:** All reports are automatically scoped to the authenticated tenant. Tenants can only see their own data. Cross-tenant access is impossible.

## Endpoints

### 1. Invoice Report

Get paginated invoice report with filtering options.

**Endpoint:** `GET /api/v1/reports/invoices`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1, minimum: 1) |
| `page_size` | integer | No | Items per page (default: 50, maximum: 100) |
| `date_from` | datetime | No | Filter by start date (ISO format) |
| `date_to` | datetime | No | Filter by end date (ISO format) |
| `status` | string | No | Filter by invoice status (CREATED, PROCESSING, CLEARED, REJECTED, FAILED) |
| `phase` | string | No | Filter by invoice phase (PHASE_1, PHASE_2) |

**Example Request:**

```bash
curl -X GET "https://api.example.com/api/v1/reports/invoices?page=1&page_size=50&status=CLEARED" \
  -H "X-API-Key: your-api-key"
```

**Example Response:**

```json
{
  "invoices": [
    {
      "invoice_number": "INV-001",
      "status": "CLEARED",
      "phase": "PHASE_2",
      "total_amount": 1150.0,
      "tax_amount": 150.0,
      "created_at": "2025-01-18T10:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 50,
  "total_pages": 2
}
```

### 2. VAT Summary

Get VAT summary aggregated by day or month.

**Endpoint:** `GET /api/v1/reports/vat-summary`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date_from` | datetime | No | Filter by start date (ISO format) |
| `date_to` | datetime | No | Filter by end date (ISO format) |
| `group_by` | string | No | Aggregation period: "day" (default) or "month" |

**Example Request:**

```bash
curl -X GET "https://api.example.com/api/v1/reports/vat-summary?group_by=month&date_from=2025-01-01T00:00:00Z" \
  -H "X-API-Key: your-api-key"
```

**Example Response:**

```json
{
  "summary": [
    {
      "date": "2025-01",
      "total_tax_amount": 1500.0,
      "total_invoice_amount": 10000.0,
      "invoice_count": 50
    }
  ],
  "total_tax_amount": 1500.0,
  "total_invoice_amount": 10000.0,
  "total_invoice_count": 50,
  "date_from": "2025-01-01T00:00:00Z",
  "date_to": null,
  "group_by": "month"
}
```

### 3. Status Breakdown

Get invoice status breakdown.

**Endpoint:** `GET /api/v1/reports/status-breakdown`

**Example Request:**

```bash
curl -X GET "https://api.example.com/api/v1/reports/status-breakdown" \
  -H "X-API-Key: your-api-key"
```

**Example Response:**

```json
{
  "breakdown": [
    {
      "status": "CLEARED",
      "count": 80
    },
    {
      "status": "REJECTED",
      "count": 10
    },
    {
      "status": "FAILED",
      "count": 5
    },
    {
      "status": "PROCESSING",
      "count": 3
    },
    {
      "status": "CREATED",
      "count": 2
    }
  ],
  "total_invoices": 100
}
```

### 4. Revenue Summary

Get revenue summary for the tenant.

**Endpoint:** `GET /api/v1/reports/revenue-summary`

**Example Request:**

```bash
curl -X GET "https://api.example.com/api/v1/reports/revenue-summary" \
  -H "X-API-Key: your-api-key"
```

**Example Response:**

```json
{
  "total_revenue": 115000.0,
  "total_tax": 15000.0,
  "net_revenue": 100000.0,
  "cleared_invoice_count": 80,
  "total_invoice_count": 100
}
```

## Notes on Tenant Isolation

All reporting endpoints automatically filter data by the authenticated tenant's `tenant_id`. This is enforced at the database query level, ensuring:

- Tenants can only see their own invoices
- Cross-tenant data leakage is impossible
- No additional filtering is required in application code

## Performance Considerations

### Query Optimization

All reporting queries use:

- **Indexes:** Leverage existing database indexes on `tenant_id`, `status`, `created_at`, and composite indexes
- **Aggregation:** Use SQL aggregation functions (SUM, COUNT, GROUP BY) for efficient computation
- **Pagination:** Invoice report uses pagination to limit result sets
- **No N+1 Queries:** All data is fetched in single queries

### Recommended Usage

- **Invoice Report:** Use pagination for large datasets (default page_size: 50)
- **VAT Summary:** Use date filters to limit aggregation scope
- **Status Breakdown:** Fast query, can be called frequently
- **Revenue Summary:** Fast query, uses aggregation

### Caching Considerations

For high-traffic scenarios, consider caching:

- Status breakdown (changes infrequently)
- Revenue summary (can be cached for short periods)
- VAT summary (can be cached per day/month)

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK`: Success
- `400 Bad Request`: Invalid parameters (e.g., invalid `group_by` value)
- `401 Unauthorized`: Missing or invalid API key
- `500 Internal Server Error`: Server error

## Rate Limiting

Reporting endpoints are subject to the same rate limiting as other API endpoints. Check your subscription plan for rate limit details.

## Example Use Cases

### Dashboard Overview

```bash
# Get status breakdown for dashboard
GET /api/v1/reports/status-breakdown

# Get revenue summary for dashboard
GET /api/v1/reports/revenue-summary
```

### Monthly VAT Report

```bash
# Get monthly VAT summary for current month
GET /api/v1/reports/vat-summary?group_by=month&date_from=2025-01-01T00:00:00Z&date_to=2025-01-31T23:59:59Z
```

### Invoice Audit Trail

```bash
# Get all cleared invoices from last 30 days
GET /api/v1/reports/invoices?status=CLEARED&date_from=2024-12-19T00:00:00Z&page_size=100
```

## Implementation Details

### Service Layer

All reporting logic is implemented in `ReportingService` (`backend/app/services/reporting_service.py`):

- Tenant isolation enforced in all queries
- Efficient aggregation queries
- Proper error handling
- Logging for debugging

### Database Queries

Queries use SQLAlchemy ORM with:

- `func.sum()` for aggregations
- `func.count()` for counting
- `func.date()` and `extract()` for date grouping
- Proper filtering by `tenant_id`

### Response Schemas

All responses use Pydantic schemas defined in `backend/app/schemas/reporting.py`:

- Type-safe response models
- Automatic validation
- Clear documentation

## Support

For questions or issues:

1. Review this documentation
2. Check unit tests in `tests/backend/test_reporting.py` for usage examples
3. Review service code in `backend/app/services/reporting_service.py` for implementation details

