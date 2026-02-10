# Quick Alembic PostgreSQL Verification

## After Pulling Latest Changes

Run these commands in Codespaces to verify Alembic is using PostgreSQL:

### 1. Clear Python Cache (if needed)
```bash
cd backend
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
```

### 2. Verify DATABASE_URL
```bash
cd backend
python -c "from app.db.session import get_database_url; print('DATABASE_URL:', get_database_url())"
```

**Expected:** `DATABASE_URL: postgresql+psycopg2://zatca:zatca123@postgres:5432/zatca_ai`

### 3. Check Alembic Current (MUST show PostgresqlImpl)
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

**❌ WRONG Output (if you see this, the fix didn't work):**
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
```

### 4. Run Migrations (if needed)
```bash
cd backend
alembic upgrade head
```

**Expected:** Should show `PostgresqlImpl` and run migrations against PostgreSQL.

### 5. Verify PostgreSQL Container
```bash
docker-compose ps
```

**Expected:** PostgreSQL container should be running.

## Troubleshooting

If still showing `SQLiteImpl`:

1. **Check if .env exists in project root:**
   ```bash
   cat .env | grep DATABASE_URL
   ```

2. **Verify Settings can read it:**
   ```bash
   cd backend
   python -c "from app.core.config import Settings; s = Settings(); print('database_url:', s.database_url)"
   ```

3. **Check if changes were actually pulled:**
   ```bash
   git log --oneline -3
   ```
   Should show commit `650a2fc` with "Force Alembic to use PostgreSQL"

4. **Restart terminal/reload Python:**
   - Close and reopen terminal
   - Or run: `exec bash`

