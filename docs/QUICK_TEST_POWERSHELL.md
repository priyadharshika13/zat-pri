# Quick Test PowerShell Commands

## Test Invoice API (Phase-2)

### From Project Root Directory

```powershell
# Set headers
$headers = @{
    "X-API-Key" = "test-key"
    "Content-Type" = "application/json"
}

# Read payload from tests/backend directory
$body = Get-Content -Raw -Path "tests\backend\sample_phase2_payload_1.json"

# Submit invoice
Invoke-RestMethod `
    -Uri "http://localhost:8000/api/v1/invoices" `
    -Method POST `
    -Headers $headers `
    -Body $body
```

### From tests/backend Directory

```powershell
# Navigate to tests/backend
cd tests\backend

# Set headers
$headers = @{
    "X-API-Key" = "test-key"
    "Content-Type" = "application/json"
}

# Read payload
$body = Get-Content -Raw -Path ".\sample_phase2_payload_1.json"

# Submit invoice
Invoke-RestMethod `
    -Uri "http://localhost:8000/api/v1/invoices" `
    -Method POST `
    -Headers $headers `
    -Body $body
```

## Test Production Onboarding

```powershell
# Set headers
$headers = @{
    "X-API-Key" = "test-key"
}

# Step 1: Submit onboarding request
$csr = Get-Content -Raw -Path "path\to\csr.pem"
$privateKey = Get-Content -Raw -Path "path\to\private_key.pem"

$formData = @{
    csr = $csr
    private_key = $privateKey
    organization_name = "My Company Ltd"
    vat_number = "123456789012345"
}

Invoke-RestMethod `
    -Uri "http://localhost:8000/api/v1/zatca/production/onboarding/submit" `
    -Method POST `
    -Headers $headers `
    -Form $formData

# Step 2: Validate OTP (if OTP required)
$formData = @{
    csr = $csr
    private_key = $privateKey
    organization_name = "My Company Ltd"
    vat_number = "123456789012345"
    otp = "123456"
    request_id = "req-12345"
}

Invoke-RestMethod `
    -Uri "http://localhost:8000/api/v1/zatca/production/onboarding/submit" `
    -Method POST `
    -Headers $headers `
    -Form $formData
```

## Common Issues

### Issue 1: File Not Found
**Error:** `Cannot find path 'E:\ZATCA_AI_API\sample_phase2_payload_1.json'`

**Solution:** Use the correct path: `tests\backend\sample_phase2_payload_1.json`

### Issue 2: Validation Error
**Error:** `Field 'body': Field required`

**Solution:** The API expects the JSON directly in the request body, not wrapped. Make sure you're using `-Body $body` (not `-Body @{body=$body}`)

### Issue 3: API Key Invalid
**Error:** `401 Unauthorized`

**Solution:** Check that your API key matches what's configured in `.env` file:
- `API_KEYS=test-key` (comma-separated list)

## Quick Test Script

Save this as `test-invoice.ps1`:

```powershell
# Quick Invoice Test Script
param(
    [string]$ApiKey = "test-key",
    [string]$PayloadPath = "tests\backend\sample_phase2_payload_1.json",
    [string]$BaseUrl = "http://localhost:8000"
)

# Check if file exists
if (-not (Test-Path $PayloadPath)) {
    Write-Host "Error: Payload file not found at $PayloadPath" -ForegroundColor Red
    Write-Host "Please check the file path and try again." -ForegroundColor Yellow
    exit 1
}

# Set headers
$headers = @{
    "X-API-Key" = $ApiKey
    "Content-Type" = "application/json"
}

# Read payload
$body = Get-Content -Raw -Path $PayloadPath

Write-Host "Submitting invoice..." -ForegroundColor Cyan
Write-Host "Payload: $PayloadPath" -ForegroundColor Gray
Write-Host "API Key: $ApiKey" -ForegroundColor Gray
Write-Host ""

try {
    $response = Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/invoices" `
        -Method POST `
        -Headers $headers `
        -Body $body
    
    Write-Host "Success!" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "Error occurred:" -ForegroundColor Red
    $_.Exception.Message
    
    if ($_.ErrorDetails.Message) {
        Write-Host "Details:" -ForegroundColor Yellow
        $_.ErrorDetails.Message | ConvertFrom-Json | ConvertTo-Json -Depth 10
    }
}
```

Usage:
```powershell
.\test-invoice.ps1
```
