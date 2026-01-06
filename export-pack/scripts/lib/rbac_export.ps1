# RBAC (Role Assignment) Exporter
# Exports role assignments at subscription and resource group scopes

. "$PSScriptRoot\common.ps1"

function Export-SubscriptionRBAC {
    param(
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting subscription-level RBAC" @{ SubscriptionId = $SubscriptionId }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $rbacPath = Join-Path $OutputPath "rbac"
    if (-not (Test-Path $rbacPath)) {
        New-Item -ItemType Directory -Path $rbacPath -Force | Out-Null
    }
    
    try {
        $assignments = az role assignment list --all --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $assignments) {
            # Filter to subscription scope only
            $subScope = "/subscriptions/$SubscriptionId"
            $subAssignments = $assignments | Where-Object { 
                $_.scope -eq $subScope -or $_.scope.StartsWith($subScope + "/")
            }
            
            Save-JsonFile -Path (Join-Path $rbacPath "subscription_assignments.json") -Data $subAssignments -RedactSecrets
            
            # Create CSV summary
            $csvData = $subAssignments | Select-Object `
                @{Name='Scope'; Expression={$_.scope}}, `
                @{Name='RoleDefinitionName'; Expression={$_.roleDefinitionName}}, `
                @{Name='PrincipalType'; Expression={$_.principalType}}, `
                @{Name='PrincipalName'; Expression={$_.principalName}}, `
                @{Name='Condition'; Expression={$_.condition}} `
                | Sort-Object Scope, RoleDefinitionName
            
            $csvPath = Join-Path $rbacPath "subscription_assignments.csv"
            $csvData | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
            
            Write-Log "SUCCESS" "Subscription RBAC exported" @{
                AssignmentCount = $subAssignments.Count
            }
            
            return $subAssignments
        }
        else {
            Write-Log "INFO" "No subscription-level role assignments found"
            return @()
        }
    }
    catch {
        Write-Log "WARN" "Failed to export subscription RBAC" @{ Error = $_.Exception.Message }
        return @()
    }
}

function Export-ResourceGroupRBAC {
    param(
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting resource group RBAC" @{
        ResourceGroup = $ResourceGroupName
        SubscriptionId = $SubscriptionId
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $rbacPath = Join-Path $OutputPath "rbac"
    if (-not (Test-Path $rbacPath)) {
        New-Item -ItemType Directory -Path $rbacPath -Force | Out-Null
    }
    
    $rgScope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName"
    
    try {
        $assignments = az role assignment list --all --scope $rgScope --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $assignments) {
            Save-JsonFile -Path (Join-Path $rbacPath "rg_assignments.json") -Data $assignments -RedactSecrets
            
            # Create CSV summary
            $csvData = $assignments | Select-Object `
                @{Name='Scope'; Expression={$_.scope}}, `
                @{Name='RoleDefinitionName'; Expression={$_.roleDefinitionName}}, `
                @{Name='PrincipalType'; Expression={$_.principalType}}, `
                @{Name='PrincipalName'; Expression={$_.principalName}}, `
                @{Name='Condition'; Expression={$_.condition}} `
                | Sort-Object RoleDefinitionName, PrincipalName
            
            $csvPath = Join-Path $rbacPath "rg_assignments.csv"
            $csvData | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
            
            Write-Log "SUCCESS" "Resource group RBAC exported" @{
                ResourceGroup = $ResourceGroupName
                AssignmentCount = $assignments.Count
            }
            
            return $assignments
        }
        else {
            Write-Log "INFO" "No resource group role assignments found" @{ ResourceGroup = $ResourceGroupName }
            return @()
        }
    }
    catch {
        Write-Log "WARN" "Failed to export resource group RBAC" @{
            ResourceGroup = $ResourceGroupName
            Error = $_.Exception.Message
        }
        return @()
    }
}

# Functions available when dot-sourced

