# PowerShell script to run tests with coverage

Write-Host "Running tests with coverage..." -ForegroundColor Green

# Run tests
pytest --cov=src --cov-report=html --cov-report=term-missing -v

# Check exit code
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nTests passed! Coverage report generated in htmlcov/index.html" -ForegroundColor Green
} else {
    Write-Host "`nTests failed! Check output above." -ForegroundColor Red
    exit $LASTEXITCODE
}

