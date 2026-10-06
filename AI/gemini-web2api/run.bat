@echo off
title Gemini Web2API Server
cd /d "%~dp0"

echo ==========================================================
echo               Gemini Web2API Server Startup
echo ==========================================================
echo.

rem Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to system PATH.
    echo Please install Python 3.8 or higher.
    pause
    exit /b 1
)

rem Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment venv...
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] Virtual environment venv not found.
    echo Running with default system python.
)

rem Check for httpx module
python -c "import httpx" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] httpx is not installed. Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

rem Start the server with any optional arguments passed to the script
echo.
echo [INFO] Starting Gemini Web2API server...
echo.
python gemini_web2api.py %*

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server terminated with exit code %errorlevel%.
    pause
)
