# Exports Module Documentation

## Overview

The Exports module provides data export functionality for invoices and invoice logs (audit trail) in multiple formats. All exports are tenant-scoped, streaming-enabled, and designed for ZATCA compliance and audit requirements.

## Features

- **Multiple Formats**: CSV (mandatory), JSON (mandatory), XML (optional, future-ready)
- **Streaming Support**: Efficient handling of large datasets without loading all data into memory
- **Tenant Isolation**: All exports automatically filter by authenticated tenant
- **Comprehensive Filtering**: Date ranges, invoice numbers, status, phase, environment
- **Production Access Control**: Production exports require active subscription
- **ZATCA Compliance**: Complete audit trail export for compliance requirements

## API Endpoints

### Export Invoices

```
GET /api/v1/exports/invoices
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `format` | string | No | Export format: `csv` (default) or `json` |
| `date_from` | datetime | No | Filter by start date (ISO format) |
| `date_to` | datetime | No | Filter by end date (ISO format) |
| `invoice_number` | string | No | Filter by invoice number (partial match, case-insensitive) |
| `status` | string | No | Filter by status: `CREATED`, `PROCESSING`, `CLEARED`, `REJECTED`, `FAILED` |
| `phase` | string | No | Filter by phase: `PHASE_1`, `PHASE_2` |
| `environment` | string | No | Filter by environment: `SANDBOX`, `PRODUCTION` |

**Response:**

- **Content-Type**: `text/csv; charset=utf-8` (CSV) or `application/json; charset=utf-8` (JSON)
- **Content-Disposition**: `attachment; filename="invoices_export_YYYYMMDD_HHMMSS.{format}"`
- **Body**: Streaming response with export data

### Export Invoice Logs (Audit Trail)

```
GET /api/v1/exports/invoice-logs
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `format` | string | No | Export format: `csv` (default) or `json` |
| `date_from` | datetime | No | Filter by start date (ISO format) |
| `date_to` | datetime | No | Filter by end date (ISO format) |
| `invoice_number` | string | No | Filter by invoice number (partial match, case-insensitive) |
| `status` | string | No | Filter by log status: `SUBMITTED`, `CLEARED`, `REJECTED`, `ERROR` |
| `environment` | string | No | Filter by environment: `SANDBOX`, `PRODUCTION` |

**Response:**

- **Content-Type**: `text/csv; charset=utf-8` (CSV) or `application/json; charset=utf-8` (JSON)
- **Content-Disposition**: `attachment; filename="invoice_logs_export_YYYYMMDD_HHMMSS.{format}"`
- **Body**: Streaming response with export data

## Authentication

All export endpoints require API key authentication:

```
X-API-Key: your-api-key-here
```

## Usage Examples

### Export All Invoices (CSV)

```bash
curl -X GET "https://api.example.com/api/v1/exports/invoices?format=csv" \
  -H "X-API-Key: your-api-key" \
  -o invoices_export.csv
```

### Export Invoices with Filters (JSON)

```bash
curl -X GET "https://api.example.com/api/v1/exports/invoices?format=json&status=CLEARED&phase=PHASE_2&date_from=2025-01-01T00:00:00Z&date_to=2025-01-31T23:59:59Z" \
  -H "X-API-Key: your-api-key" \
  -o invoices_cleared_phase2_january.json
```

### Export Invoice Logs (Audit Trail)

```bash
curl -X GET "https://api.example.com/api/v1/exports/invoice-logs?format=csv&date_from=2025-01-01T00:00:00Z" \
  -H "X-API-Key: your-api-key" \
  -o invoice_logs_audit_trail.csv
```

### Export Production Invoices (Requires Paid Plan)

```bash
curl -X GET "https://api.example.com/api/v1/exports/invoices?format=csv&environment=PRODUCTION" \
  -H "X-API-Key: your-api-key" \
  -o invoices_production.csv
```

**Note:** Production exports require an active subscription (Starter, Pro, or Enterprise plan). Free/Trial plans are restricted to Sandbox exports only.

## Export Formats

### CSV Format

**Structure:**
- First row contains column headers
- Each subsequent row represents one record
- Fields are comma-separated
- Special characters (quotes, commas, newlines) are properly escaped
- UTF-8 encoding

**Invoice CSV Columns:**
- `id`: Invoice ID
- `invoice_number`: Invoice number
- `phase`: ZATCA phase (PHASE_1 or PHASE_2)
- `status`: Invoice status
- `environment`: Environment (SANDBOX or PRODUCTION)
- `total_amount`: Total amount including tax
- `tax_amount`: Tax amount
- `hash`: XML hash (Phase-2 only)
- `uuid`: Invoice UUID (Phase-2 only)
- `error_message`: Error message (if failed)
- `created_at`: Creation timestamp (ISO format)
- `updated_at`: Last update timestamp (ISO format)

**Invoice Log CSV Columns:**
- `id`: Log ID
- `invoice_number`: Invoice number
- `uuid`: Invoice UUID
- `hash`: XML hash
- `environment`: Environment
- `status`: Log status
- `zatca_response_code`: ZATCA response code or error message
- `action`: Action type (e.g., "RETRY", "SUBMIT")
- `previous_status`: Previous invoice status (for retries)
- `submitted_at`: Submission timestamp (ISO format)
- `cleared_at`: Clearance timestamp (ISO format)
- `created_at`: Creation timestamp (ISO format)

