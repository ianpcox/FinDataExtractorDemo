# Azure Storage Account Exporter
# Exports storage account configuration and generates data migration scripts

. "$PSScriptRoot\common.ps1"

function Export-StorageAccount {
    param(
        [string]$StorageAccountName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting Azure Storage Account" @{
        StorageAccountName = $StorageAccountName
        ResourceGroup = $ResourceGroupName
        SubscriptionId = $SubscriptionId
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $storagePath = Join-Path $OutputPath "storage" (Get-SafeFileName $StorageAccountName)
    if (-not (Test-Path $storagePath)) {
        New-Item -ItemType Directory -Path $storagePath -Force | Out-Null
    }
    
    # Export storage account configuration
    try {
        $storage = az storage account show --name $StorageAccountName --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0) {
            $redacted = Remove-SecretsFromObject $storage
            Save-JsonFile -Path (Join-Path $storagePath "account.json") -Data $redacted -RedactSecrets
            Write-Log "SUCCESS" "Storage account configuration exported"
        }
        else {
            Write-Log "ERROR" "Failed to get Storage Account details"
            return
        }
    }
    catch {
        Write-Log "ERROR" "Failed to export Storage Account" @{ Error = $_.Exception.Message }
        return
    }
    
    # Generate operator-assisted container/share listing and migration script
    Generate-StorageMigrationScript -StorageAccountName $StorageAccountName `
        -ResourceGroupName $ResourceGroupName -SubscriptionId $SubscriptionId -OutputPath $storagePath
}

function Generate-StorageMigrationScript {
    param(
        [string]$StorageAccountName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    $scriptPath = Join-Path $OutputPath "migrate_data.ps1"
    
    $scriptContent = @"
# Operator-assisted Storage data migration script
# This script lists containers/shares and generates AzCopy command stubs for data migration
# Requires storage account key or SAS token (prompted at runtime, not persisted)

param(
    [Parameter(Mandatory=`$true)]
    [string]`$StorageAccountName = "$StorageAccountName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$ResourceGroupName = "$ResourceGroupName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$SubscriptionId = "$SubscriptionId",
    
    [Parameter(Mandatory=`$true)]
    [string]`$TargetStorageAccountName,
    
    [Parameter(Mandatory=`$true)]
    [string]`$TargetContainerName,
    
    [ValidateSet("Key", "SAS")]
    [string]`$AuthMethod = "SAS"
)

`$ErrorActionPreference = "Stop"

Write-Host "Azure Storage Data Migration Script" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Set subscription
az account set --subscription `$SubscriptionId | Out-Null

# Get storage account details
`$storage = az storage account show --name `$StorageAccountName --resource-group `$ResourceGroupName --output json | ConvertFrom-Json
`$sourceUrl = "https://`$StorageAccountName.`$(`$storage.primaryEndpoints.blob.Split('/')[2])"

# Prompt for authentication
if (`$AuthMethod -eq "SAS") {
    Write-Host "Enter source storage account SAS token (input will be hidden):" -ForegroundColor Yellow
    `$sourceAuth = Read-Host -AsSecureString
    `$sourceAuthPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR(`$sourceAuth)
    )
    `$sourceUrlWithAuth = "`$sourceUrl`$sourceAuthPlain"
}
else {
    Write-Host "Enter source storage account key (input will be hidden):" -ForegroundColor Yellow
    `$sourceKey = Read-Host -AsSecureString
    `$sourceKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR(`$sourceKey)
    )
}

Write-Host "Enter target storage account SAS token (input will be hidden):" -ForegroundColor Yellow
`$targetAuth = Read-Host -AsSecureString
`$targetAuthPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR(`$targetAuth)
)

`$targetUrl = "https://`$TargetStorageAccountName.blob.core.windows.net/`$TargetContainerName`$targetAuthPlain"

# List containers
Write-Host "`nListing containers..." -ForegroundColor Cyan
try {
    if (`$AuthMethod -eq "SAS") {
        `$containers = az storage container list --account-name `$StorageAccountName --sas-token `$sourceAuthPlain --output json | ConvertFrom-Json
    }
    else {
        `$containers = az storage container list --account-name `$StorageAccountName --account-key `$sourceKeyPlain --output json | ConvertFrom-Json
    }
    
    if (`$containers) {
        `$containers | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path `$PSScriptRoot "containers.json") -Encoding UTF8
        
        Write-Host "Found `$(`$containers.Count) containers" -ForegroundColor Green
        Write-Host "`nGenerating AzCopy command stubs..." -ForegroundColor Cyan
        
        `$commands = @()
        foreach (`$container in `$containers) {
            `$containerName = `$container.name
            `$sourceContainerUrl = "`$sourceUrl/`$containerName"
            `$targetContainerUrl = "`$targetUrl/`$containerName"
            
            # Generate AzCopy command stub
            `$cmd = "azcopy copy `"`$sourceContainerUrl"
            if (`$AuthMethod -eq "SAS") {
                `$cmd += "`$sourceAuthPlain"
            }
            `$cmd += "`" `"`$targetContainerUrl`" --recursive"
            
            `$commands += `$cmd
        }
        
        `$commands | Set-Content -Path (Join-Path `$PSScriptRoot "azcopy_commands.txt") -Encoding UTF8
        Write-Host "AzCopy commands saved to: azcopy_commands.txt" -ForegroundColor Green
        Write-Host "`nIMPORTANT: Review and execute commands manually. Keys/SAS tokens are not embedded." -ForegroundColor Yellow
    }
}
catch {
    Write-Error "Failed to list containers: `$(`$_.Exception.Message)"
    exit 1
}

# List file shares (if any)
Write-Host "`nListing file shares..." -ForegroundColor Cyan
try {
    if (`$AuthMethod -eq "SAS") {
        `$shares = az storage share list --account-name `$StorageAccountName --sas-token `$sourceAuthPlain --output json 2>&1 | ConvertFrom-Json
    }
    else {
        `$shares = az storage share list --account-name `$StorageAccountName --account-key `$sourceKeyPlain --output json 2>&1 | ConvertFrom-Json
    }
    
    if (`$shares -and `$shares.Count -gt 0) {
        `$shares | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path `$PSScriptRoot "shares.json") -Encoding UTF8
        Write-Host "Found `$(`$shares.Count) file shares" -ForegroundColor Green
        Write-Host "Note: File share migration requires separate AzCopy commands or Azure File Sync" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "No file shares found or error listing shares (this is OK)" -ForegroundColor Gray
}

# Clear secrets from memory
`$sourceAuthPlain = `$null
`$sourceAuth = `$null
`$sourceKeyPlain = `$null
`$sourceKey = `$null
`$targetAuthPlain = `$null
`$targetAuth = `$null

Write-Host "`nMigration script completed. Review generated files before executing commands." -ForegroundColor Green
"@
    
    Set-Content -Path $scriptPath -Value $scriptContent -Encoding UTF8
    Write-Log "INFO" "Generated storage migration helper script" @{ Path = $scriptPath }
}

# Functions available when dot-sourced

