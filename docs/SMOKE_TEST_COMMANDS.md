# Smoke Test Verification Commands

Quick reference for checking application status and running smoke tests.

---

## 1. Check Backend Status

### Check if backend is running
```bash
# Windows PowerShell
curl http://localhost:8000/api/v1/system/health

# Or using Invoke-WebRequest
Invoke-WebRequest -Uri http://localhost:8000/api/v1/system/health -UseBasicParsing

# Linux/Mac
curl http://localhost:8000/api/v1/system/health
```

### Check backend authentication
```bash
# Windows PowerShell
$headers = @{ "X-API-Key" = "test-key" }
Invoke-WebRequest -Uri http://localhost:8000/api/v1/tenants/me -Headers $headers -UseBasicParsing

# Linux/Mac
curl -H "X-API-Key: test-key" http://localhost:8000/api/v1/tenants/me
```

---

## 2. Check Frontend Status

### Check if frontend is running
```bash
# Windows PowerShell
Invoke-WebRequest -Uri http://localhost:5173 -UseBasicParsing

# Linux/Mac
curl http://localhost:5173
```

---

## 3. Start Services

### Start Backend
```bash
# From project root
cd backend

# Windows
run_test_server.bat

# Linux/Mac
bash run_test_server.sh

# Or directly with uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Start Frontend
```bash
# From project root
cd frontend
npm run dev
```

---

## 4. Run Playwright Smoke Test

### Run smoke test
```bash
# From frontend directory
cd frontend
npx playwright test smoke-test.spec.ts --reporter=list
```

### Run with UI mode (interactive)
```bash
cd frontend
npx playwright test smoke-test.spec.ts --ui
```

### Run in headed mode (see browser)
```bash
cd frontend
npx playwright test smoke-test.spec.ts --headed
```

### Run all E2E tests
```bash
cd frontend
npx playwright test
```

---

## 5. Manual Browser Verification

### Quick Checklist
1. Open browser: `http://localhost:5173`
2. Open Developer Console (F12)
3. Check Console tab for errors
4. Navigate to:
   - `/dashboard`
   - `/invoices`
   - `/api-playground`
   - `/billing`
5. Verify:
   - No blank screens
   - No infinite loaders
   - No console errors
   - Pages load correctly

### Set API Key in Browser Console
```javascript
// In browser console (F12)
localStorage.setItem('api_key', 'test-key');
location.reload();
```

---

## 6. Database Check

### Check if database is accessible
```bash
# From backend directory
cd backend
python -c "from app.db.session import SessionLocal; db = SessionLocal(); print('Database connected'); db.close()"
```

### Check if test-key exists
```bash
# From backend directory
cd backend
python -c "from app.db.session import SessionLocal; from app.models.api_key import ApiKey; db = SessionLocal(); key = db.query(ApiKey).filter(ApiKey.api_key == 'test-key').first(); print('test-key exists:', key is not None); db.close()"
```

---

## 7. One-Line Health Check

### Windows PowerShell
```powershell
# Check backend
$backend = try { (Invoke-WebRequest -Uri http://localhost:8000/api/v1/system/health -UseBasicParsing).StatusCode } catch { "Not running" }; Write-Host "Backend: $backend"

# Check frontend
$frontend = try { (Invoke-WebRequest -Uri http://localhost:5173 -UseBasicParsing).StatusCode } catch { "Not running" }; Write-Host "Frontend: $frontend"
```

### Linux/Mac
```bash
# Check backend
echo "Backend: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/system/health || echo 'Not running')"

# Check frontend
echo "Frontend: $(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173 || echo 'Not running')"
```

---

## 8. Full Smoke Test Sequence

### Complete verification script (Windows PowerShell)
```powershell
# Check backend
Write-Host "Checking backend..." -ForegroundColor Yellow
$backendHealth = try {
    $response = Invoke-WebRequest -Uri http://localhost:8000/api/v1/system/health -UseBasicParsing
    Write-Host "✅ Backend is running (Status: $($response.StatusCode))" -ForegroundColor Green
    $true
} catch {
    Write-Host "❌ Backend is not running" -ForegroundColor Red
    $false
}

# Check backend authentication
if ($backendHealth) {
    Write-Host "Checking backend authentication..." -ForegroundColor Yellow
    try {
        $headers = @{ "X-API-Key" = "test-key" }
        $response = Invoke-WebRequest -Uri http://localhost:8000/api/v1/tenants/me -Headers $headers -UseBasicParsing
        Write-Host "✅ Backend authentication works" -ForegroundColor Green
    } catch {
        Write-Host "❌ Backend authentication failed" -ForegroundColor Red
    }
}

# Check frontend
Write-Host "Checking frontend..." -ForegroundColor Yellow
$frontendHealth = try {
    $response = Invoke-WebRequest -Uri http://localhost:5173 -UseBasicParsing
    Write-Host "✅ Frontend is running (Status: $($response.StatusCode))" -ForegroundColor Green
    $true
} catch {
    Write-Host "❌ Frontend is not running" -ForegroundColor Red
    $false
}

# Summary
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
if ($backendHealth -and $frontendHealth) {
    Write-Host "✅ Application is ready for testing" -ForegroundColor Green
} else {
    Write-Host "❌ Application is not ready. Please start missing services." -ForegroundColor Red
}
```

### Complete verification script (Linux/Mac)
```bash
#!/bin/bash

# Check backend
echo "Checking backend..."
if curl -s -f http://localhost:8000/api/v1/system/health > /dev/null; then
    echo "✅ Backend is running"
    
    # Check authentication
    echo "Checking backend authentication..."
    if curl -s -f -H "X-API-Key: test-key" http://localhost:8000/api/v1/tenants/me > /dev/null; then
        echo "✅ Backend authentication works"
    else
        echo "❌ Backend authentication failed"
    fi
else
    echo "❌ Backend is not running"
fi

# Check frontend
echo "Checking frontend..."
if curl -s -f http://localhost:5173 > /dev/null; then
    echo "✅ Frontend is running"
else
    echo "❌ Frontend is not running"
fi
```

---

## 9. Quick Test Commands

### Test specific endpoint
```bash
# Test invoice list (should work with empty DB)
curl -H "X-API-Key: test-key" http://localhost:8000/api/v1/invoices

# Test tenant info
curl -H "X-API-Key: test-key" http://localhost:8000/api/v1/tenants/me

# Test health
curl http://localhost:8000/api/v1/system/health
```

---

## 10. Troubleshooting Commands

### Check if ports are in use
```bash
# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# Linux/Mac
lsof -i :8000
lsof -i :5173
```

### Check Playwright installation
```bash
cd frontend
npx playwright --version
npx playwright install
```

### Check Node/npm
```bash
node --version
npm --version
```

### Check Python/uvicorn
```bash
python --version
python -m uvicorn --version
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start backend | `cd backend && run_test_server.bat` (Windows) or `bash run_test_server.sh` (Linux/Mac) |
| Start frontend | `cd frontend && npm run dev` |
| Check backend | `curl http://localhost:8000/api/v1/system/health` |
| Check frontend | `curl http://localhost:5173` |
| Run smoke test | `cd frontend && npx playwright test smoke-test.spec.ts` |
| Test auth | `curl -H "X-API-Key: test-key" http://localhost:8000/api/v1/tenants/me` |

---

**Note:** All commands assume you're in the project root directory unless otherwise specified.

