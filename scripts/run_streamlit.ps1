# PowerShell script to run Streamlit HITL interface

Write-Host "Starting Streamlit HITL Interface..." -ForegroundColor Green
Write-Host ""
Write-Host "Prerequisites:" -ForegroundColor Yellow
Write-Host "  1. API server should be running on http://localhost:8000"
Write-Host "  2. Run: uvicorn api.main:app --reload"
Write-Host ""
Write-Host "Starting Streamlit..." -ForegroundColor Green

# Activate virtual environment and run Streamlit
cd $PSScriptRoot\..
.\venv\Scripts\Activate.ps1
streamlit run streamlit_app.py

