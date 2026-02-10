#!/bin/bash
# Test server startup script - minimal config for E2E tests

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
VENV_PATH="$PROJECT_ROOT/.venv"

# Set test-friendly defaults
# PostgreSQL for E2E tests
# DATABASE_URL will be auto-resolved by backend if not set
# Backend will detect docker vs host and use correct hostname
export ENVIRONMENT="${ENVIRONMENT:-sandbox}"
export ENVIRONMENT_NAME="${ENVIRONMENT_NAME:-local}"

# Activate virtual environment if it exists
if [ -d "$VENV_PATH" ] && [ -f "$VENV_PATH/pyvenv.cfg" ]; then
    source "$VENV_PATH/bin/activate"
fi

# Change to backend directory
cd "$SCRIPT_DIR"

# Create database if it doesn't exist
echo "Checking database connection..."
if [ -f "$SCRIPT_DIR/scripts/create_database.py" ]; then
    python "$SCRIPT_DIR/scripts/create_database.py" || echo "Note: Database creation check skipped"
else
    echo "Note: Database creation script not found, skipping"
fi

# Run database migrations
echo "Running database migrations..."
python -m alembic upgrade head || echo "Warning: Migrations may have failed, continuing anyway..."

# Run uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

