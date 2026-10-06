# Windows PowerShell / PowerShell Core Startup Script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "               Gemini Web2API Server Startup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Verify Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ first." -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    Exit 1
}

# Activate virtual environment
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "[INFO] Activating virtual environment (.venv)..." -ForegroundColor Green
    & .venv\Scripts\Activate.ps1
} else {
    Write-Host "[WARNING] Virtual environment (.venv) not found. Using system Python." -ForegroundColor Yellow
}

# Verify dependencies
python -c "import httpx" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Installing required dependencies..." -ForegroundColor Green
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install dependencies." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        Exit 1
    }
}

Write-Host ""
Write-Host "[INFO] Starting Gemini Web2API server..." -ForegroundColor Green
Write-Host ""

# Run the python script forwarding all arguments
python gemini_web2api.py $args

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Server terminated with exit code $LASTEXITCODE." -ForegroundColor Red
    Read-Host "Press Enter to exit..."
}
