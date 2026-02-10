#!/usr/bin/env python
"""
Development server startup script.

Ensures the application runs from the correct directory with proper Python path.
Automatically creates and activates virtual environment if missing.
"""

import os
import sys
import subprocess
import venv
from pathlib import Path

# Get the backend directory (where this script is located)
backend_dir = Path(__file__).parent.absolute()
project_root = backend_dir.parent
venv_path = project_root / ".venv"

# Check if virtual environment exists
venv_exists = venv_path.exists() and (venv_path / "pyvenv.cfg").exists()

if not venv_exists:
    print("Virtual environment not found. Creating one...")
    print(f"Creating virtual environment at: {venv_path}")
    
    # Create virtual environment
    venv.create(venv_path, with_pip=True)
    print("Virtual environment created successfully!")
    
    # Determine the Python executable in the venv
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"
    
    print("Installing dependencies...")
    # Install requirements
    subprocess.run([
        str(pip_exe), "install", "-r", str(backend_dir / "requirements.txt")
    ], check=True)
    print("Dependencies installed successfully!")
else:
    # Use the virtual environment's Python
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    # Check if we're already using the venv Python
    current_python = Path(sys.executable).resolve()
    venv_python = python_exe.resolve()
    
    if current_python != venv_python:
        print(f"Virtual environment found at: {venv_path}")
        print("Note: Not using venv Python. Using current Python interpreter.")
        print("For best results, activate the virtual environment first:")
        if sys.platform == "win32":
            print(f"  .venv\\Scripts\\Activate.ps1")
        else:
            print(f"  source .venv/bin/activate")
        # Continue anyway - use current Python

# Change to backend directory
os.chdir(backend_dir)

# Add backend directory to Python path (in case it's not already there)
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Run uvicorn
if __name__ == "__main__":
    # Use the virtual environment's Python if it exists, otherwise use current
    if venv_exists and python_exe.exists():
        python = str(python_exe)
    else:
        python = sys.executable
    
    print(f"Starting development server with {python}...")
    print(f"Working directory: {backend_dir}")
    
    # Check for DATABASE_URL
    if not os.getenv("DATABASE_URL"):
        print("\n" + "="*60)
        print("WARNING: DATABASE_URL not set!")
        print("="*60)
        print("\nThe server will fail to start without DATABASE_URL.")
        print("\nSet it before starting the server:")
        if sys.platform == "win32":
            print('  PowerShell: $env:DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/zatca_ai"')
            print('  CMD: set DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/zatca_ai')
        else:
            print('  export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/zatca_ai"')
        print("\nOr for SQLite (local dev only, not recommended):")
        if sys.platform == "win32":
            print('  PowerShell: $env:DATABASE_URL="sqlite:///./zatca.db"')
            print('  CMD: set DATABASE_URL=sqlite:///./zatca.db')
        else:
            print('  export DATABASE_URL="sqlite:///./zatca.db"')
        print("\n" + "="*60)
        print("Attempting to start server anyway...")
        print("="*60 + "\n")
    
    # Build uvicorn command
    cmd = [
        python, "-m", "uvicorn",
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
    ]
    
    # Add any additional arguments from command line
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    
    # Run uvicorn
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
        sys.exit(0)
