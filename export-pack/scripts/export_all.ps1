# Azure Export & Rebuild Pack - Main Orchestration Script
# Exports Azure resources for handoff to NetOps team

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string[]]$Subscriptions = @(),
    
    [Parameter(Mandatory=$false)]
    [switch]$AllSubscriptions,
    
    [Parameter(Mandatory=$false)]
    [string[]]$ResourceGroups = @(),
    
    [Parameter(Mandatory=$false)]
    [switch]$IncludeAksWorkloads = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$IncludeSearchSchema = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$IncludeOpenAiDeployments = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$IncludeSqlConfig = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$IncludeStorageInventory = $true,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputRoot = "./out",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseAdminKubeconfig = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$ExportKeyVaultSecrets = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$ExportAADStubs = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$ExportNetworkGaps = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$ExportQuotaCheck = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$ExportWorkbooks = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$ExportClassicReport = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

# Import common functions
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. "$scriptRoot\lib\common.ps1"

# Initialize
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
if (-not $DryRun) {
    $outputPath = Join-Path (Resolve-Path $OutputRoot).Path $timestamp
    if (-not (Test-Path $outputPath)) {
        New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
    }
    Initialize-Logging -OutputRoot $outputPath -Timestamp $timestamp
} else {
    $outputPath = Join-Path $OutputRoot $timestamp
}

Write-Log "INFO" "Azure Export Pack - Starting export" @{
    Timestamp = $timestamp
    OutputPath = $outputPath
    DryRun = $DryRun
    ExportKeyVaultSecrets = $ExportKeyVaultSecrets
    ExportAADStubs = $ExportAADStubs
    ExportNetworkGaps = $ExportNetworkGaps
    ExportQuotaCheck = $ExportQuotaCheck
    ExportWorkbooks = $ExportWorkbooks
    ExportClassicReport = $ExportClassicReport
}

# Check prerequisites
if (-not $DryRun) {
    $tools = Test-Prerequisites
    if (-not $tools) {
        throw "Prerequisites check failed"
    }
}

# Import all exporter modules
. "$scriptRoot\lib\azure_inventory.ps1"
. "$scriptRoot\lib\arm_export.ps1"
. "$scriptRoot\lib\rbac_export.ps1"
. "$scriptRoot\lib\aks_export.ps1"
. "$scriptRoot\lib\search_export.ps1"
. "$scriptRoot\lib\openai_export.ps1"
. "$scriptRoot\lib\sql_export.ps1"
. "$scriptRoot\lib\storage_export.ps1"
. "$scriptRoot\lib\redis_export.ps1"
. "$scriptRoot\lib\monitor_export.ps1"
. "$scriptRoot\lib\keyvault_export.ps1"
. "$scriptRoot\lib\aad_export.ps1"
. "$scriptRoot\lib\network_gaps.ps1"
. "$scriptRoot\lib\quota_check.ps1"
. "$scriptRoot\lib\classic_detection.ps1"
. "$scriptRoot\lib\parity_checklist.ps1"

# Determine subscriptions to export
$subscriptionsToExport = @()

if ($AllSubscriptions) {
    Write-Log "INFO" "Exporting all subscriptions"
    $allSubs = az account list --output json 2>&1 | ConvertFrom-Json
    $subscriptionsToExport = $allSubs | ForEach-Object { $_.id }
}
elseif ($Subscriptions.Count -gt 0) {
    foreach ($sub in $Subscriptions) {
        $subId = Get-AzureSubscriptionId -SubscriptionNameOrId $sub
        $subscriptionsToExport += $subId
    }
}
else {
    # Default: current subscription
    $currentSub = az account show --output json 2>&1 | ConvertFrom-Json
    $subscriptionsToExport = @($currentSub.id)
    Write-Log "INFO" "No subscriptions specified, using current subscription" @{
        SubscriptionId = $currentSub.id
        SubscriptionName = $currentSub.name
    }
}

Write-Log "INFO" "Subscriptions to export" @{
    Count = $subscriptionsToExport.Count
    Subscriptions = ($subscriptionsToExport -join ", ")
}

$exportSummary = @{
    Timestamp = $timestamp
    Subscriptions = @()
    TotalResourceGroups = 0
    TotalResources = 0
    ServicesExported = @{}
    Errors = @()
    Warnings = @()
}

