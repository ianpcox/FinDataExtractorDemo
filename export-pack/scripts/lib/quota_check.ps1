# Quota and SKU Feasibility Check Generator
# Generates checklist for validating quotas and SKU availability in target region

. "$PSScriptRoot\common.ps1"

function Export-QuotaCheck {
    param(
        [string]$SubscriptionId,
        [string]$OutputPath,
        [array]$Resources = @()
    )
    
    Write-Log "INFO" "Generating quota/SKU feasibility checklist" @{ SubscriptionId = $SubscriptionId }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $quotaPath = Join-Path $OutputPath "quota_sku_checklist.md"
    
    # Analyze resources to extract SKUs and types
    $resourceTypes = @{}
    
    foreach ($resource in $Resources) {
        $type = $resource.type
        if (-not $resourceTypes.ContainsKey($type)) {
            $resourceTypes[$type] = @()
        }
        
        $skuInfo = @{
            Name = $resource.name
            Location = $resource.location
            SKU = $null
            Size = $null
        }
        
        # Extract SKU/size based on resource type
        if ($resource.sku) {
            $skuInfo.SKU = $resource.sku
        }
        if ($resource.properties.hardwareProfile) {
            $skuInfo.Size = $resource.properties.hardwareProfile.vmSize
        }
        if ($resource.properties.currentServiceObjectiveName) {
            $skuInfo.SKU = $resource.properties.currentServiceObjectiveName
        }
        if ($resource.properties.sku) {
            $skuInfo.SKU = $resource.properties.sku
        }
        
        $resourceTypes[$type] += $skuInfo
    }
    
    # Generate checklist
    $checklist = Generate-QuotaChecklistMarkdown -ResourceTypes $resourceTypes -SubscriptionId $SubscriptionId
    
    if (-not (Test-Path (Split-Path $quotaPath -Parent))) {
        New-Item -ItemType Directory -Path (Split-Path $quotaPath -Parent) -Force | Out-Null
    }
    
    Set-Content -Path $quotaPath -Value $checklist -Encoding UTF8
    Write-Log "SUCCESS" "Quota/SKU checklist generated" @{ Path = $quotaPath }
    
    return $quotaPath
}

