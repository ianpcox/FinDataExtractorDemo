# Azure SQL Exporter
# Exports SQL Server configuration, firewall rules, and database inventory

. "$PSScriptRoot\common.ps1"

function Export-SQLServer {
    param(
        [string]$ServerName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting Azure SQL Server" @{
        ServerName = $ServerName
        ResourceGroup = $ResourceGroupName
        SubscriptionId = $SubscriptionId
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $sqlPath = Join-Path $OutputPath "sql" (Get-SafeFileName $ServerName)
    if (-not (Test-Path $sqlPath)) {
        New-Item -ItemType Directory -Path $sqlPath -Force | Out-Null
    }
    
    # Export server configuration
    try {
        $server = az sql server show --name $ServerName --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0) {
            $redacted = Remove-SecretsFromObject $server
            Save-JsonFile -Path (Join-Path $sqlPath "server.json") -Data $redacted -RedactSecrets
            Write-Log "SUCCESS" "SQL Server configuration exported"
        }
        else {
            Write-Log "ERROR" "Failed to get SQL Server details"
            return
        }
    }
    catch {
        Write-Log "ERROR" "Failed to export SQL Server" @{ Error = $_.Exception.Message }
        return
    }
    
    # Export firewall rules
    try {
        $firewallRules = az sql server firewall-rule list --server $ServerName --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $firewallRules) {
            Save-JsonFile -Path (Join-Path $sqlPath "firewall_rules.json") -Data $firewallRules
            Write-Log "SUCCESS" "Firewall rules exported" @{ Count = $firewallRules.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export firewall rules" @{ Error = $_.Exception.Message }
    }
    
    # Export database list
    try {
        $databases = az sql db list --server $ServerName --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $databases) {
            Save-JsonFile -Path (Join-Path $sqlPath "databases.json") -Data $databases -RedactSecrets
            
            # Create summary
            $summary = $databases | Select-Object `
                @{Name='Name'; Expression={$_.name}}, `
                @{Name='Status'; Expression={$_.status}}, `
                @{Name='Edition'; Expression={$_.edition}}, `
                @{Name='ServiceObjective'; Expression={$_.currentServiceObjectiveName}}, `
                @{Name='MaxSizeBytes'; Expression={$_.maxSizeBytes}}, `
                @{Name='CreationDate'; Expression={$_.creationDate}}
            
            $summary | Export-Csv -Path (Join-Path $sqlPath "databases_summary.csv") -NoTypeInformation -Encoding UTF8
            Write-Log "SUCCESS" "Databases exported" @{ Count = $databases.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export databases" @{ Error = $_.Exception.Message }
    }
    
    # Generate data export helper script
    Generate-SQLDataExportScript -ServerName $ServerName -ResourceGroupName $ResourceGroupName `
        -SubscriptionId $SubscriptionId -OutputPath $sqlPath
}

function Generate-SQLDataExportScript {
    param(
        [string]$ServerName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    $scriptPath = Join-Path $OutputPath "export_data.ps1"
    
    # Get database list for the script
    try {
        Set-AzureSubscription -SubscriptionId $SubscriptionId
        $databases = az sql db list --server $ServerName --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        $dbNames = if ($databases) { $databases | ForEach-Object { $_.name } } else { @() }
    }
    catch {
        $dbNames = @()
    }
    
    $scriptContent = @"
# Operator-assisted SQL data export script
# This script exports SQL databases as BACPAC files
# Requires storage account SAS token for export destination

param(
    [Parameter(Mandatory=`$true)]
    [string]`$ServerName = "$ServerName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$ResourceGroupName = "$ResourceGroupName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$SubscriptionId = "$SubscriptionId",
    
    [Parameter(Mandatory=`$true)]
    [string]`$StorageAccountName,
    
    [Parameter(Mandatory=`$true)]
    [string]`$StorageContainerName,
    
    [string[]]`$DatabaseNames = @($($dbNames | ForEach-Object { "'$_'" } -join ", ")),
    
    [string]`$StorageResourceGroup
)

`$ErrorActionPreference = "Stop"

Write-Host "SQL Database BACPAC Export Script" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Set subscription
az account set --subscription `$SubscriptionId | Out-Null

# Prompt for storage SAS token (secure)
Write-Host "Enter storage account SAS token for export destination (input will be hidden):" -ForegroundColor Yellow
`$sasToken = Read-Host -AsSecureString
`$sasTokenPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR(`$sasToken)
)

if ([string]::IsNullOrWhiteSpace(`$sasTokenPlain)) {
    Write-Error "SAS token is required"
    exit 1
}

# Construct storage URL
`$storageUrl = "https://`$StorageAccountName.blob.core.windows.net/`$StorageContainerName"

# Export each database
foreach (`$dbName in `$DatabaseNames) {
    Write-Host "Exporting database: `$dbName..." -ForegroundColor Cyan
    
    `$bacpacName = "`$dbName-`$(Get-Date -Format 'yyyyMMdd-HHmmss').bacpac"
    `$bacpacUrl = "`$storageUrl/`$bacpacName`$sasTokenPlain"
    
    try {
        az sql db export `
            --server `$ServerName `
            --resource-group `$ResourceGroupName `
            --name `$dbName `
            --storage-key-type SharedAccessKey `
            --storage-key `$sasTokenPlain `
            --storage-uri `$bacpacUrl `
            --administrator-login (Read-Host "Enter SQL admin username for `$ServerName") `
            --administrator-login-password (Read-Host "Enter SQL admin password (input will be hidden)" -AsSecureString | ConvertFrom-SecureString -AsPlainText)
        
        if (`$LASTEXITCODE -eq 0) {
            Write-Host "Export initiated for `$dbName. BACPAC will be saved to: `$bacpacUrl" -ForegroundColor Green
        }
        else {
            Write-Warning "Failed to initiate export for `$dbName"
        }
    }
    catch {
        Write-Error "Error exporting `$dbName : `$(`$_.Exception.Message)"
    }
}

# Clear SAS token from memory
`$sasTokenPlain = `$null
`$sasToken = `$null

Write-Host ""
Write-Host "Export operations completed. Check Azure Portal for export status." -ForegroundColor Green
Write-Host "BACPAC files will be available at: `$storageUrl" -ForegroundColor Green
Write-Host ""
Write-Host "Validation Steps:" -ForegroundColor Cyan
Write-Host "1. Verify BACPAC files in storage account" -ForegroundColor White
Write-Host "2. Check file sizes match source databases" -ForegroundColor White
Write-Host "3. Import to target SQL Server and verify schema" -ForegroundColor White
Write-Host "4. Run data validation queries" -ForegroundColor White
Write-Host ""
Write-Host "Enhanced Import Command (with validation):" -ForegroundColor Cyan
Write-Host "az sql db import \`" -ForegroundColor White
Write-Host "  --server <target-server> \`" -ForegroundColor White
Write-Host "  --resource-group <target-rg> \`" -ForegroundColor White
Write-Host "  --name <target-db-name> \`" -ForegroundColor White
Write-Host "  --storage-key-type SharedAccessKey \`" -ForegroundColor White
Write-Host "  --storage-key <sas-token> \`" -ForegroundColor White
Write-Host "  --storage-uri <bacpac-url> \`" -ForegroundColor White
Write-Host "  --administrator-login <admin> \`" -ForegroundColor White
Write-Host "  --administrator-login-password <password>" -ForegroundColor White
"@
    
    Set-Content -Path $scriptPath -Value $scriptContent -Encoding UTF8
    Write-Log "INFO" "Generated SQL data export helper script" @{ Path = $scriptPath }
}

# Functions available when dot-sourced

