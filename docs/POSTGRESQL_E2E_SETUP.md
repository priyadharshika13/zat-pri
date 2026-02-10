# PostgreSQL Setup for E2E Tests

## Quick Setup

The E2E test scripts now use PostgreSQL by default. Follow these steps to set up:

### 1. Install PostgreSQL (if not already installed)

**Linux (Codespaces/Ubuntu):**
```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
sudo service postgresql start
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Windows:**
Download and install from [PostgreSQL Downloads](https://www.postgresql.org/download/windows/)

### 2. Create Database

```bash
# Create database
createdb zatca_ai

# Or using psql
psql -U postgres -c "CREATE DATABASE zatca_ai;"
```

### 3. Verify Connection

The default connection string is:
```
postgresql+psycopg2://postgres:postgres@localhost:5432/zatca_ai
```

**If your PostgreSQL credentials are different**, set `DATABASE_URL` before running tests:

```bash
export DATABASE_URL="postgresql+psycopg2://your_user:your_password@localhost:5432/zatca_ai"
```

### 4. Run Migrations

```bash
cd backend
alembic upgrade head
```

### 5. Run E2E Tests

```bash
cd frontend
npm run test:e2e
```

## Default Configuration

The test scripts use these defaults (can be overridden via environment variables):

- **Database:** `zatca_ai`
- **User:** `postgres`
- **Password:** `postgres`
- **Host:** `localhost`
- **Port:** `5432`

## Customizing Connection

You can override the default by setting `DATABASE_URL`:

```bash
# Linux/Mac
export DATABASE_URL="postgresql+psycopg2://user:password@host:5432/database"

# Windows PowerShell
$env:DATABASE_URL="postgresql+psycopg2://user:password@host:5432/database"

# Windows CMD
set DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database
```

## Troubleshooting

### "Database does not exist"
```bash
createdb zatca_ai
```

### "Connection refused"
Make sure PostgreSQL is running:
```bash
# Linux
sudo service postgresql status
sudo service postgresql start

# macOS
brew services list
brew services start postgresql
```

### "Authentication failed"
Check your PostgreSQL credentials and update `DATABASE_URL` accordingly.

### "psycopg2 not found"
Install PostgreSQL driver:
```bash
cd backend
pip install psycopg2-binary
```

## Benefits of PostgreSQL for E2E Tests

✅ **Consistency** - Same database as production/dev  
✅ **Real-world testing** - Tests against actual database behavior  
✅ **Better isolation** - Can use separate test database  
✅ **Advanced features** - JSON, enums, transactions work correctly  