# Process each subscription
foreach ($subId in $subscriptionsToExport) {
    try {
        Set-AzureSubscription -SubscriptionId $subId
        
        $subInfo = az account show --subscription $subId --output json 2>&1 | ConvertFrom-Json
        $subName = $subInfo.name
        $safeSubName = Get-SafeFileName $subName
        
        Write-Log "INFO" "Processing subscription" @{
            SubscriptionId = $subId
            SubscriptionName = $subName
        }
        
        $subOutputPath = Get-ExportPath -OutputRoot $outputPath -Timestamp $timestamp `
            -SubscriptionNameOrId "$safeSubName ($subId)"
        
        # Export subscription-level inventory and RBAC
        if (-not $DryRun) {
            Export-SubscriptionInventory -SubscriptionId $subId -SubscriptionName $subName -OutputPath $subOutputPath
            Export-SubscriptionRBAC -SubscriptionId $subId -OutputPath $subOutputPath
            
            # AAD stubs (subscription-level, opt-in)
            if ($ExportAADStubs) {
                Export-AADStubs -SubscriptionId $subId -OutputPath $subOutputPath
            }
            
            # Network gaps (subscription-level, opt-in)
            if ($ExportNetworkGaps) {
                Export-NetworkGaps -SubscriptionId $subId -OutputPath $subOutputPath
            }
            
            # Quota check (subscription-level, opt-in)
            if ($ExportQuotaCheck) {
                # Collect all resources from all RGs in subscription
                $allResources = @()
                foreach ($rg in $resourceGroups) {
                    $rgResources = Get-AzureResources -ResourceGroupName $rg.name -SubscriptionId $subId
                    if ($rgResources) {
                        $allResources += $rgResources
                    }
                }
                if ($allResources.Count -gt 0) {
                    Export-QuotaCheck -SubscriptionId $subId -OutputPath $subOutputPath -Resources $allResources
                }
            }
        }
        
        # Get resource groups
        $resourceGroups = Get-AzureResourceGroups -SubscriptionId $subId
        
        # Filter resource groups if specified
        if ($ResourceGroups.Count -gt 0) {
            $resourceGroups = $resourceGroups | Where-Object { $ResourceGroups -contains $_.name }
            Write-Log "INFO" "Filtered resource groups" @{
                Requested = ($ResourceGroups -join ", ")
                Found = ($resourceGroups | ForEach-Object { $_.name }) -join ", "
            }
        }
        
        $subSummary = @{
            SubscriptionId = $subId
            SubscriptionName = $subName
            ResourceGroups = @()
        }
        
        # Process each resource group
        foreach ($rg in $resourceGroups) {
            try {
                $rgName = $rg.name
                Write-Log "INFO" "Processing resource group" @{
                    ResourceGroup = $rgName
                    Subscription = $subName
                }
                
                $rgOutputPath = Get-ExportPath -OutputRoot $outputPath -Timestamp $timestamp `
                    -SubscriptionNameOrId "$safeSubName ($subId)" -ResourceGroupName $rgName
                
                # Export inventory
                if (-not $DryRun) {
                    $inventory = Export-ResourceGroupInventory -ResourceGroupName $rgName `
                        -SubscriptionId $subId -OutputPath $rgOutputPath
                    
                    $exportSummary.TotalResourceGroups++
                    if ($inventory.Resources) {
                        $exportSummary.TotalResources += $inventory.Resources.Count
                    }
                }
                
                # Export ARM template and decompile to Bicep
                if (-not $DryRun) {
                    $armFile = Export-ARMTemplate -ResourceGroupName $rgName `
                        -SubscriptionId $subId -OutputPath $rgOutputPath
                    
                    if ($armFile) {
                        Decompile-ToBicep -ArmTemplatePath $armFile -OutputPath $rgOutputPath
                    }
                    
                    Export-Deployments -ResourceGroupName $rgName `
                        -SubscriptionId $subId -OutputPath $rgOutputPath
                }
                
                # Export RBAC
                if (-not $DryRun) {
                    Export-ResourceGroupRBAC -ResourceGroupName $rgName `
                        -SubscriptionId $subId -OutputPath $rgOutputPath
                }
                
                # Export service-specific resources
                if (-not $DryRun -and $inventory.IdentifiedServices) {
                    $services = $inventory.IdentifiedServices
                    
                    # AKS
                    if ($services.AKS) {
                        foreach ($aks in $services.AKS) {
                            $aksName = ($aks.id -split '/')[-1]
                            Export-AKSCluster -ClusterName $aksName -ResourceGroupName $rgName `
                                -SubscriptionId $subId -OutputPath $rgOutputPath `
                                -IncludeWorkloads:$IncludeAksWorkloads -UseAdminKubeconfig:$UseAdminKubeconfig
                            
                            if (-not $exportSummary.ServicesExported.ContainsKey("AKS")) {
                                $exportSummary.ServicesExported["AKS"] = 0
                            }
                            $exportSummary.ServicesExported["AKS"]++
                        }
                    }
                    
                    # Search
                    if ($services.Search) {
                        foreach ($search in $services.Search) {
                            $searchName = ($search.id -split '/')[-1]
                            Export-SearchService -SearchServiceName $searchName `
                                -ResourceGroupName $rgName -SubscriptionId $subId `
                                -OutputPath $rgOutputPath -IncludeSchema:$IncludeSearchSchema
                            
                            if (-not $exportSummary.ServicesExported.ContainsKey("Search")) {
                                $exportSummary.ServicesExported["Search"] = 0
                            }
                            $exportSummary.ServicesExported["Search"]++
                        }
                    }
                    
                    # OpenAI / Cognitive Services
                    if ($services.CognitiveServices) {
                        foreach ($cog in $services.CognitiveServices) {
                            $cogName = ($cog.id -split '/')[-1]
                            Export-OpenAIService -AccountName $cogName `
                                -ResourceGroupName $rgName -SubscriptionId $subId `
                                -OutputPath $rgOutputPath -IncludeDeployments:$IncludeOpenAiDeployments
                            
                            if (-not $exportSummary.ServicesExported.ContainsKey("OpenAI")) {
                                $exportSummary.ServicesExported["OpenAI"] = 0
                            }
                            $exportSummary.ServicesExported["OpenAI"]++
                        }
                    }
                    
                    # SQL Server
                    if ($services.SQLServer) {
                        foreach ($sql in $services.SQLServer) {
                            $sqlName = ($sql.id -split '/')[-1]
                            Export-SQLServer -ServerName $sqlName `
                                -ResourceGroupName $rgName -SubscriptionId $subId `
                                -OutputPath $rgOutputPath
                            
                            if (-not $exportSummary.ServicesExported.ContainsKey("SQL")) {
                                $exportSummary.ServicesExported["SQL"] = 0
                            }
                            $exportSummary.ServicesExported["SQL"]++
                        }
                    }
                    
                    # Storage
                    if ($services.Storage -and $IncludeStorageInventory) {
                        foreach ($storage in $services.Storage) {
                            $storageName = ($storage.id -split '/')[-1]
                            Export-StorageAccount -StorageAccountName $storageName `
                                -ResourceGroupName $rgName -SubscriptionId $subId `
                                -OutputPath $rgOutputPath
                            
                            if (-not $exportSummary.ServicesExported.ContainsKey("Storage")) {
                                $exportSummary.ServicesExported["Storage"] = 0
                            }
                            $exportSummary.ServicesExported["Storage"]++
                        }
                    }
                    
                    # Redis
                    if ($services.Redis) {
                        foreach ($redis in $services.Redis) {
                            $redisName = ($redis.id -split '/')[-1]
                            Export-RedisCache -CacheName $redisName `
                                -ResourceGroupName $rgName -SubscriptionId $subId `
                                -OutputPath $rgOutputPath
                            
                            if (-not $exportSummary.ServicesExported.ContainsKey("Redis")) {
                                $exportSummary.ServicesExported["Redis"] = 0
                            }
                            $exportSummary.ServicesExported["Redis"]++
                        }
                    }
                    
                    # Monitor
                    if ($services.LogAnalytics -or $services.Monitor -or $services.Insights) {
                        Export-MonitorResources -ResourceGroupName $rgName `
                            -SubscriptionId $subId -OutputPath $rgOutputPath
                        
                        # Export workbooks if requested
                        if ($ExportWorkbooks) {
                            if ($services.LogAnalytics) {
                                foreach ($ws in $services.LogAnalytics) {
                                    $wsName = ($ws.id -split '/')[-1]
                                    Export-MonitorWorkbooks -WorkspaceName $wsName `
                                        -ResourceGroupName $rgName -SubscriptionId $subId -OutputPath $rgOutputPath
                                }
                            }
                        }
                        
                        if (-not $exportSummary.ServicesExported.ContainsKey("Monitor")) {
                            $exportSummary.ServicesExported["Monitor"] = 0
                        }
                        $exportSummary.ServicesExported["Monitor"]++
                    }
                    
                    # Key Vault secrets (opt-in)
                    if ($ExportKeyVaultSecrets -and $services.KeyVault) {
                        foreach ($kv in $services.KeyVault) {
                            $kvName = ($kv.id -split '/')[-1]
                            Export-KeyVaultSecrets -VaultName $kvName `
                                -ResourceGroupName $rgName -SubscriptionId $subId -OutputPath $rgOutputPath
                            
                            if (-not $exportSummary.ServicesExported.ContainsKey("KeyVault")) {
                                $exportSummary.ServicesExported["KeyVault"] = 0
                            }
                            $exportSummary.ServicesExported["KeyVault"]++
                        }
                    }
                    
                    # Classic resource detection (opt-in, per RG)
                    if ($ExportClassicReport -and $inventory.Resources) {
                        Export-ClassicResources -SubscriptionId $subId `
                            -OutputPath $rgOutputPath -Resources $inventory.Resources
                    }
                }
                
                $subSummary.ResourceGroups += @{
                    Name = $rgName
                    Location = $rg.location
                    Status = "Exported"
                }
            }
            catch {
                $errorMsg = "Failed to export resource group $($rg.name): $($_.Exception.Message)"
                Write-Log "ERROR" $errorMsg
                $exportSummary.Errors += $errorMsg
                $subSummary.ResourceGroups += @{
                    Name = $rg.name
                    Status = "Failed"
                    Error = $_.Exception.Message
                }
            }
        }
        
        $exportSummary.Subscriptions += $subSummary
    }
    catch {
        $errorMsg = "Failed to process subscription $subId : $($_.Exception.Message)"
        Write-Log "ERROR" $errorMsg
        $exportSummary.Errors += $errorMsg
    }
}

