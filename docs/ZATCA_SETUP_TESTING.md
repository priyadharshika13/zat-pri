# ZATCA Setup Testing Guide

This guide provides manual testing steps for the ZATCA Setup functionality.

## Prerequisites

1. Backend server running on `http://localhost:8000`
2. Frontend server running on `http://localhost:5173`
3. Valid API key (default: `test-key`)

## Backend API Testing

### 1. Test ZATCA Status Endpoint

#### Get Status (No Certificate)
```bash
# Windows PowerShell
$headers = @{ "X-API-Key" = "test-key" }
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/zatca/status" -Headers $headers -UseBasicParsing | ConvertFrom-Json

# Linux/Mac
curl -H "X-API-Key: test-key" http://localhost:8000/api/v1/zatca/status
```

**Expected Response:**
```json
{
  "connected": false,
  "environment": "SANDBOX",
  "certificate": null,
  "certificate_expiry": null,
  "last_sync": null
}
```

#### Get Status with Environment
```bash
curl -H "X-API-Key: test-key" "http://localhost:8000/api/v1/zatca/status?environment=PRODUCTION"
```

### 2. Test CSR Generation

#### Generate CSR with All Fields
```bash
# Windows PowerShell
$headers = @{ "X-API-Key" = "test-key" }
$formData = @{
    environment = "SANDBOX"
    common_name = "test-company.com"
    organization = "Test Company"
    organizational_unit = "IT Department"
    country = "SA"
    state = "Riyadh"
    locality = "Riyadh"
    email = "admin@test-company.com"
}
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/zatca/csr/generate" -Method POST -Headers $headers -Form $formData

# Linux/Mac (using curl)
curl -X POST \
  -H "X-API-Key: test-key" \
  -F "environment=SANDBOX" \
  -F "common_name=test-company.com" \
  -F "organization=Test Company" \
  -F "organizational_unit=IT Department" \
  -F "country=SA" \
  -F "state=Riyadh" \
  -F "locality=Riyadh" \
  -F "email=admin@test-company.com" \
  http://localhost:8000/api/v1/zatca/csr/generate
```

**Expected Response:**
```json
{
  "csr": "-----BEGIN CERTIFICATE REQUEST-----\n...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "subject": "C=SA, ST=Riyadh, L=Riyadh, O=Test Company, OU=IT Department, CN=test-company.com, emailAddress=admin@test-company.com",
  "key_size": 2048,
  "environment": "SANDBOX",
  "common_name": "test-company.com"
}
```

#### Generate CSR with Minimal Fields
```bash
curl -X POST \
  -H "X-API-Key: test-key" \
  -F "environment=SANDBOX" \
  -F "common_name=minimal-test.com" \
  http://localhost:8000/api/v1/zatca/csr/generate
```

### 3. Test CSID Upload

#### Upload Certificate and Private Key
```bash
# Create test certificate and key files first
# Then upload:

curl -X POST \
  -H "X-API-Key: test-key" \
  -F "environment=SANDBOX" \
  -F "certificate=@certificate.pem" \
  -F "private_key=@private_key.pem" \
  http://localhost:8000/api/v1/zatca/csid/upload
```

**Expected Response:**
```json
{
  "success": true,
  "certificate": {
    "id": 1,
    "serial": "...",
    "issuer": "...",
    "expiry_date": "2025-01-01T00:00:00",
    "uploaded_at": "2024-01-15T10:30:00",
    "environment": "SANDBOX",
    "status": "ACTIVE"
  },
  "message": "CSID certificate uploaded successfully"
}
```

#### Verify Status After Upload
```bash
curl -H "X-API-Key: test-key" http://localhost:8000/api/v1/zatca/status
```

**Expected Response (after upload):**
```json
{
  "connected": true,
  "environment": "SANDBOX",
  "certificate": {
    "id": 1,
    "serial": "...",
    "issuer": "...",
    "status": "ACTIVE",
    "is_active": true
  },
  "certificate_expiry": "2025-01-01T00:00:00",
  "last_sync": "2024-01-15T10:30:00"
}
```

## Frontend Testing

### 1. Access ZATCA Setup Page

1. Open browser: `http://localhost:5173`
2. Login with API key: `test-key`
3. Navigate to "ZATCA Setup" from sidebar menu
4. URL should be: `http://localhost:5173/#/zatca-setup`

### 2. Test Status Display

