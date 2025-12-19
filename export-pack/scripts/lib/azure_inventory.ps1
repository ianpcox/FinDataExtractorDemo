# Azure Resource Inventory Exporter
# Exports comprehensive resource inventories by subscription and resource group

. "$PSScriptRoot\common.ps1"

function Export-SubscriptionInventory {
    param(
        [string]$SubscriptionId,
        [string]$SubscriptionName,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting subscription inventory" @{
        SubscriptionId = $SubscriptionId
        SubscriptionName = $SubscriptionName
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $metadata = @{
        SubscriptionId = $SubscriptionId
        SubscriptionName = $SubscriptionName
        ExportTimestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ")
    }
    
    # Get subscription details
    try {
        $account = az account show --output json 2>&1 | ConvertFrom-Json
        $metadata.Account = Remove-SecretsFromObject $account
    }
    catch {
        Write-Log "WARN" "Failed to get account details" @{ Error = $_.Exception.Message }
    }
    
    # Get registered providers
    try {
        $providers = az provider list --output json 2>&1 | ConvertFrom-Json
        $metadata.RegisteredProviders = $providers | Where-Object { $_.RegistrationState -eq "Registered" } | 
            Select-Object Namespace, RegistrationState
    }
    catch {
        Write-Log "WARN" "Failed to list providers" @{ Error = $_.Exception.Message }
    }
    
    # Get policy assignments (subscription scope)
    try {
        $policies = az policy assignment list --output json 2>&1 | ConvertFrom-Json
        $metadata.PolicyAssignments = $policies | Select-Object Name, DisplayName, PolicyDefinitionId, Scope
    }
    catch {
        Write-Log "WARN" "Failed to list policy assignments" @{ Error = $_.Exception.Message }
    }
    
    # Get resource groups
    try {
        $resourceGroups = Get-AzureResourceGroups -SubscriptionId $SubscriptionId
        $metadata.ResourceGroupCount = $resourceGroups.Count
        $metadata.ResourceGroups = $resourceGroups | Select-Object Name, Location, Tags, ProvisioningState
    }
    catch {
        Write-Log "WARN" "Failed to list resource groups" @{ Error = $_.Exception.Message }
    }
    
    # Save metadata
    $metadataPath = Join-Path $OutputPath "metadata"
    if (-not (Test-Path $metadataPath)) {
        New-Item -ItemType Directory -Path $metadataPath -Force | Out-Null
    }
    
    Save-JsonFile -Path (Join-Path $metadataPath "subscription_metadata.json") -Data $metadata -RedactSecrets
    
    return $metadata
}

function Export-ResourceGroupInventory {
    param(
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting resource group inventory" @{
        ResourceGroup = $ResourceGroupName
        SubscriptionId = $SubscriptionId
    }
    
    $inventoryPath = Join-Path $OutputPath "inventory"
    if (-not (Test-Path $inventoryPath)) {
        New-Item -ItemType Directory -Path $inventoryPath -Force | Out-Null
    }
    
    # Get all resources in the RG
    $resources = Get-AzureResources -ResourceGroupName $ResourceGroupName -SubscriptionId $SubscriptionId
    
    if ($resources.Count -eq 0) {
        Write-Log "WARN" "No resources found in resource group" @{ ResourceGroup = $ResourceGroupName }
        return
    }
    
    # Save full JSON inventory
    Save-JsonFile -Path (Join-Path $inventoryPath "resources.json") -Data $resources -RedactSecrets
    
    # Create CSV summary
    $csvData = $resources | Select-Object `
        @{Name='Name'; Expression={$_.name}}, `
        @{Name='Type'; Expression={$_.type}}, `
        @{Name='Location'; Expression={$_.location}}, `
        @{Name='ProvisioningState'; Expression={$_.properties.provisioningState}}, `
        @{Name='Tags'; Expression={($_.tags | ConvertTo-Json -Compress)}} `
        | Sort-Object Type, Name
    
    $csvPath = Join-Path $inventoryPath "resources.csv"
    $csvData | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
    Write-Log "INFO" "Saved CSV inventory" @{ Path = $csvPath }
    
    # Create summary by resource type
    $typeSummary = $resources | Group-Object -Property type | 
        Select-Object @{Name='ResourceType'; Expression={$_.Name}}, Count,
        @{Name='Resources'; Expression={$_.Group | Select-Object -ExpandProperty name}}
    
    Save-JsonFile -Path (Join-Path $inventoryPath "resource_type_summary.json") -Data $typeSummary
    
    # Identify special service types
    $serviceTypes = @{
        AKS = "Microsoft.ContainerService/managedClusters"
        ACR = "Microsoft.ContainerRegistry/registries"
        Search = "Microsoft.Search/searchServices"
        CognitiveServices = "Microsoft.CognitiveServices/accounts"
        SQLServer = "Microsoft.Sql/servers"
        SQLDatabase = "Microsoft.Sql/servers/databases"
        Redis = "Microsoft.Cache/Redis"
        Storage = "Microsoft.Storage/storageAccounts"
        LogAnalytics = "Microsoft.OperationalInsights/workspaces"
        Monitor = "Microsoft.Monitor/accounts"
        Insights = "Microsoft.Insights/components"
    }
    
    $identifiedServices = @{}
    foreach ($serviceType in $serviceTypes.Keys) {
        $matching = $resources | Where-Object { $_.type -eq $serviceTypes[$serviceType] }
        if ($matching) {
            $identifiedServices[$serviceType] = $matching | Select-Object name, id, location
        }
    }
    
    Save-JsonFile -Path (Join-Path $inventoryPath "identified_services.json") -Data $identifiedServices
    
    Write-Log "SUCCESS" "Resource group inventory exported" @{
        ResourceGroup = $ResourceGroupName
        ResourceCount = $resources.Count
        ServiceTypes = ($identifiedServices.Keys -join ", ")
    }
    
    return @{
        Resources = $resources
        IdentifiedServices = $identifiedServices
    }
}

# Functions available when dot-sourced

