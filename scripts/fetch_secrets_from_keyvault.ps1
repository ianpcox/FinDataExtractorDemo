# PowerShell script to fetch secrets from Azure Key Vault and update .env

param(
    [string]$KeyVaultName = "kvdiofindataextractor"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fetch Secrets from Azure Key Vault" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if logged in
Write-Host "[INFO] Checking Azure login..." -ForegroundColor Yellow
$account = az account show 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Not logged in to Azure CLI" -ForegroundColor Red
    Write-Host "Please run: az login" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Logged in to Azure" -ForegroundColor Green
Write-Host ""

# Get secrets
$secrets = @{
    "document-intelligence-endpoint" = "AZURE_FORM_RECOGNIZER_ENDPOINT"
    "document-intelligence-key" = "AZURE_FORM_RECOGNIZER_KEY"
}

$envFile = Join-Path $PSScriptRoot "..\.env"
$updated = $false

foreach ($secretName in $secrets.Keys) {
    $envVarName = $secrets[$secretName]
    
    Write-Host "[INFO] Fetching secret: $secretName..." -ForegroundColor Yellow
    
    try {
        $secretValue = az keyvault secret show `
            --vault-name $KeyVaultName `
            --name $secretName `
            --query value `
            -o tsv 2>$null
        
        if ($LASTEXITCODE -eq 0 -and $secretValue) {
            # Update .env file
            $content = Get-Content $envFile -Raw
            
            # Check if variable exists
            if ($content -match "$envVarName=.*") {
                # Replace existing value
                $content = $content -replace "$envVarName=.*", "$envVarName=$secretValue"
            } else {
                # Append new variable
                $content += "`n$envVarName=$secretValue"
            }
            
            Set-Content -Path $envFile -Value $content -NoNewline
            Write-Host "[OK] Updated $envVarName in .env" -ForegroundColor Green
            $updated = $true
        } else {
            Write-Host "[WARN] Could not fetch $secretName" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[WARN] Error fetching $secretName : $_" -ForegroundColor Yellow
    }
}

Write-Host ""

if ($updated) {
    Write-Host "[SUCCESS] Credentials updated in .env file" -ForegroundColor Green
    Write-Host "You can now run tests or use Document Intelligence features" -ForegroundColor Cyan
} else {
    Write-Host "[ERROR] No credentials were updated" -ForegroundColor Red
    Write-Host "Please check:" -ForegroundColor Yellow
    Write-Host "  1. You're logged in: az login" -ForegroundColor White
    Write-Host "  2. You have access to Key Vault: $KeyVaultName" -ForegroundColor White
    Write-Host "  3. The secrets exist in Key Vault" -ForegroundColor White
}

