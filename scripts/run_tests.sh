#!/bin/bash
# Test runner script for ZATCA AI API

set -e

echo "Running ZATCA AI API Test Suite"
echo "=================================="
echo ""

# Change to project root directory
cd "$(dirname "$0")/.."

# Check if pytest is available via python -m pytest
if ! python -m pytest --version &> /dev/null; then
    echo "ERROR: pytest is not installed. Installing dependencies..."
    pip install -r backend/requirements.txt
fi

# Use python -m pytest for cross-platform compatibility (works on Windows/Git Bash)
# Default: run tests with coverage
if [ "$1" == "--no-cov" ]; then
    echo "Running tests without coverage..."
    python -m pytest -v
elif [ "$1" == "--html" ]; then
    echo "Running tests with HTML coverage report..."
    python -m pytest --cov=backend.app --cov-report=html --cov-report=term-missing -v
    echo ""
    echo "HTML coverage report generated in htmlcov/index.html"
elif [ "$1" == "--min" ]; then
    echo "Running tests with minimum coverage threshold (80%)..."
    python -m pytest --cov=backend.app --cov-report=term-missing --cov-fail-under=80 -v
else
    echo "Running tests with coverage report..."
    python -m pytest --cov=backend.app --cov-report=term-missing -v
fi

echo ""
echo "Tests completed!"

