# PowerShell script to deploy FinDataExtractorVanilla infrastructure to Azure

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "rg-dio-findataextractorvanilla-cace",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "canadaeast",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory=$false)]
    [string]$SubscriptionId = ""
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FinDataExtractorVanilla Infrastructure Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Azure CLI
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Azure CLI not found. Please install Azure CLI." -ForegroundColor Red
    exit 1
}

# Login to Azure
Write-Host "[INFO] Checking Azure login..." -ForegroundColor Yellow
$account = az account show 2>$null
if (-not $account) {
    Write-Host "[INFO] Logging in to Azure..." -ForegroundColor Yellow
    az login
}

# Set subscription if provided
if ($SubscriptionId) {
    Write-Host "[INFO] Setting subscription to $SubscriptionId..." -ForegroundColor Yellow
    az account set --subscription $SubscriptionId
}

# Get current subscription
$currentSub = az account show --query id -o tsv
Write-Host "[INFO] Using subscription: $currentSub" -ForegroundColor Green
Write-Host ""

# Create resource group if it doesn't exist
Write-Host "[INFO] Creating resource group: $ResourceGroupName..." -ForegroundColor Yellow
$rgExists = az group exists --name $ResourceGroupName
if ($rgExists -eq "false") {
    az group create --name $ResourceGroupName --location $Location
    Write-Host "[OK] Resource group created" -ForegroundColor Green
} else {
    Write-Host "[OK] Resource group already exists" -ForegroundColor Green
}
Write-Host ""

# Deploy Bicep template
Write-Host "[INFO] Deploying infrastructure..." -ForegroundColor Yellow
$deploymentName = "findataextractorvanilla-deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

az deployment group create `
    --resource-group $ResourceGroupName `
    --name $deploymentName `
    --template-file "$PSScriptRoot\main.bicep" `
    --parameters environment=$Environment location=$Location

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Infrastructure deployed successfully!" -ForegroundColor Green
    Write-Host ""
    
    # Get outputs
    Write-Host "[INFO] Deployment outputs:" -ForegroundColor Yellow
    az deployment group show `
        --resource-group $ResourceGroupName `
        --name $deploymentName `
        --query properties.outputs `
        --output table
    
    Write-Host ""
    Write-Host "[SUCCESS] Deployment complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Store secrets in Key Vault:" -ForegroundColor White
    Write-Host "     - document-intelligence-endpoint" -ForegroundColor Gray
    Write-Host "     - document-intelligence-key" -ForegroundColor Gray
    Write-Host "     - storage-connection-string" -ForegroundColor Gray
    Write-Host "  2. Run database migrations" -ForegroundColor White
    Write-Host "  3. Deploy application container" -ForegroundColor White
} else {
    Write-Host "[ERROR] Deployment failed!" -ForegroundColor Red
    exit 1
}

