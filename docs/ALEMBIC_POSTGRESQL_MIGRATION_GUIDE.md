# Alembic PostgreSQL Migration Guide - Codespaces

## Root Cause

**Problem:** Alembic was using `os.getenv("DATABASE_URL")` which doesn't read `.env` files. When `DATABASE_URL` wasn't set in the shell environment, Alembic fell back to the SQLite URL in `alembic.ini` (`sqlite:///./zatca.db`), causing:

1. Migrations ran against SQLite (created `zatca.db` file)
2. FastAPI app connected to PostgreSQL (from `.env`)
3. Schema mismatch: PostgreSQL had no tables, SQLite had tables
4. Seeding failed: `relation "tenants" does not exist`

**Fix:** Updated `backend/alembic/env.py` to use `get_database_url()` from `app.db.session`, which:
- Reads from Settings (loads `.env` file)
- Uses same database URL resolution as the app
- Fails fast if SQLite is detected
- Ensures migrations and app use the same database

## Fix Steps

### Step 1: Verify Alembic Uses PostgreSQL

```bash
cd backend
alembic current
```

**✅ CORRECT Output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
005 (head)
```

**❌ WRONG Output (if you see this, fix didn't work):**
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
```

### Step 2: Remove SQLite Artifacts

```bash
# From project root
rm -f zatca.db backend/zatca.db

# Verify they're gone
find . -name "*.db" -type f
```

### Step 3: Verify PostgreSQL Connection

```bash
cd backend
python -c "from app.db.session import get_database_url; print('DATABASE_URL:', get_database_url())"
```

**Expected:**
```
DATABASE_URL: postgresql+psycopg2://zatca:zatca123@postgres:5432/zatca_ai
```

### Step 4: Check PostgreSQL Container is Running

```bash
docker-compose ps
```

**Expected:**
```
NAME                STATUS
zatca-postgres      Up
```

### Step 5: Run Migrations Against PostgreSQL

```bash
cd backend
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade -> 001, create tenants api_keys
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, create invoice_logs
INFO  [alembic.runtime.migration] Running upgrade 002 -> 003, create subscription tables
INFO  [alembic.runtime.migration] Running upgrade 003 -> 004, create certificates
INFO  [alembic.runtime.migration] Running upgrade 004 -> 005, extend invoice_logs with observability fields
```

### Step 6: Verify Tables Exist

```bash
cd backend
python -c "
from app.db.session import SessionLocal
from sqlalchemy import inspect
db = SessionLocal()
inspector = inspect(db.bind)
tables = inspector.get_table_names()
print('Tables:', ', '.join(tables))
db.close()
"
```

**Expected:** Should list: `tenants`, `api_keys`, `invoice_logs`, `plans`, `subscriptions`, `usage_counters`, `certificates`

### Step 7: Start FastAPI and Verify Seeding

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Logs (Successful Seeding):**
```
INFO:     Application startup complete.
{"timestamp": "...", "level": "INFO", "logger": "app.services.tenant_seed_service", "message": "Starting tenant seeding for local/dev environment..."}
{"timestamp": "...", "level": "INFO", "logger": "app.services.tenant_seed_service", "message": "Default tenant already exists: Demo Tenant"}
{"timestamp": "...", "level": "INFO", "logger": "app.services.tenant_seed_service", "message": "Test API key 'test-key' already exists"}
{"timestamp": "...", "level": "INFO", "logger": "app.services.tenant_seed_service", "message": "Tenant seeding completed successfully. Tenant: Demo Tenant (ID: 1), API Key: test-key"}
{"timestamp": "...", "level": "INFO", "logger": "app.services.plan_seed_service", "message": "Plans already exist (5). Skipping seed."}
```

**OR (First Run - Creating):**
```
{"timestamp": "...", "level": "INFO", "logger": "app.services.tenant_seed_service", "message": "Created default tenant: Demo Tenant (ID: 1)"}
{"timestamp": "...", "level": "INFO", "logger": "app.services.tenant_seed_service", "message": "Created test API key 'test-key' for tenant 1"}
{"timestamp": "...", "level": "INFO", "logger": "app.services.plan_seed_service", "message": "Created plan: Free Sandbox"}
...
```

