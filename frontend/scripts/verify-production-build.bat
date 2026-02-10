@echo off
REM Production build verification script for Windows
REM Verifies that the production build completes successfully

echo Building production bundle...
call npm run build

if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    exit /b 1
)

echo Build completed successfully

echo Checking build output...
if not exist "dist" (
    echo Error: dist directory not found
    exit /b 1
)

echo Build output directory exists

echo Verifying critical files...
if not exist "dist\index.html" (
    echo Error: index.html not found in dist
    exit /b 1
)

echo index.html found

echo Production build verification complete!

