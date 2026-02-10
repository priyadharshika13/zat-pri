# PowerShell script to test Phase-2 invoice endpoint
# Usage: .\test_phase2_invoice.ps1

$headers = @{
    "X-API-Key" = "test-key"
    "Content-Type" = "application/json"
}

# Method 1: Using Invoke-RestMethod (RECOMMENDED for PowerShell)
Write-Host "`n=== Method 1: Invoke-RestMethod (Recommended) ===" -ForegroundColor Green
$body = Get-Content -Raw -Path ".\sample_phase2_payload.json"

try {
    $response = Invoke-RestMethod `
        -Uri "http://localhost:8000/api/v1/invoices" `
        -Method POST `
        -Headers $headers `
        -Body $body
    
    Write-Host "✅ Success!" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
}

# Method 2: Using curl.exe with proper PowerShell escaping
Write-Host "`n=== Method 2: curl.exe (Alternative) ===" -ForegroundColor Cyan
$jsonContent = Get-Content -Raw -Path ".\sample_phase2_payload.json"

try {
    # Use -d with properly escaped JSON content
    $response = curl.exe -X POST "http://localhost:8000/api/v1/invoices" `
        -H "X-API-Key: test-key" `
        -H "Content-Type: application/json" `
        -d $jsonContent
    
    Write-Host "✅ Response received" -ForegroundColor Green
    $response
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Method 3: Using curl.exe with temporary file (Most reliable for curl)
Write-Host "`n=== Method 3: curl.exe with --data-binary (Single line) ===" -ForegroundColor Cyan
try {
    # Single line - no backslash continuation needed
    $response = curl.exe -X POST "http://localhost:8000/api/v1/invoices" -H "X-API-Key: test-key" -H "Content-Type: application/json" --data-binary "@sample_phase2_payload.json"
    
    Write-Host "✅ Response received" -ForegroundColor Green
    $response
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Testing Complete ===" -ForegroundColor Green