function Generate-QuotaChecklistMarkdown {
    param(
        [hashtable]$ResourceTypes,
        [string]$SubscriptionId
    )
    
    $md = @"
# Quota and SKU Feasibility Checklist

**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  
**Source Subscription:** $SubscriptionId

## Overview

This checklist helps validate that target region/tenant has sufficient quotas and SKU availability for all exported resources.

**Target Region:** [ENTER TARGET REGION HERE]  
**Target Subscription:** [ENTER TARGET SUBSCRIPTION ID HERE]

---

## Instructions

1. Set target region and subscription above
2. Run the provided Azure CLI commands for each resource type
3. Verify quotas are sufficient
4. Verify SKUs are available in target region
5. Note any required changes (SKU substitutions, quota increases)

---

## Resource Type Checklist

"@
    
    # VM quotas
    if ($ResourceTypes.ContainsKey("Microsoft.Compute/virtualMachines")) {
        $md += @"
### Virtual Machines

**Resources Found:** $($ResourceTypes["Microsoft.Compute/virtualMachines"].Count)

**Check VM quotas:**
``````powershell
az vm list-usage --location <TARGET_REGION> --output table
``````

**Check available VM sizes:**
``````powershell
az vm list-sizes --location <TARGET_REGION> --output table
``````

**Resources to validate:**
"@
        foreach ($vm in $ResourceTypes["Microsoft.Compute/virtualMachines"]) {
            $size = if ($vm.Size) { $vm.Size } else { "Unknown" }
            $md += @"
- **$($vm.Name)** - Size: $size - Location: $($vm.Location)
"@
        }
        $md += "`n"
    }
    
    # Storage accounts
    if ($ResourceTypes.ContainsKey("Microsoft.Storage/storageAccounts")) {
        $md += @"
### Storage Accounts

**Resources Found:** $($ResourceTypes["Microsoft.Storage/storageAccounts"].Count)

**Check storage account quotas:**
``````powershell
az storage account list --query "[].{Name:name, SKU:sku.name, Location:location}" --output table
``````

**Note:** Storage account limits are typically 250 per subscription per region.

**Resources to validate:**
"@
        foreach ($sa in $ResourceTypes["Microsoft.Storage/storageAccounts"]) {
            $sku = if ($sa.SKU) { $sa.SKU.name } else { "Standard_LRS" }
            $md += @"
- **$($sa.Name)** - SKU: $sku - Location: $($sa.Location)
"@
        }
        $md += "`n"
    }
    
    # SQL Databases
    if ($ResourceTypes.ContainsKey("Microsoft.Sql/servers/databases")) {
        $md += @"
### SQL Databases

**Resources Found:** $($ResourceTypes["Microsoft.Sql/servers/databases"].Count)

**Check SQL service objectives:**
``````powershell
az sql db list-editions --location <TARGET_REGION> --output table
``````

**Resources to validate:**
"@
        foreach ($db in $ResourceTypes["Microsoft.Sql/servers/databases"]) {
            $sku = if ($db.SKU) { $db.SKU } else { "Unknown" }
            $md += @"
- **$($db.Name)** - Service Objective: $sku - Location: $($db.Location)
"@
        }
        $md += "`n"
    }
    
    # AKS
    if ($ResourceTypes.ContainsKey("Microsoft.ContainerService/managedClusters")) {
        $md += @"
### AKS Clusters

**Resources Found:** $($ResourceTypes["Microsoft.ContainerService/managedClusters"].Count)

**Check AKS quotas:**
``````powershell
az vm list-sizes --location <TARGET_REGION> --query "[?contains(name, 'Standard_DS')]" --output table
``````

**Resources to validate:**
"@
        foreach ($aks in $ResourceTypes["Microsoft.ContainerService/managedClusters"]) {
            $md += @"
- **$($aks.Name)** - Location: $($aks.Location)
"@
        }
        $md += "`n"
    }
    
    # Generic resource types
    foreach ($type in $ResourceTypes.Keys) {
        if ($type -notin @("Microsoft.Compute/virtualMachines", "Microsoft.Storage/storageAccounts", 
                           "Microsoft.Sql/servers/databases", "Microsoft.ContainerService/managedClusters")) {
            $typeName = ($type -split '/')[-1]
            $md += @"
### $typeName

**Resources Found:** $($ResourceTypes[$type].Count)

**Check availability:**
``````powershell
# Review Azure documentation for $type quotas
az provider show --namespace "$(($type -split '/')[0])" --query "resourceTypes[?resourceType=='$(($type -split '/')[1])']" --output table
``````

**Resources to validate:**
"@
            foreach ($res in $ResourceTypes[$type]) {
                $md += @"
- **$($res.Name)** - Location: $($res.Location)
"@
            }
            $md += "`n"
        }
    }
    
    $md += @"
---

## General Quota Checks

### Subscription-Level Quotas

``````powershell
# Check all quotas for target region
az vm list-usage --location <TARGET_REGION> --output table
az network list-usages --location <TARGET_REGION> --output table
``````

### Request Quota Increases

If quotas are insufficient, request increases via:
- Azure Portal: Subscriptions → Usage + quotas
- Azure Support: Create support request for quota increase

---

## Notes

- Some SKUs may not be available in all regions
- Quotas vary by subscription type (Pay-as-you-go, Enterprise, etc.)
- Some resources have subscription-level limits, others are regional
- Review [Azure subscription and service limits](https://docs.microsoft.com/azure/azure-resource-manager/management/azure-subscription-service-limits)

---

**Last Updated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
"@
    
    return $md
}

# Functions available when dot-sourced

