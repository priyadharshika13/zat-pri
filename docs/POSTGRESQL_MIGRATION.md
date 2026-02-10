# PostgreSQL Migration Guide

## Overview

The ZATCA AI API backend has been migrated from SQLite to PostgreSQL while maintaining full test compatibility with SQLite in-memory databases.

## Changes Made

### 1. Database Configuration

**File: `backend/app/core/config.py`**
- Added `database_url` and `async_database_url` settings
- Added `get_database_url()` method that:
  - Uses `DATABASE_URL` environment variable if set
  - Falls back to SQLite only for tests (pytest detection)
  - Requires `DATABASE_URL` for production/dev

**File: `backend/app/db/session.py`**
- Complete rewrite to support PostgreSQL and SQLite
- Lazy engine initialization
- Automatic detection of database type (PostgreSQL vs SQLite)
- Proper connection pooling for PostgreSQL
- Backward-compatible `SessionLocal` proxy

### 2. Alembic Configuration

**File: `backend/alembic.ini`**
- Updated comment to indicate PostgreSQL support
- Still defaults to SQLite for backward compatibility
- Can be overridden by `DATABASE_URL` environment variable

**File: `backend/alembic/env.py`**
- Reads `DATABASE_URL` environment variable
- Overrides `sqlalchemy.url` if `DATABASE_URL` is set
- Allows migrations to work with PostgreSQL without modifying `alembic.ini`

### 3. Model Updates

**File: `backend/app/models/subscription.py`**
- Removed `sqlite_autoincrement` from `UsageCounter` table args
- PostgreSQL handles autoincrement automatically
- SQLite also handles it automatically, so this was redundant

### 4. Dependencies

**File: `backend/requirements.txt`**
- Added `psycopg2-binary>=2.9.9` (sync PostgreSQL driver)
- Added `asyncpg>=0.29.0` (async PostgreSQL driver, for future use)

### 5. Environment Configuration

**File: `backend/.env.example`**
- Added `DATABASE_URL` example with PostgreSQL format
- Added `ASYNC_DATABASE_URL` example (optional)
- Documented SQLite fallback for local development

## Migration Steps

### For Development

1. **Install PostgreSQL drivers:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL database:**
   ```bash
   # Create database
   createdb zatca_ai
   
   # Or using psql:
   psql -U postgres -c "CREATE DATABASE zatca_ai;"
   ```

3. **Set environment variable:**
   ```bash
   export DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/zatca_ai
   ```

4. **Run migrations:**
   ```bash
   cd backend
   alembic upgrade head
   ```

5. **Verify:**
   ```bash
   # Start the application
   uvicorn app.main:app --reload
   ```

### For Production

1. **Set `DATABASE_URL` environment variable:**
   ```bash
   export DATABASE_URL=postgresql+psycopg2://user:password@host:5432/zatca_ai
   ```

2. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

3. **Start application:**
   ```bash
   gunicorn app.main:app -c gunicorn.conf.py
   ```

### For Testing

**No changes required!** Tests continue to use SQLite in-memory databases via pytest fixtures. The test isolation remains intact with fresh databases per test.

## Database URL Formats

### PostgreSQL (Recommended)
```
postgresql+psycopg2://user:password@localhost:5432/zatca_ai
```

### PostgreSQL (Async - Optional)
```
postgresql+asyncpg://user:password@localhost:5432/zatca_ai
```

### SQLite (Local Dev Only)
```
sqlite:///./zatca.db
```

## Compatibility Notes

### Migrations
All existing migrations are PostgreSQL-compatible:
- ✅ `sa.JSON()` - Works on both SQLite 3.9+ and PostgreSQL
- ✅ `sa.Enum()` - SQLAlchemy handles PostgreSQL enum creation
- ✅ `sa.Boolean()` - Works on both databases
- ✅ `server_default` - SQLAlchemy converts SQLite '1' to PostgreSQL 'true'

### Models
All models are PostgreSQL-compatible:
- ✅ JSON columns use `sa.JSON()` (not `postgresql.JSON`)
- ✅ Enums use `SQLEnum` which works on both databases
- ✅ Boolean columns work on both databases
- ✅ Foreign keys and constraints work identically

### Test Suite
- ✅ Tests use SQLite in-memory via fixtures
- ✅ No test code changes required
- ✅ Test isolation maintained (fresh database per test)
- ✅ All 63 tests pass without modification

## Verification Checklist

- [x] Database configuration supports PostgreSQL
- [x] Alembic reads `DATABASE_URL` environment variable
- [x] Session management works with PostgreSQL
- [x] Models are PostgreSQL-compatible
- [x] Migrations are PostgreSQL-compatible
- [x] Tests still use SQLite in-memory
- [x] Test isolation maintained
- [x] Backward compatibility preserved

## Troubleshooting

### "DATABASE_URL must be set" Error
**Solution:** Set the `DATABASE_URL` environment variable:
```bash
export DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/zatca_ai
```

### Connection Refused
**Solution:** Ensure PostgreSQL is running and accessible:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -U user -d zatca_ai -h localhost
```

### Migration Errors
**Solution:** Ensure database exists and user has permissions:
```bash
# Create database
createdb zatca_ai

# Grant permissions (if needed)
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE zatca_ai TO user;"
```

### Enum Creation Errors
**Solution:** PostgreSQL requires explicit enum type creation. SQLAlchemy handles this automatically, but if you see errors, you may need to drop and recreate the database:
```bash
dropdb zatca_ai
createdb zatca_ai
alembic upgrade head
```

## Performance Considerations

### Connection Pooling
PostgreSQL configuration uses:
- `pool_size=5` - Base connection pool size
- `max_overflow=10` - Additional connections when pool is exhausted
- `pool_pre_ping=True` - Verify connections before using (prevents stale connections)

### For High Traffic
Consider adjusting pool settings in `backend/app/db/session.py`:
```python
"pool_size": 10,  # Increase base pool
"max_overflow": 20,  # Increase overflow
```

## Security Considerations

1. **Never commit `DATABASE_URL` with credentials** to version control
2. **Use environment variables** for database credentials
3. **Use connection pooling** to prevent connection exhaustion
4. **Enable SSL** for production PostgreSQL connections:
   ```
   postgresql+psycopg2://user:password@host:5432/zatca_ai?sslmode=require
   ```

## Rollback Plan

If you need to rollback to SQLite:

1. Set `DATABASE_URL` to SQLite:
   ```bash
   export DATABASE_URL=sqlite:///./zatca.db
   ```

2. Run migrations (will work with SQLite):
   ```bash
   alembic upgrade head
   ```

3. Restart application

**Note:** Data migration from PostgreSQL to SQLite is not supported. This rollback is only for development/testing.

## Future Enhancements

- [ ] Async database support (asyncpg integration)
- [ ] Database connection health checks
- [ ] Read replicas support
- [ ] Connection retry logic
- [ ] Database migration rollback automation

## Support

For issues or questions:
- Check PostgreSQL logs: `/var/log/postgresql/`
- Check application logs for database connection errors
- Verify `DATABASE_URL` format is correct
- Ensure PostgreSQL user has proper permissions