### JSON Format

**Structure:**
- Newline-delimited JSON (NDJSON)
- Each line is a complete JSON object
- UTF-8 encoding
- Suitable for streaming and processing large datasets

**Example:**
```json
{"id":1,"invoice_number":"INV-2024-001","phase":"PHASE_2","status":"CLEARED","environment":"SANDBOX","total_amount":1150.0,"tax_amount":150.0,"hash":"abc123...","uuid":"550e8400-e29b-41d4-a716-446655440000","error_message":null,"created_at":"2025-01-18T10:00:00Z","updated_at":"2025-01-18T10:00:00Z"}
{"id":2,"invoice_number":"INV-2024-002","phase":"PHASE_1","status":"CLEARED","environment":"SANDBOX","total_amount":230.0,"tax_amount":30.0,"hash":null,"uuid":null,"error_message":null,"created_at":"2025-01-18T11:00:00Z","updated_at":"2025-01-18T11:00:00Z"}
```

## Tenant Isolation

**CRITICAL:** All exports automatically filter data by the authenticated tenant's `tenant_id`. This is enforced at the database query level, ensuring:

- Tenants can only export their own invoices and logs
- Cross-tenant data leakage is impossible
- No additional filtering is required in application code

## Production Access Control

**Production exports require active subscription:**

- **Allowed Plans**: Starter, Pro, Enterprise
- **Restricted Plans**: Free Sandbox, Trial

**Behavior:**
- Sandbox exports are always allowed
- Production exports check subscription status
- Returns `403 Forbidden` if production access is denied

## Performance Considerations

### Streaming Architecture

Exports use streaming responses to handle large datasets efficiently:

- **Chunked Processing**: Data is fetched in chunks of 1,000 records
- **Memory Efficient**: Does not load all data into memory
- **Progressive Download**: Client can start processing data as it arrives

### Query Optimization

All export queries:

- Use database indexes (`tenant_id`, `created_at`, `status`, etc.)
- Apply filters at database level (not in Python)
- Use efficient ordering for consistent results
- Support pagination through chunked processing

### Recommended Usage

- **Small Datasets (< 1,000 records)**: Direct download, fast response
- **Large Datasets (> 1,000 records)**: Streaming response, progressive download
- **Very Large Datasets (> 10,000 records)**: Use date filters to limit scope

## ZATCA Compliance

### Audit Trail Requirements

Invoice logs provide complete audit trail for ZATCA compliance:

- **All Processing Events**: Every invoice submission, retry, and status change
- **ZATCA Responses**: Complete ZATCA API responses stored in logs
- **Timestamps**: Precise timestamps for all events
- **Action Tracking**: Retry actions and status transitions

### Export Use Cases

1. **ZATCA Audit Preparation**: Export invoice logs for ZATCA audit submissions
2. **Compliance Reporting**: Generate compliance reports from invoice data
3. **Data Backup**: Regular exports for data backup and archival
4. **Analysis**: Export data for external analysis tools (Excel, BI tools)

## Error Handling

### HTTP Status Codes

- **200 OK**: Export successful
- **400 Bad Request**: Invalid parameters (e.g., invalid format, invalid status)
- **401 Unauthorized**: Missing or invalid API key
- **403 Forbidden**: Production access denied (subscription required)
- **500 Internal Server Error**: Server error during export

### Error Responses

```json
{
  "detail": "Error message describing what went wrong"
}
```

## File Naming Convention

Exports use timestamped filenames:

- **Invoices**: `invoices_export_YYYYMMDD_HHMMSS.{format}`
- **Invoice Logs**: `invoice_logs_export_YYYYMMDD_HHMMSS.{format}`

**Example:**
- `invoices_export_20250118_143022.csv`
- `invoice_logs_export_20250118_143022.json`

## Best Practices

### Filtering

1. **Use Date Filters**: Always use `date_from` and `date_to` for large datasets
2. **Combine Filters**: Use multiple filters to narrow results
3. **Production Data**: Use `environment=PRODUCTION` filter for production-only exports

### Format Selection

1. **CSV**: Best for Excel, spreadsheet tools, simple analysis
2. **JSON**: Best for programmatic processing, data pipelines, APIs

### Performance

1. **Limit Date Ranges**: Export data in monthly or quarterly chunks
2. **Use Specific Filters**: Narrow results with status, phase, or invoice number filters
3. **Schedule Exports**: Use scheduled exports for regular reporting

## Security Considerations

1. **API Key Protection**: Keep API keys secure, rotate regularly
2. **Production Access**: Only grant production access to authorized users
3. **Data Privacy**: Exports contain sensitive financial data - handle with care
4. **Audit Logging**: All export requests are logged for audit purposes

## Limitations

1. **Format Support**: XML format is planned but not yet implemented
2. **Export Size**: No hard limit, but very large exports may take time
3. **Concurrent Exports**: Multiple concurrent exports are supported

## Support

For questions or issues with exports:

1. Check API documentation for parameter details
2. Verify API key and subscription status
3. Review error messages for specific issues
4. Contact support for production access requests

---

**Last Updated**: 2025-01-18  
**Version**: 1.0.0

