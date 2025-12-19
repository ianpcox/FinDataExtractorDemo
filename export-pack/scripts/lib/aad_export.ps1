# Azure AD (Entra) App Registration and Service Principal Stubs
# Discovers app IDs and generates recreation scripts

. "$PSScriptRoot\common.ps1"

function Export-AADStubs {
    param(
        [string]$SubscriptionId,
        [string]$OutputPath,
        [array]$ResourceGroups = @()
    )
    
    Write-Log "INFO" "Exporting Azure AD app registration stubs" @{ SubscriptionId = $SubscriptionId }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $metadataPath = Join-Path $OutputPath "metadata"
    if (-not (Test-Path $metadataPath)) {
        New-Item -ItemType Directory -Path $metadataPath -Force | Out-Null
    }
    
    $discoveredApps = @()
    
    # Discover from RBAC assignments
    try {
        Write-Log "INFO" "Discovering app IDs from RBAC assignments"
        $assignments = az role assignment list --all --output json 2>&1 | ConvertFrom-Json
        if ($assignments) {
            foreach ($assignment in $assignments) {
                if ($assignment.principalType -eq "ServicePrincipal" -and $assignment.principalId) {
                    $discoveredApps += @{
                        AppId = $assignment.principalId
                        ObjectId = $assignment.principalId
                        DisplayName = $assignment.principalName
                        ReferencedIn = "RBAC Assignment: $($assignment.roleDefinitionName) at $($assignment.scope)"
                        PrincipalType = "ServicePrincipal"
                    }
                }
            }
        }
    }
    catch {
        Write-Log "WARN" "Failed to discover apps from RBAC" @{ Error = $_.Exception.Message }
    }
    
    # Discover from managed identities (if we can get them from resources)
    # This would require parsing resource configs - simplified for now
    
    # Deduplicate by ObjectId
    $uniqueApps = $discoveredApps | Sort-Object -Property ObjectId -Unique
    
    if ($uniqueApps.Count -gt 0) {
        Save-JsonFile -Path (Join-Path $metadataPath "identity_stubs.json") -Data $uniqueApps -RedactSecrets
        
        # Create CSV
        $csvData = $uniqueApps | Select-Object AppId, ObjectId, DisplayName, ReferencedIn, PrincipalType
        $csvPath = Join-Path $metadataPath "identity_stubs.csv"
        $csvData | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
        
        # Generate recreation script template
        Generate-AADRecreationScript -Apps $uniqueApps -OutputPath $metadataPath
        
        Write-Log "SUCCESS" "Azure AD stubs exported" @{ Count = $uniqueApps.Count }
    }
    else {
        Write-Log "INFO" "No Azure AD apps/service principals discovered"
    }
    
    return $uniqueApps
}

function Generate-AADRecreationScript {
    param(
        [array]$Apps,
        [string]$OutputPath
    )
    
    $scriptPath = Join-Path $OutputPath "recreate_aad_apps.ps1"
    
    $appList = $Apps | ForEach-Object {
        "    # App: $($_.DisplayName) (ObjectId: $($_.ObjectId))"
        "    # Referenced in: $($_.ReferencedIn)"
        "    # az ad app create --display-name `"$($_.DisplayName)`" --required-resource-accesses @()"
        "    # az ad sp create --id <app-id-from-above>"
        ""
    } | Out-String
    
    $scriptContent = @"
# Azure AD App Registration Recreation Script
# This script provides templates to recreate app registrations and service principals
# discovered in the source environment.

# Prerequisites:
# - Azure CLI with Graph API permissions
# - Application Administrator or Global Administrator role
# - Authenticated to target tenant: az login

param(
    [Parameter(Mandatory=`$true)]
    [string]`$TargetTenantId
)

`$ErrorActionPreference = "Stop"

Write-Host "Azure AD App Registration Recreation" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script provides templates for recreating app registrations." -ForegroundColor Yellow
Write-Host "Review and customize each command before execution." -ForegroundColor Yellow
Write-Host ""

# Read discovered apps
`$apps = Get-Content (Join-Path `$PSScriptRoot "identity_stubs.json") | ConvertFrom-Json

Write-Host "Found `$(`$apps.Count) app registrations/service principals to recreate" -ForegroundColor Green
Write-Host ""

foreach (`$app in `$apps) {
    Write-Host "Processing: `$(`$app.DisplayName)" -ForegroundColor Cyan
    Write-Host "  ObjectId: `$(`$app.ObjectId)" -ForegroundColor Gray
    Write-Host "  Referenced in: `$(`$app.ReferencedIn)" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "  Step 1: Create app registration" -ForegroundColor Yellow
    Write-Host "  az ad app create \`" -ForegroundColor White
    Write-Host "    --display-name `"`$(`$app.DisplayName)`" \`" -ForegroundColor White
    Write-Host "    --required-resource-accesses @() \`" -ForegroundColor White
    Write-Host "    --web-redirect-uris @() \`" -ForegroundColor White
    Write-Host "    --api-permissions @()" -ForegroundColor White
    Write-Host ""
    
    Write-Host "  Step 2: Create service principal (if needed)" -ForegroundColor Yellow
    Write-Host "  `$newAppId = (az ad app create ... | ConvertFrom-Json).appId" -ForegroundColor White
    Write-Host "  az ad sp create --id `$newAppId" -ForegroundColor White
    Write-Host ""
    
    Write-Host "  Step 3: Assign roles (if needed)" -ForegroundColor Yellow
    Write-Host "  az role assignment create \`" -ForegroundColor White
    Write-Host "    --assignee `$newAppId \`" -ForegroundColor White
    Write-Host "    --role <role-name> \`" -ForegroundColor White
    Write-Host "    --scope <resource-scope>" -ForegroundColor White
    Write-Host ""
    
    Write-Host "  Note: Secrets and certificates must be created manually" -ForegroundColor Yellow
    Write-Host "  Note: Required permissions must be configured manually" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  ---" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "Recreation script completed." -ForegroundColor Green
Write-Host "Review identity_stubs.json and identity_stubs.csv for details." -ForegroundColor Yellow
"@
    
    Set-Content -Path $scriptPath -Value $scriptContent -Encoding UTF8
    Write-Log "INFO" "Generated AAD recreation script" @{ Path = $scriptPath }
}

# Functions available when dot-sourced