**❌ ERROR (if you see this, migrations didn't run):**
```
psycopg2.errors.UndefinedTable: relation "tenants" does not exist
```

## Complete Verification Script

Run this complete verification in Codespaces:

```bash
#!/bin/bash
set -e

echo "=== Step 1: Verify DATABASE_URL ==="
cd backend
python -c "from app.db.session import get_database_url; url = get_database_url(); print('DATABASE_URL:', url); assert url.startswith('postgresql'), 'ERROR: Not PostgreSQL!'"

echo -e "\n=== Step 2: Verify Alembic Uses PostgreSQL ==="
alembic current | grep -q "PostgresqlImpl" && echo "✅ Alembic using PostgreSQL" || (echo "❌ Alembic using SQLite!" && exit 1)

echo -e "\n=== Step 3: Remove SQLite Artifacts ==="
cd ..
rm -f zatca.db backend/zatca.db
echo "✅ SQLite files removed"

echo -e "\n=== Step 4: Run Migrations ==="
cd backend
alembic upgrade head

echo -e "\n=== Step 5: Verify Tables Exist ==="
python -c "
from app.db.session import SessionLocal
from sqlalchemy import inspect
db = SessionLocal()
inspector = inspect(db.bind)
tables = inspector.get_table_names()
required = ['tenants', 'api_keys', 'invoice_logs', 'plans']
missing = [t for t in required if t not in tables]
if missing:
    print(f'❌ Missing tables: {missing}')
    exit(1)
else:
    print(f'✅ All required tables exist: {required}')
db.close()
"

echo -e "\n=== Step 6: Verify Seeding Works ==="
echo "Starting FastAPI server (will show seeding logs)..."
echo "Press Ctrl+C after seeing seeding complete"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Expected Complete Output

### Successful Migration:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade -> 001, create tenants api_keys
INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, create invoice_logs
INFO  [alembic.runtime.migration] Running upgrade 002 -> 003, create subscription tables
INFO  [alembic.runtime.migration] Running upgrade 003 -> 004, create certificates
INFO  [alembic.runtime.migration] Running upgrade 004 -> 005, extend invoice_logs with observability fields
```

### Successful Seeding:
```
{"timestamp": "...", "level": "INFO", "logger": "app.services.tenant_seed_service", "message": "Starting tenant seeding for local/dev environment..."}
{"timestamp": "...", "level": "INFO", "logger": "app.services.tenant_seed_service", "message": "Tenant seeding completed successfully. Tenant: Demo Tenant (ID: 1), API Key: test-key"}
{"timestamp": "...", "level": "INFO", "logger": "app.services.plan_seed_service", "message": "Plan seeding completed successfully."}
INFO:     Application startup complete.
```

## Why This Fix Works

1. **Consistent Database URL:** Both Alembic and FastAPI now use `get_database_url()` which:
   - Reads from Settings (loads `.env` file)
   - Uses same auto-detection logic
   - Ensures same database for migrations and runtime

2. **Fail-Fast Protection:** Alembic now:
   - Exits with error if `DATABASE_URL` not set
   - Rejects SQLite URLs explicitly
   - Prevents accidental SQLite usage

3. **Idempotent Seeding:** Seeding logic:
   - Checks if tenant/API key exists before creating
   - Safe to run multiple times
   - Non-critical (warns but doesn't fail startup)

## Troubleshooting

### If Alembic Still Shows SQLiteImpl

1. **Clear Python cache:**
   ```bash
   find backend -name "*.pyc" -delete
   find backend -name "__pycache__" -type d -exec rm -rf {} +
   ```

2. **Verify changes were pulled:**
   ```bash
   git log --oneline -3
   ```
   Should show commit `650a2fc`

3. **Restart terminal:**
   ```bash
   exec bash
   ```

### If Migrations Fail

1. **Check PostgreSQL is running:**
   ```bash
   docker-compose ps
   docker-compose up -d postgres
   ```

2. **Verify connection:**
   ```bash
   cd backend
   python -c "from app.db.session import SessionLocal; db = SessionLocal(); db.execute('SELECT 1'); print('✅ Connected'); db.close()"
   ```

### If Seeding Still Fails

1. **Check tables exist:**
   ```bash
   cd backend
   python -c "from app.db.session import SessionLocal; from sqlalchemy import inspect; db = SessionLocal(); print('Tables:', inspect(db.bind).get_table_names()); db.close()"
   ```

2. **Check ENVIRONMENT_NAME:**
   ```bash
   cd backend
   python -c "from app.core.config import Settings; s = Settings(); print('ENVIRONMENT_NAME:', s.environment_name)"
   ```
   Should be `local` or `dev` for seeding to run.

