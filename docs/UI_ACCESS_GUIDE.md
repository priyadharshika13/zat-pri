# How to Access the UI

## Quick Start

### 1. Start the Backend Server

**From the project root:**

```bash
# Windows
cd backend
python run_dev.py

# Or use the batch file
cd backend
run_dev.bat

# Linux/Mac
cd backend
bash run_dev.sh
```

**Backend will run on:** `http://localhost:8000`

**Verify backend is running:**
```bash
curl http://localhost:8000/api/v1/system/health
```

---

### 2. Start the Frontend Server

**Open a NEW terminal window/tab:**

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

**Frontend will run on:** `https://zat-pri.vercel.app/`

---

### 3. Access the UI in Your Browser

Open your browser and navigate to:

```
https://zat-pri.vercel.app/
```

---

## Available Pages & Routes

### Public Pages (No Login Required)

| Route | Description |
|-------|-------------|
| `/login` | Login page (API key authentication) |
| `/plans` | View subscription plans |

### Protected Pages (Requires Authentication)

| Route | Description |
|-------|-------------|
| `/dashboard` | Main dashboard with stats and overview |
| `/invoices` | List all invoices with pagination |
| `/invoices/create` | Create new invoice (full form UI) |
| `/invoices/:invoiceId` | View invoice details (Summary, XML, Response, etc.) |
| `/api-playground` | Interactive API testing tool |
| `/billing` | Subscription and usage information |
| `/ai-insights` | AI insights (coming soon) |

**Default redirect:** `/` → `/dashboard`

---

## First Time Setup

### 1. Login

1. Navigate to `https://zat-pri.vercel.app/`
2. You'll be redirected to `/login` if not authenticated
3. Enter your API key (stored in `localStorage`)
4. Click "Login"

**Default test API key:** `test-key` (if using test data)

### 2. Explore the Dashboard

After login, you'll see:
- **Dashboard** (`/dashboard`) - Overview with stats
- **Invoices** (`/invoices`) - Invoice list (may be empty initially)
- **API Playground** (`/api-playground`) - Test API endpoints
- **Billing** (`/billing`) - Subscription details

---

## Troubleshooting

### Frontend Not Loading

**Check if frontend server is running:**
```bash
# Should show Vite dev server output
cd frontend
npm run dev
```

**Expected output:**
```
  VITE v5.0.8  ready in 500 ms

  ➜  Local:   https://zat-pri.vercel.app//
  ➜  Network: use --host to expose
```

### Backend Not Responding

**Check if backend server is running:**
```bash
# Should show FastAPI/uvicorn output
cd backend
python run_dev.py
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Test backend health:**
```bash
curl http://localhost:8000/api/v1/system/health
```

### Port Already in Use

If port 5173 is already in use:

1. **Kill the process using the port:**
   ```bash
   # Windows
   netstat -ano | findstr :5173
   taskkill /PID <PID> /F
   
   # Linux/Mac
   lsof -ti:5173 | xargs kill -9
   ```

2. **Or change the port in `frontend/vite.config.ts`:**
   ```typescript
   server: {
     port: 5174, // Change to different port
   }
   ```

### CORS Errors

The frontend is configured to proxy API requests to the backend. If you see CORS errors:

1. Ensure backend is running on `http://localhost:8000`
2. Check `frontend/vite.config.ts` has the proxy configuration:
   ```typescript
   proxy: {
     '/api': {
       target: 'http://localhost:8000',
       changeOrigin: true,
     },
   }
   ```

### Authentication Issues

**If you can't login:**

1. Check browser console (F12) for errors
2. Verify API key is correct
3. Ensure backend is running and accessible
4. Check `localStorage` in browser DevTools:
   - Key: `apiKey`
   - Should contain your API key

**Clear authentication:**
```javascript
// In browser console (F12)
localStorage.removeItem('apiKey')
// Then refresh the page
```

---

## Development Workflow

### Typical Development Session

1. **Terminal 1 - Backend:**
   ```bash
   cd backend
   python run_dev.py
   ```

2. **Terminal 2 - Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Browser:**
   - Open `https://zat-pri.vercel.app/`
   - Make changes to frontend code
   - See hot-reload updates automatically

### Hot Reload

- **Frontend:** Changes to React components auto-reload
- **Backend:** Changes to Python code auto-reload (with `--reload` flag)

---

## Production Build

To build for production:

```bash
cd frontend
npm run build
```

Output will be in `frontend/dist/`

Preview production build:
```bash
npm run preview
```

---

## Port Summary

| Service | Port | URL |
|---------|------|-----|
| **Frontend (Dev)** | 5173 | `https://zat-pri.vercel.app/` |
| **Backend (API)** | 8000 | `http://localhost:8000` |
| **Backend Health** | 8000 | `http://localhost:8000/api/v1/system/health` |

---

## Quick Reference Commands

```bash
# Start backend
cd backend && python run_dev.py

# Start frontend (new terminal)
cd frontend && npm run dev

# Check backend health
curl http://localhost:8000/api/v1/system/health

# Open in browser
# https://zat-pri.vercel.app/
```

---

## Need Help?

- Check browser console (F12) for errors
- Check backend terminal for API errors
- Verify both servers are running
- Ensure database is configured (if needed)
- Review `README.md` for full setup instructions

