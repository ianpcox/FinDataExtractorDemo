# PowerShell script to run tests with progress and timeout

param(
    [switch]$Fast = $false,
    [switch]$All = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Running Tests (45s SLA per test)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$startTime = Get-Date

if ($Fast) {
    Write-Host "[FAST MODE] Running without coverage, stopping on first failure" -ForegroundColor Yellow
    $pytestArgs = @(
        "tests/",
        "-v",
        "--tb=line",
        "--timeout=45",
        "--timeout-method=thread",
        "--durations=5",
        "--no-cov",
        "-x"
    )
} else {
    Write-Host "[FULL MODE] Running all tests with coverage" -ForegroundColor Yellow
    $pytestArgs = @(
        "tests/",
        "-v",
        "--tb=short",
        "--timeout=45",
        "--timeout-method=thread",
        "--durations=10",
        "--cov=src",
        "--cov-report=term-missing"
    )
}

Write-Host ""
Write-Host "Starting tests..." -ForegroundColor Green
Write-Host ""

# Activate venv and run pytest
& ".\venv\Scripts\Activate.ps1"
$result = & python -m pytest @pytestArgs 2>&1

$elapsed = (Get-Date) - $startTime

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tests completed in $($elapsed.TotalSeconds.ToString('F2')) seconds" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Output results
$result

# Check exit code
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[SUCCESS] All tests passed!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[FAILED] Some tests failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
}

exit $LASTEXITCODE

