# Classic Resource Detection
# Detects classic/ASM resources that cannot be exported via ARM

. "$PSScriptRoot\common.ps1"

function Export-ClassicResources {
    param(
        [string]$SubscriptionId,
        [string]$OutputPath,
        [array]$Resources = @()
    )
    
    Write-Log "INFO" "Detecting classic/ASM resources" @{ SubscriptionId = $SubscriptionId }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $classicResources = @()
    
    # Detect classic resources by API version or type
    foreach ($resource in $Resources) {
        $isClassic = $false
        $reason = ""
        
        # Check API version for classic indicators
        if ($resource.apiVersion) {
            if ($resource.apiVersion -like "*classic*" -or 
                $resource.apiVersion -like "2014-*" -or
                $resource.apiVersion -like "2015-*") {
                $isClassic = $true
                $reason = "Classic API version: $($resource.apiVersion)"
            }
        }
        
        # Check resource type for known classic types
        $classicTypes = @(
            "Microsoft.ClassicCompute",
            "Microsoft.ClassicStorage",
            "Microsoft.ClassicNetwork"
        )
        
        foreach ($classicType in $classicTypes) {
            if ($resource.type -like "$classicType/*") {
                $isClassic = $true
                $reason = "Classic resource type: $($resource.type)"
                break
            }
        }
        
        if ($isClassic) {
            $classicResources += @{
                Name = $resource.name
                Type = $resource.type
                Location = $resource.location
                ResourceGroup = $resource.resourceGroup
                Reason = $reason
                SuggestedARMEquivalent = Get-SuggestedARMEquivalent -ResourceType $resource.type
            }
        }
    }
    
    if ($classicResources.Count -gt 0) {
        Save-JsonFile -Path (Join-Path $OutputPath "classic_resources.json") -Data $classicResources -RedactSecrets
        
        # Generate report
        Generate-ClassicResourcesReport -Resources $classicResources -OutputPath $OutputPath
        
        Write-Log "SUCCESS" "Classic resources detected" @{ Count = $classicResources.Count }
    }
    else {
        Write-Log "INFO" "No classic resources detected"
    }
    
    return $classicResources
}

function Get-SuggestedARMEquivalent {
    param([string]$ResourceType)
    
    $equivalents = @{
        "Microsoft.ClassicCompute/virtualMachines" = "Microsoft.Compute/virtualMachines"
        "Microsoft.ClassicCompute/domainNames" = "Microsoft.Compute/virtualMachines (with public IP)"
        "Microsoft.ClassicStorage/storageAccounts" = "Microsoft.Storage/storageAccounts"
        "Microsoft.ClassicNetwork/virtualNetworks" = "Microsoft.Network/virtualNetworks"
        "Microsoft.ClassicNetwork/reservedIps" = "Microsoft.Network/publicIPAddresses"
    }
    
    foreach ($key in $equivalents.Keys) {
        if ($ResourceType -like "$key*") {
            return $equivalents[$key]
        }
    }
    
    return "Review Azure migration documentation"
}

function Generate-ClassicResourcesReport {
    param(
        [array]$Resources,
        [string]$OutputPath
    )
    
    $reportPath = Join-Path $OutputPath "classic_resources_report.md"
    
    $md = @"
# Classic Resource Detection Report

**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

## Overview

This report lists classic/ASM (Azure Service Manager) resources that cannot be exported via ARM templates. These resources require manual migration or recreation using ARM/Bicep equivalents.

**Total Classic Resources Found:** $($Resources.Count)

---

## Classic Resources

"@
    
    foreach ($resource in $Resources) {
        $md += @"
### $($resource.Name)

- **Type:** $($resource.Type)
- **Location:** $($resource.Location)
- **Resource Group:** $($resource.ResourceGroup)
- **Detection Reason:** $($resource.Reason)
- **Suggested ARM Equivalent:** $($resource.SuggestedARMEquivalent)

**Migration Steps:**
1. Review ARM equivalent resource type
2. Export configuration manually (if possible)
3. Recreate using ARM/Bicep template
4. Migrate data/configuration
5. Update application references

**Documentation:**
- [Migrate Classic resources to ARM](https://docs.microsoft.com/azure/virtual-machines/migration-classic-resource-manager-overview)
- [Classic to Resource Manager migration](https://docs.microsoft.com/azure/virtual-machines/migration-classic-resource-manager-ps)

---

"@
    }
    
    $md += @"
## Summary by Type

"@
    
    $byType = $Resources | Group-Object -Property Type
    foreach ($group in $byType) {
        $md += @"
- **$($group.Name):** $($group.Count) resources
"@
    }
    
    $md += @"

---

## Recommendations

1. **Plan Migration:** Classic resources should be migrated to ARM before environment rebuild
2. **Manual Export:** Document configuration manually for classic resources
3. **ARM Equivalents:** Use suggested ARM equivalents for recreation
4. **Testing:** Test migration in non-production environment first
5. **Timeline:** Classic resources may be deprecated - plan migration accordingly

---

**Note:** Classic resources are being phased out. Consider migrating to ARM equivalents before rebuilding in target tenant.

**Last Updated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
"@
    
    Set-Content -Path $reportPath -Value $md -Encoding UTF8
    Write-Log "INFO" "Classic resources report generated" @{ Path = $reportPath }
}

# Functions available when dot-sourced

