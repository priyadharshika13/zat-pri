#!/bin/bash
# Development server startup script for Linux/Mac

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
VENV_PATH="$PROJECT_ROOT/.venv"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ] || [ ! -f "$VENV_PATH/pyvenv.cfg" ]; then
    echo "Virtual environment not found. Creating one..."
    echo "Creating virtual environment at: $VENV_PATH"
    python3 -m venv "$VENV_PATH"
    echo "Virtual environment created successfully!"
    
    echo "Installing dependencies..."
    "$VENV_PATH/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
    echo "Dependencies installed successfully!"
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Change to backend directory
cd "$SCRIPT_DIR"

# Run uvicorn from backend directory (use python -m for reliability)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 "$@"