# Save export summary and generate parity checklist
if (-not $DryRun) {
    $summaryPath = Join-Path $outputPath "export_summary.json"
    Save-JsonFile -Path $summaryPath -Data $exportSummary
    
    # Generate environment parity checklist
    $options = @{
        ExportKeyVaultSecrets = $ExportKeyVaultSecrets
        ExportAADStubs = $ExportAADStubs
        ExportNetworkGaps = $ExportNetworkGaps
        ExportQuotaCheck = $ExportQuotaCheck
        ExportWorkbooks = $ExportWorkbooks
        ExportClassicReport = $ExportClassicReport
    }
    Generate-ParityChecklist -ExportSummary $exportSummary -OutputPath $outputPath -Options $options
    
    Write-Log "SUCCESS" "Export completed" @{
        TotalSubscriptions = $exportSummary.Subscriptions.Count
        TotalResourceGroups = $exportSummary.TotalResourceGroups
        TotalResources = $exportSummary.TotalResources
        ServicesExported = ($exportSummary.ServicesExported.Keys -join ", ")
        ErrorCount = $exportSummary.Errors.Count
    }
    
    Stop-Logging
}
else {
    Write-Log "INFO" "Dry run completed - no files were written"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Export Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Subscriptions: $($exportSummary.Subscriptions.Count)" -ForegroundColor White
Write-Host "Resource Groups: $($exportSummary.TotalResourceGroups)" -ForegroundColor White
Write-Host "Total Resources: $($exportSummary.TotalResources)" -ForegroundColor White
Write-Host "Services Exported: $($exportSummary.ServicesExported.Keys.Count)" -ForegroundColor White
if ($exportSummary.Errors.Count -gt 0) {
    Write-Host "Errors: $($exportSummary.Errors.Count)" -ForegroundColor Red
}
Write-Host ""
if (-not $DryRun) {
    Write-Host "Output location: $outputPath" -ForegroundColor Green
    Write-Host "Review the export_summary.json file for detailed results." -ForegroundColor Yellow
}

