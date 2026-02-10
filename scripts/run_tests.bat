@echo off
REM Test runner script for ZATCA AI API (Windows)

echo Running ZATCA AI API Test Suite
echo ==================================
echo.

REM Change to project root directory
cd /d "%~dp0\.."

REM Check if pytest is available via python -m pytest
python -m pytest --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: pytest is not installed. Installing dependencies...
    pip install -r backend\requirements.txt
)

REM Use python -m pytest for cross-platform compatibility
REM Default: run tests with coverage
if "%1"=="--no-cov" (
    echo Running tests without coverage...
    python -m pytest -v
) else if "%1"=="--html" (
    echo Running tests with HTML coverage report...
    python -m pytest --cov=backend.app --cov-report=html --cov-report=term-missing -v
    echo.
    echo HTML coverage report generated in htmlcov/index.html
) else if "%1"=="--min" (
    echo Running tests with minimum coverage threshold (80%%)...
    python -m pytest --cov=backend.app --cov-report=term-missing --cov-fail-under=80 -v
) else (
    echo Running tests with coverage report...
    python -m pytest --cov=backend.app --cov-report=term-missing -v
)

echo.
echo Tests completed!

