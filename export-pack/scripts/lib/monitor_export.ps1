# Azure Monitor / Log Analytics Exporter
# Exports Log Analytics workspaces, DCR/DCE, alert rules, and action groups

. "$PSScriptRoot\common.ps1"

function Export-MonitorResources {
    param(
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting Monitor resources" @{
        ResourceGroup = $ResourceGroupName
        SubscriptionId = $SubscriptionId
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $monitorPath = Join-Path $OutputPath "monitor"
    if (-not (Test-Path $monitorPath)) {
        New-Item -ItemType Directory -Path $monitorPath -Force | Out-Null
    }
    
    # Export Log Analytics workspaces
    try {
        $workspaces = az monitor log-analytics workspace list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $workspaces) {
            foreach ($workspace in $workspaces) {
                $wsPath = Join-Path $monitorPath "workspaces" (Get-SafeFileName $workspace.name)
                if (-not (Test-Path $wsPath)) {
                    New-Item -ItemType Directory -Path $wsPath -Force | Out-Null
                }
                
                $redacted = Remove-SecretsFromObject $workspace
                Save-JsonFile -Path (Join-Path $wsPath "workspace.json") -Data $redacted -RedactSecrets
            }
            Write-Log "SUCCESS" "Log Analytics workspaces exported" @{ Count = $workspaces.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export Log Analytics workspaces" @{ Error = $_.Exception.Message }
    }
    
    # Export Data Collection Rules (DCR)
    try {
        $dcrs = az monitor data-collection rule list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $dcrs) {
            Save-JsonFile -Path (Join-Path $monitorPath "data_collection_rules.json") -Data $dcrs -RedactSecrets
            Write-Log "SUCCESS" "Data Collection Rules exported" @{ Count = $dcrs.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export Data Collection Rules" @{ Error = $_.Exception.Message }
    }
    
    # Export Data Collection Endpoints (DCE)
    try {
        $dces = az monitor data-collection endpoint list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $dces) {
            Save-JsonFile -Path (Join-Path $monitorPath "data_collection_endpoints.json") -Data $dces -RedactSecrets
            Write-Log "SUCCESS" "Data Collection Endpoints exported" @{ Count = $dces.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export Data Collection Endpoints" @{ Error = $_.Exception.Message }
    }
    
    # Export metric alert rules
    try {
        $metricAlerts = az monitor metrics alert list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $metricAlerts) {
            Save-JsonFile -Path (Join-Path $monitorPath "metric_alerts.json") -Data $metricAlerts -RedactSecrets
            Write-Log "SUCCESS" "Metric alerts exported" @{ Count = $metricAlerts.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export metric alerts" @{ Error = $_.Exception.Message }
    }
    
    # Export scheduled query alert rules (Log Analytics alerts)
    try {
        $scheduledQueryAlerts = az monitor scheduled-query list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $scheduledQueryAlerts) {
            Save-JsonFile -Path (Join-Path $monitorPath "scheduled_query_alerts.json") -Data $scheduledQueryAlerts -RedactSecrets
            Write-Log "SUCCESS" "Scheduled query alerts exported" @{ Count = $scheduledQueryAlerts.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export scheduled query alerts" @{ Error = $_.Exception.Message }
    }
    
    # Export action groups
    try {
        $actionGroups = az monitor action-group list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $actionGroups) {
            $redacted = $actionGroups | ForEach-Object {
                Remove-SecretsFromObject $_
            }
            Save-JsonFile -Path (Join-Path $monitorPath "action_groups.json") -Data $redacted -RedactSecrets
            Write-Log "SUCCESS" "Action groups exported" @{ Count = $actionGroups.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export action groups" @{ Error = $_.Exception.Message }
    }
    
    # Export Prometheus rule groups (if available)
    try {
        $prometheusRules = az prometheus rule-group list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $prometheusRules) {
            Save-JsonFile -Path (Join-Path $monitorPath "prometheus_rule_groups.json") -Data $prometheusRules -RedactSecrets
            Write-Log "SUCCESS" "Prometheus rule groups exported" @{ Count = $prometheusRules.Count }
        }
    }
    catch {
        Write-Log "INFO" "Prometheus rule groups not found or command not available (this is OK)"
    }
    
    Write-Log "SUCCESS" "Monitor resources export completed" @{ ResourceGroup = $ResourceGroupName }
}

function Export-MonitorWorkbooks {
    param(
        [string]$WorkspaceName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting Monitor workbooks and saved searches" @{
        Workspace = $WorkspaceName
        ResourceGroup = $ResourceGroupName
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $workspacePath = Join-Path $OutputPath "workspaces" (Get-SafeFileName $WorkspaceName)
    if (-not (Test-Path $workspacePath)) {
        New-Item -ItemType Directory -Path $workspacePath -Force | Out-Null
    }
    
    $workbooksPath = Join-Path $workspacePath "workbooks"
    $savedSearchesPath = Join-Path $workspacePath "savedsearches"
    
    if (-not (Test-Path $workbooksPath)) {
        New-Item -ItemType Directory -Path $workbooksPath -Force | Out-Null
    }
    if (-not (Test-Path $savedSearchesPath)) {
        New-Item -ItemType Directory -Path $savedSearchesPath -Force | Out-Null
    }
    
    # Get workspace resource ID
    try {
        $workspace = az monitor log-analytics workspace show --workspace-name $WorkspaceName --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        $workspaceId = $workspace.id
        $workspaceResourceId = $workspace.customerId
    }
    catch {
        Write-Log "WARN" "Failed to get workspace details" @{ Error = $_.Exception.Message }
        return
    }
    
    # Generate operator-assisted script for workbooks
    Generate-WorkbookExportScript -WorkspaceName $WorkspaceName -ResourceGroupName $ResourceGroupName `
        -SubscriptionId $SubscriptionId -WorkspaceId $workspaceId -OutputPath $workbooksPath
    
    # Generate operator-assisted script for saved searches
    Generate-SavedSearchExportScript -WorkspaceName $WorkspaceName -ResourceGroupName $ResourceGroupName `
        -SubscriptionId $SubscriptionId -WorkspaceResourceId $workspaceResourceId -OutputPath $savedSearchesPath
    
    Write-Log "SUCCESS" "Workbook/saved search export scripts generated" @{ Workspace = $WorkspaceName }
}

function Generate-WorkbookExportScript {
    param(
        [string]$WorkspaceName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$WorkspaceId,
        [string]$OutputPath
    )
    
    $scriptPath = Join-Path $OutputPath "export_workbooks.ps1"
    
    $scriptContent = @"
# Log Analytics Workbook Export Script
# Exports workbooks from Log Analytics workspace

param(
    [Parameter(Mandatory=`$true)]
    [string]`$WorkspaceName = "$WorkspaceName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$ResourceGroupName = "$ResourceGroupName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$SubscriptionId = "$SubscriptionId"
)

`$ErrorActionPreference = "Stop"

Write-Host "Exporting Log Analytics Workbooks" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

az account set --subscription `$SubscriptionId | Out-Null

# Get workspace details
`$workspace = az monitor log-analytics workspace show --workspace-name `$WorkspaceName --resource-group `$ResourceGroupName --output json | ConvertFrom-Json
`$workspaceId = `$workspace.id

# Get access token for REST API
`$token = az account get-access-token --query accessToken -o tsv
`$headers = @{
    "Authorization" = "Bearer `$token"
    "Content-Type" = "application/json"
}

# List workbooks
`$uri = "https://management.azure.com`$workspaceId/workbooks?api-version=2023-06-01"
`$workbooks = Invoke-RestMethod -Uri `$uri -Method Get -Headers `$headers

if (`$workbooks.value) {
    Write-Host "Found `$(`$workbooks.value.Count) workbooks" -ForegroundColor Green
    
    foreach (`$workbook in `$workbooks.value) {
        `$workbookName = `$workbook.name
        `$safeName = `$workbookName -replace '[^\w\-]', '_'
        `$outputFile = Join-Path `$PSScriptRoot "`$safeName.json"
        
        Write-Host "Exporting workbook: `$workbookName" -ForegroundColor Gray
        
        # Get full workbook details
        `$workbookUri = "https://management.azure.com`$workspaceId/workbooks/`$workbookName?api-version=2023-06-01"
        `$workbookDetails = Invoke-RestMethod -Uri `$workbookUri -Method Get -Headers `$headers
        
        `$workbookDetails | ConvertTo-Json -Depth 20 | Set-Content -Path `$outputFile -Encoding UTF8
        Write-Host "  ✓ Saved to `$outputFile" -ForegroundColor Green
    }
}
else {
    Write-Host "No workbooks found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Workbook export completed." -ForegroundColor Green
"@
    
    Set-Content -Path $scriptPath -Value $scriptContent -Encoding UTF8
    Write-Log "INFO" "Generated workbook export script" @{ Path = $scriptPath }
}

function Generate-SavedSearchExportScript {
    param(
        [string]$WorkspaceName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$WorkspaceResourceId,
        [string]$OutputPath
    )
    
    $scriptPath = Join-Path $OutputPath "export_saved_searches.ps1"
    
    $scriptContent = @"
# Log Analytics Saved Search Export Script
# Exports saved searches from Log Analytics workspace

param(
    [Parameter(Mandatory=`$true)]
    [string]`$WorkspaceName = "$WorkspaceName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$ResourceGroupName = "$ResourceGroupName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$SubscriptionId = "$SubscriptionId"
)

`$ErrorActionPreference = "Stop"

Write-Host "Exporting Log Analytics Saved Searches" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

az account set --subscription `$SubscriptionId | Out-Null

# Get workspace customer ID
`$workspace = az monitor log-analytics workspace show --workspace-name `$WorkspaceName --resource-group `$ResourceGroupName --output json | ConvertFrom-Json
`$customerId = `$workspace.customerId

# Get access token
`$token = az account get-access-token --query accessToken -o tsv
`$headers = @{
    "Authorization" = "Bearer `$token"
    "Content-Type" = "application/json"
}

# List saved searches via REST API
`$uri = "https://api.loganalytics.io/v1/workspaces/`$customerId/savedSearches"
`$savedSearches = Invoke-RestMethod -Uri `$uri -Method Get -Headers `$headers

if (`$savedSearches.value) {
    Write-Host "Found `$(`$savedSearches.value.Count) saved searches" -ForegroundColor Green
    
    `$savedSearches.value | ConvertTo-Json -Depth 20 | Set-Content -Path (Join-Path `$PSScriptRoot "saved_searches.json") -Encoding UTF8
    Write-Host "Saved searches exported to saved_searches.json" -ForegroundColor Green
}
else {
    Write-Host "No saved searches found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Saved search export completed." -ForegroundColor Green
"@
    
    Set-Content -Path $scriptPath -Value $scriptContent -Encoding UTF8
    Write-Log "INFO" "Generated saved search export script" @{ Path = $scriptPath }
}

# Functions available when dot-sourced

