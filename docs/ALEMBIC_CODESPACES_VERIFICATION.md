# Alembic PostgreSQL Fix - Codespaces Verification

## Issue in Codespaces

In Codespaces, `alembic current` was showing:
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.  ❌
```

This happened because Alembic wasn't reading `DATABASE_URL` from `.env` file.

## Fix Applied

Updated `backend/alembic/env.py` to use `get_database_url()` which:
1. Reads from Settings (loads `.env` file)
2. Uses same database URL resolution as the app
3. Fails fast if SQLite is detected

## Verification Steps for Codespaces

### 1. Pull Latest Changes

```bash
git pull origin main
```

### 2. Verify DATABASE_URL is Set

```bash
cd backend
python -c "from app.db.session import get_database_url; print('DATABASE_URL:', get_database_url())"
```

**Expected output:**
```
DATABASE_URL: postgresql+psycopg2://zatca:zatca123@postgres:5432/zatca_ai
```

### 3. Verify Alembic Uses PostgreSQL

```bash
cd backend
alembic current
```

**Expected output (CORRECT):**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.  ✅
INFO  [alembic.runtime.migration] Will assume transactional DDL.
005 (head)
```

**NOT this (WRONG):**
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.  ❌
```

### 4. Run Migrations (if needed)

```bash
cd backend
alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade -> 001, create tenants api_keys
...
```

### 5. Verify PostgreSQL Container is Running

```bash
docker-compose ps
```

**Expected:**
```
NAME                STATUS
zatca-postgres      Up
```

### 6. Clean Up SQLite Files (if any)

```bash
# Remove SQLite database files
rm -f zatca.db backend/zatca.db

# Verify they're gone
find . -name "*.db" -type f
```

## Troubleshooting

### If Still Showing SQLiteImpl

1. **Check if changes are pulled:**
   ```bash
   git status
   git log --oneline -5
   ```

2. **Clear Python cache:**
   ```bash
   find backend -name "*.pyc" -delete
   find backend -name "__pycache__" -type d -exec rm -rf {} +
   ```

3. **Verify .env file exists:**
   ```bash
   cat .env | grep DATABASE_URL
   ```

4. **Check DATABASE_URL format:**
   ```bash
   cd backend
   python -c "from app.db.session import get_database_url; url = get_database_url(); print('URL:', url); print('Is PostgreSQL:', url.startswith('postgresql'))"
   ```

### If DATABASE_URL Not Found

1. **Check .env file location:**
   ```bash
   ls -la .env
   ```

2. **Verify Settings can read it:**
   ```bash
   cd backend
   python -c "from app.core.config import Settings; s = Settings(); print('database_url:', s.database_url)"
   ```

3. **Check PostgreSQL hostname:**
   - In Codespaces with docker-compose: Use `postgres` (service name)
   - The auto-detection should handle this via `get_database_url()`

## Expected Behavior

After the fix:
- ✅ Alembic always uses PostgreSQL (same as app)
- ✅ No SQLite fallback
- ✅ Fails fast if DATABASE_URL not set
- ✅ Works in Codespaces and local dev
- ✅ Same database URL resolution as application

