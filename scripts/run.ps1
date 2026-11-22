<#
.SYNOPSIS
    LENS Desktop Launcher for Windows PowerShell
.DESCRIPTION
    Checks virtual environment, verifies dependencies, starts the FastAPI server,
    and opens the LENS user interface in your default browser.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "      LENS: AI-Powered File Discovery     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check Python environment
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Virtual environment not detected at .\venv. Creating one..." -ForegroundColor Yellow
    python -m venv (Join-Path $ProjectRoot "venv")
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
}

# Verify frontend build exists
$DistIndex = Join-Path $ProjectRoot "frontend\dist\index.html"
if (-not (Test-Path $DistIndex)) {
    Write-Host "Compiling frontend distribution..." -ForegroundColor Yellow
    Push-Location (Join-Path $ProjectRoot "frontend")
    npm install
    npm run build
    Pop-Location
}

Write-Host "Starting LENS Server on http://127.0.0.1:8000..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Gray

# Open browser after a short delay
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://127.0.0.1:8000"
} | Out-Null

# Start backend server
Set-Location $ProjectRoot
& $VenvPython -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000
