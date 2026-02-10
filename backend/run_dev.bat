@echo off
REM Development server startup script for Windows

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%~dp0..
set VENV_PATH=%PROJECT_ROOT%\.venv

REM Check if virtual environment exists
if not exist "%VENV_PATH%\pyvenv.cfg" (
    echo Virtual environment not found. Creating one...
    echo Creating virtual environment at: %VENV_PATH%
    python -m venv "%VENV_PATH%"
    if errorlevel 1 (
        echo Failed to create virtual environment. Please ensure Python is installed.
        exit /b 1
    )
    echo Virtual environment created successfully!
    
    echo Installing dependencies...
    "%VENV_PATH%\Scripts\pip.exe" install -r "%SCRIPT_DIR%\requirements.txt"
    if errorlevel 1 (
        echo Failed to install dependencies.
        exit /b 1
    )
    echo Dependencies installed successfully!
)

REM Activate virtual environment
call "%VENV_PATH%\Scripts\activate.bat"

REM Change to backend directory
cd /d "%SCRIPT_DIR%"

REM Run uvicorn from backend directory (use python -m for reliability)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 %*

