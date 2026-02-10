@echo off
REM Test server startup script for Windows - minimal config for E2E tests

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%~dp0..
set VENV_PATH=%PROJECT_ROOT%\.venv

REM Set test-friendly defaults
REM PostgreSQL for E2E tests
REM DATABASE_URL will be auto-resolved by backend if not set
REM Backend will detect docker vs host and use correct hostname
if not defined ENVIRONMENT set ENVIRONMENT=sandbox
if not defined ENVIRONMENT_NAME set ENVIRONMENT_NAME=local

REM Activate virtual environment if it exists
if exist "%VENV_PATH%\Scripts\activate.bat" (
    call "%VENV_PATH%\Scripts\activate.bat"
)

REM Change to backend directory
cd /d "%SCRIPT_DIR%"

REM Create database if it doesn't exist (Windows - requires psql or Python script)
REM Note: On Windows, database creation is typically done manually or via migration
REM This step is primarily for Linux/docker environments

REM Run database migrations
echo Running database migrations...
python -m alembic upgrade head || echo Warning: Migrations may have failed, continuing anyway...

REM Run uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

