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

# Functions available when dot-sourced

