# Create Azure Storage Containers for FinDataExtractor Vanilla
# This script creates the vanilla-invoices-raw and vanilla-invoices-processed containers

param(
    [string]$ConnectionString = ""
)

# Read connection string from .env if not provided
if ([string]::IsNullOrEmpty($ConnectionString)) {
    $envFile = Join-Path $PSScriptRoot "..\.env"
    if (Test-Path $envFile) {
        $envContent = Get-Content $envFile
        $connStringLine = $envContent | Where-Object { $_ -match '^AZURE_STORAGE_CONNECTION_STRING=' }
        if ($connStringLine) {
            $ConnectionString = $connStringLine -replace 'AZURE_STORAGE_CONNECTION_STRING=', ''
            Write-Host "Connection string read from .env file" -ForegroundColor Green
        } else {
            Write-Host "ERROR: Could not find AZURE_STORAGE_CONNECTION_STRING in .env file" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "ERROR: .env file not found at $envFile" -ForegroundColor Red
        Write-Host "Please provide connection string as parameter: .\create_storage_containers.ps1 -ConnectionString 'YOUR_CONNECTION_STRING'" -ForegroundColor Yellow
        exit 1
    }
}

# Check if Azure CLI is installed
$azCli = Get-Command az -ErrorAction SilentlyContinue
if (-not $azCli) {
    Write-Host "ERROR: Azure CLI is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Azure CLI from: https://aka.ms/installazurecliwindows" -ForegroundColor Yellow
    exit 1
}

Write-Host "Creating Azure Storage containers for FinDataExtractor Vanilla..." -ForegroundColor Cyan
Write-Host ""

# Container names
$containers = @(
    "vanilla-invoices-raw",
    "vanilla-invoices-processed"
)

foreach ($containerName in $containers) {
    Write-Host "Creating container: $containerName" -ForegroundColor Yellow
    
    try {
        $result = az storage container create --name $containerName --connection-string $ConnectionString --auth-mode key 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Successfully created: $containerName" -ForegroundColor Green
        } else {
            # Check if container already exists
            if ($result -match "ContainerAlreadyExists") {
                Write-Host "  Container already exists: $containerName" -ForegroundColor Yellow
            } else {
                Write-Host "  Error creating container: $containerName" -ForegroundColor Red
                Write-Host "  Error: $result" -ForegroundColor Red
            }
        }
    } catch {
        Write-Host "  Exception creating container: $containerName" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "Container creation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Containers created:" -ForegroundColor Cyan
foreach ($containerName in $containers) {
    Write-Host "  - $containerName"
}
