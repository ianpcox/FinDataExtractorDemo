# PowerShell script to start FinDataExtractorDEMO
# Sources invoices from FinDataExtractor/data

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FinDataExtractorDEMO Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if demo database exists
$demoDb = "findataextractor_demo.db"
if (-not (Test-Path $demoDb)) {
    Write-Host "Demo database not found. Running setup..." -ForegroundColor Yellow
    $env:DEMO_MODE = "true"
    $env:DATABASE_URL = "sqlite+aiosqlite:///./findataextractor_demo.db"
    python scripts/setup_demo.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nERROR: Setup failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
}

# Set environment variables
$env:DEMO_MODE = "true"
$env:DATABASE_URL = "sqlite+aiosqlite:///./findataextractor_demo.db"

Write-Host "Starting services..." -ForegroundColor Cyan
Write-Host "  DEMO_MODE: $env:DEMO_MODE" -ForegroundColor White
Write-Host "  DATABASE_URL: $env:DATABASE_URL" -ForegroundColor White
Write-Host ""

# Start API server in new window
Write-Host "Starting API Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; `$env:DEMO_MODE='true'; `$env:DATABASE_URL='sqlite+aiosqlite:///./findataextractor_demo.db'; . .\venv\Scripts\Activate.ps1; Write-Host '=== API Server (DEMO MODE) ===' -ForegroundColor Cyan; Write-Host 'http://localhost:8000' -ForegroundColor Green; Write-Host 'http://localhost:8000/docs' -ForegroundColor Green; uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"

# Wait for API server to start
Start-Sleep -Seconds 4

# Start Streamlit UI in new window
Write-Host "Starting Streamlit UI..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; `$env:DEMO_MODE='true'; `$env:DATABASE_URL='sqlite+aiosqlite:///./findataextractor_demo.db'; . .\venv\Scripts\Activate.ps1; Write-Host '=== Streamlit UI (DEMO MODE) ===' -ForegroundColor Cyan; Write-Host 'http://localhost:8501' -ForegroundColor Green; streamlit run streamlit_app.py --server.port 8501 --server.address localhost"

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Demo Started Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  API Server:    http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:      http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Streamlit UI:  http://localhost:8501" -ForegroundColor White
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Mode:          DEMO (no Azure required)" -ForegroundColor Yellow
Write-Host "  Database:      findataextractor_demo.db" -ForegroundColor Yellow
Write-Host "  Invoices:      Sourced from FinDataExtractor/data" -ForegroundColor Yellow
Write-Host ""
Write-Host "Ready to use! Open http://localhost:8501 in your browser." -ForegroundColor Green

