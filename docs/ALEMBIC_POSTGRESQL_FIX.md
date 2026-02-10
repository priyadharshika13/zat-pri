# Alembic PostgreSQL Fix

## Root Cause

Alembic was using `os.getenv("DATABASE_URL")` which only reads from actual environment variables, not from `.env` files. When `DATABASE_URL` wasn't set in the shell environment, Alembic fell back to the SQLite URL in `alembic.ini` (`sqlite:///./zatca.db`), causing migrations to run against SQLite while the FastAPI app connected to PostgreSQL.

## Solution

Updated `backend/alembic/env.py` to:
1. Use `get_database_url()` from `app.db.session` which reads from Settings (loads `.env` file)
2. Fail fast if `DATABASE_URL` is not set or points to SQLite
3. Remove all SQLite fallbacks
4. Ensure migrations always use the same database as the application runtime

## Fixed Code

The key changes in `backend/alembic/env.py`:

```python
# Import Settings to read DATABASE_URL from .env file (same as app)
from app.core.config import get_settings
from app.db.session import get_database_url

# CRITICAL: Always use DATABASE_URL from environment/.env (same as app runtime)
try:
    database_url = get_database_url()
    config.attributes["sqlalchemy.url"] = database_url
    
    # Verify it's PostgreSQL, not SQLite
    if database_url.startswith("sqlite"):
        raise ValueError("ERROR: Alembic detected SQLite database URL...")
except Exception as e:
    print(f"ERROR: Failed to get database URL for Alembic: {e}", file=sys.stderr)
    sys.exit(1)
```

## Verification Commands

### 1. Verify DATABASE_URL is set correctly

```bash
# From project root
cd backend
python -c "from app.db.session import get_database_url; print('DATABASE_URL:', get_database_url())"
```

**Expected output:**
```
DATABASE_URL: postgresql+psycopg2://postgres:Krishvi23!@localhost:5432/zatca_ai
```

### 2. Verify Alembic will use PostgreSQL

```bash
cd backend
python -c "from alembic import context; from alembic.config import Config; config = Config('alembic.ini'); exec(open('alembic/env.py').read()); print('Database URL:', config.attributes.get('sqlalchemy.url'))"
```

**Expected output:**
```
Database URL: postgresql+psycopg2://postgres:Krishvi23!@localhost:5432/zatca_ai
```

### 3. Check Alembic current revision (should show PostgreSQL)

```bash
cd backend
alembic current
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

**NOT:**
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.  ❌ WRONG
```

### 4. Run migrations against PostgreSQL

```bash
cd backend
alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade -> 001, create tenants api_keys
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, create invoice_logs
...
```

## Cleanup Commands

### Remove SQLite database files

```bash
# From project root
rm -f zatca.db backend/zatca.db
# Or on Windows:
del zatca.db backend\zatca.db
```

### Verify no SQLite files remain

```bash
find . -name "*.db" -o -name "*.sqlite*"
# Or on Windows PowerShell:
Get-ChildItem -Recurse -Filter "*.db"
```

## Expected Logs/Output

### Correct Alembic Output (PostgreSQL)

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade -> 001, create tenants api_keys
```

### Incorrect Output (SQLite) - Should NOT appear

```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.  ❌
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.  ❌
```

### Error if DATABASE_URL not set

```
ERROR: Failed to get database URL for Alembic: ...
ERROR: DATABASE_URL must be set to a PostgreSQL connection string.
ERROR: Example: postgresql+psycopg2://user:password@localhost:5432/zatca_ai
```

## Testing in Codespaces

1. Ensure `.env` file exists in project root with `DATABASE_URL` set
2. Ensure PostgreSQL container is running: `docker-compose up -d postgres`
3. Run: `cd backend && alembic current`
4. Verify output shows `PostgresqlImpl`, not `SQLiteImpl`

## Production Safety

- ✅ No auto-migration: Migrations must be run manually
- ✅ Fail-fast: Alembic exits with error if DATABASE_URL not set
- ✅ No SQLite fallback: Prevents accidental SQLite usage
- ✅ Same database as app: Uses same `get_database_url()` function