**Expected Behavior:**
- Status badge shows "Disconnected" (red) when no certificate
- Status badge shows "Connected" (green) when certificate uploaded
- Environment selector works (Sandbox/Production)
- Refresh button reloads status
- Certificate expiry and last sync show "N/A" when disconnected

### 3. Test CSR Generation

**Steps:**
1. Fill in CSR form fields:
   - Common Name (required): `test-company.com`
   - Organization: `Test Company`
   - Organizational Unit: `IT Department`
   - Country: `SA`
   - State: `Riyadh`
   - Locality: `Riyadh`
   - Email: `admin@test-company.com`
2. Click "Generate CSR"
3. Wait for generation to complete

**Expected Behavior:**
- Success message appears
- "Download CSR" and "Download Private Key" buttons appear
- Clicking download buttons saves files
- Files are valid PEM format
- "Generate New CSR" button resets form

### 4. Test CSID Upload

**Steps:**
1. Generate CSR and download files (or use existing certificate files)
2. In "Upload CSID Certificate" section:
   - Select certificate file (.pem, .crt, or .cer)
   - Select private key file (.pem or .key)
3. Click "Upload CSID"

**Expected Behavior:**
- Upload succeeds
- Status updates to "Connected"
- Certificate expiry date displays
- Last sync time displays
- File inputs reset

### 5. Test Environment Switching

**Steps:**
1. Select "Sandbox" environment
2. Check status
3. Switch to "Production" environment
4. Check status

**Expected Behavior:**
- Status updates based on selected environment
- Each environment has separate certificate status
- Status badge updates correctly

### 6. Test InvoiceCreate Integration

**Steps:**
1. Navigate to "Create Invoice" page
2. Select "Phase 2" option
3. Check if Phase 2 is disabled when ZATCA is not connected

**Expected Behavior:**
- Phase 2 option is disabled when ZATCA status is disconnected
- Warning message appears: "Phase 2 requires ZATCA connection..."
- Link to ZATCA Setup page works
- When ZATCA is connected, Phase 2 is enabled
- When environment changes, ZATCA status is rechecked

## Automated Testing

### Run Backend Tests

```bash
# From project root
cd backend
pytest tests/backend/test_zatca.py -v
```

### Run All Tests

```bash
# From project root
pytest tests/backend/test_zatca.py tests/backend/test_certificates.py -v
```

### Run with Coverage

```bash
pytest tests/backend/test_zatca.py --cov=app.api.v1.routes.zatca --cov=app.services.zatca_service -v
```

## Test Checklist

### Backend Endpoints
- [ ] GET /api/v1/zatca/status returns correct status when disconnected
- [ ] GET /api/v1/zatca/status returns correct status when connected
- [ ] GET /api/v1/zatca/status with environment parameter works
- [ ] POST /api/v1/zatca/csr/generate with all fields works
- [ ] POST /api/v1/zatca/csr/generate with minimal fields works
- [ ] POST /api/v1/zatca/csr/generate validates environment
- [ ] POST /api/v1/zatca/csr/generate requires common_name
- [ ] POST /api/v1/zatca/csid/upload validates certificate format
- [ ] POST /api/v1/zatca/csid/upload validates private key format
- [ ] POST /api/v1/zatca/csid/upload updates status to connected
- [ ] All endpoints require authentication

### Frontend UI
- [ ] ZATCA Setup page loads correctly
- [ ] Status badge displays correctly (connected/disconnected)
- [ ] Environment selector works
- [ ] CSR generation form works
- [ ] CSR download works
- [ ] CSID upload works
- [ ] Status updates after upload
- [ ] Error messages display correctly
- [ ] Loading states work correctly

### Integration
- [ ] InvoiceCreate disables Phase 2 when ZATCA disconnected
- [ ] InvoiceCreate enables Phase 2 when ZATCA connected
- [ ] Environment change triggers status recheck
- [ ] Navigation to ZATCA Setup works from InvoiceCreate

## Troubleshooting

### Backend Issues

**Error: "cryptography library is required"**
- Install: `pip install cryptography`

**Error: "Invalid certificate format"**
- Ensure certificate is valid PEM format
- Check certificate hasn't expired

**Error: "Certificate and key must match"**
- Ensure private key matches the certificate

### Frontend Issues

**Error: "Failed to load ZATCA status"**
- Check backend is running
- Check API key is valid
- Check browser console for errors

**CSR Generation Fails**
- Check all required fields are filled
- Check backend logs for errors

**Upload Fails**
- Check file formats (.pem, .crt, .cer for cert; .pem, .key for key)
- Check certificate is not expired
- Check certificate and key match

