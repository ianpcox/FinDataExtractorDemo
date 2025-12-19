# Azure AI Search Exporter
# Exports Search service configuration and optionally schemas (requires operator input for admin key)

. "$PSScriptRoot\common.ps1"

function Export-SearchService {
    param(
        [string]$SearchServiceName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath,
        [switch]$IncludeSchema
    )
    
    Write-Log "INFO" "Exporting Azure AI Search service" @{
        SearchServiceName = $SearchServiceName
        ResourceGroup = $ResourceGroupName
        SubscriptionId = $SubscriptionId
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $searchPath = Join-Path $OutputPath "search" (Get-SafeFileName $SearchServiceName)
    if (-not (Test-Path $searchPath)) {
        New-Item -ItemType Directory -Path $searchPath -Force | Out-Null
    }
    
    # Export service properties (ARM level)
    try {
        $service = az resource show `
            --name $SearchServiceName `
            --resource-group $ResourceGroupName `
            --resource-type "Microsoft.Search/searchServices" `
            --output json 2>&1 | ConvertFrom-Json
        
        if ($LASTEXITCODE -eq 0) {
            $redacted = Remove-SecretsFromObject $service
            Save-JsonFile -Path (Join-Path $searchPath "service.json") -Data $redacted -RedactSecrets
            Write-Log "SUCCESS" "Search service configuration exported"
        }
        else {
            Write-Log "ERROR" "Failed to get Search service details"
            return
        }
    }
    catch {
        Write-Log "ERROR" "Failed to export Search service" @{ Error = $_.Exception.Message }
        return
    }
    
    # Get service endpoint
    $endpoint = "https://$SearchServiceName.search.windows.net"
    
    # Export schema if requested
    if ($IncludeSchema) {
        Export-SearchSchema -SearchServiceName $SearchServiceName -Endpoint $endpoint -OutputPath $searchPath
    }
    else {
        # Generate operator-assisted script
        Generate-SearchSchemaScript -SearchServiceName $SearchServiceName -Endpoint $endpoint -OutputPath $searchPath
    }
}

function Export-SearchSchema {
    param(
        [string]$SearchServiceName,
        [string]$Endpoint,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting Search schema (requires admin key)" @{ SearchService = $SearchServiceName }
    
    # Prompt for admin key (secure)
    $adminKey = Read-Host "Enter Azure AI Search admin key for $SearchServiceName (input will be hidden)" -AsSecureString
    $adminKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminKey)
    )
    
    if ([string]::IsNullOrWhiteSpace($adminKeyPlain)) {
        Write-Log "WARN" "No admin key provided, skipping schema export"
        Generate-SearchSchemaScript -SearchServiceName $SearchServiceName -Endpoint $Endpoint -OutputPath $OutputPath
        return
    }
    
    $schemaPath = Join-Path $OutputPath "schema"
    if (-not (Test-Path $schemaPath)) {
        New-Item -ItemType Directory -Path $schemaPath -Force | Out-Null
    }
    
    $headers = @{
        "api-key" = $adminKeyPlain
        "Content-Type" = "application/json"
    }
    
    # Export indexes
    try {
        $indexes = Invoke-RestMethod -Uri "$Endpoint/indexes?api-version=2023-11-01" -Method Get -Headers $headers
        if ($indexes.value) {
            Save-JsonFile -Path (Join-Path $schemaPath "indexes.json") -Data $indexes.value
            Write-Log "SUCCESS" "Indexes exported" @{ Count = $indexes.value.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export indexes" @{ Error = $_.Exception.Message }
    }
    
    # Export indexers
    try {
        $indexers = Invoke-RestMethod -Uri "$Endpoint/indexers?api-version=2023-11-01" -Method Get -Headers $headers
        if ($indexers.value) {
            Save-JsonFile -Path (Join-Path $schemaPath "indexers.json") -Data $indexers.value
            Write-Log "SUCCESS" "Indexers exported" @{ Count = $indexers.value.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export indexers" @{ Error = $_.Exception.Message }
    }
    
    # Export datasources
    try {
        $datasources = Invoke-RestMethod -Uri "$Endpoint/datasources?api-version=2023-11-01" -Method Get -Headers $headers
        if ($datasources.value) {
            Save-JsonFile -Path (Join-Path $schemaPath "datasources.json") -Data $datasources.value
            Write-Log "SUCCESS" "Data sources exported" @{ Count = $datasources.value.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export datasources" @{ Error = $_.Exception.Message }
    }
    
    # Export skillsets
    try {
        $skillsets = Invoke-RestMethod -Uri "$Endpoint/skillsets?api-version=2023-11-01" -Method Get -Headers $headers
        if ($skillsets.value) {
            Save-JsonFile -Path (Join-Path $schemaPath "skillsets.json") -Data $skillsets.value
            Write-Log "SUCCESS" "Skillsets exported" @{ Count = $skillsets.value.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export skillsets" @{ Error = $_.Exception.Message }
    }
    
    # Clear the key from memory
    $adminKeyPlain = $null
    $adminKey = $null
}

function Generate-SearchSchemaScript {
    param(
        [string]$SearchServiceName,
        [string]$Endpoint,
        [string]$OutputPath
    )
    
    $scriptPath = Join-Path $OutputPath "export_schema.ps1"
    $scriptContent = @"
# Operator-assisted Search schema export script
# This script prompts for the admin key at runtime and exports Search schemas
# DO NOT store the admin key in this file or commit it to source control

param(
    [Parameter(Mandatory=`$true)]
    [string]`$SearchServiceName = "$SearchServiceName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$Endpoint = "$Endpoint"
)

`$ErrorActionPreference = "Stop"

# Prompt for admin key (secure input)
Write-Host "Enter Azure AI Search admin key for `$SearchServiceName (input will be hidden):" -ForegroundColor Yellow
`$adminKey = Read-Host -AsSecureString
`$adminKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR(`$adminKey)
)

if ([string]::IsNullOrWhiteSpace(`$adminKeyPlain)) {
    Write-Error "Admin key is required"
    exit 1
}

`$headers = @{
    "api-key" = `$adminKeyPlain
    "Content-Type" = "application/json"
}

`$schemaPath = Join-Path `$PSScriptRoot "schema"
if (-not (Test-Path `$schemaPath)) {
    New-Item -ItemType Directory -Path `$schemaPath -Force | Out-Null
}

# Export indexes
try {
    `$indexes = Invoke-RestMethod -Uri "`$Endpoint/indexes?api-version=2023-11-01" -Method Get -Headers `$headers
    if (`$indexes.value) {
        `$indexes.value | ConvertTo-Json -Depth 20 | Set-Content -Path (Join-Path `$schemaPath "indexes.json") -Encoding UTF8
        Write-Host "Exported `$(`$indexes.value.Count) indexes" -ForegroundColor Green
    }
}
catch {
    Write-Warning "Failed to export indexes: `$(`$_.Exception.Message)"
}

# Export indexers
try {
    `$indexers = Invoke-RestMethod -Uri "`$Endpoint/indexers?api-version=2023-11-01" -Method Get -Headers `$headers
    if (`$indexers.value) {
        `$indexers.value | ConvertTo-Json -Depth 20 | Set-Content -Path (Join-Path `$schemaPath "indexers.json") -Encoding UTF8
        Write-Host "Exported `$(`$indexers.value.Count) indexers" -ForegroundColor Green
    }
}
catch {
    Write-Warning "Failed to export indexers: `$(`$_.Exception.Message)"
}

# Export datasources
try {
    `$datasources = Invoke-RestMethod -Uri "`$Endpoint/datasources?api-version=2023-11-01" -Method Get -Headers `$headers
    if (`$datasources.value) {
        `$datasources.value | ConvertTo-Json -Depth 20 | Set-Content -Path (Join-Path `$schemaPath "datasources.json") -Encoding UTF8
        Write-Host "Exported `$(`$datasources.value.Count) datasources" -ForegroundColor Green
    }
}
catch {
    Write-Warning "Failed to export datasources: `$(`$_.Exception.Message)"
}

# Export skillsets
try {
    `$skillsets = Invoke-RestMethod -Uri "`$Endpoint/skillsets?api-version=2023-11-01" -Method Get -Headers `$headers
    if (`$skillsets.value) {
        `$skillsets.value | ConvertTo-Json -Depth 20 | Set-Content -Path (Join-Path `$schemaPath "skillsets.json") -Encoding UTF8
        Write-Host "Exported `$(`$skillsets.value.Count) skillsets" -ForegroundColor Green
    }
}
catch {
    Write-Warning "Failed to export skillsets: `$(`$_.Exception.Message)"
}

# Clear key from memory
`$adminKeyPlain = `$null
`$adminKey = `$null

Write-Host "Schema export completed. Files saved to: `$schemaPath" -ForegroundColor Green
"@
    
    Set-Content -Path $scriptPath -Value $scriptContent -Encoding UTF8
    Write-Log "INFO" "Generated operator-assisted schema export script" @{ Path = $scriptPath }
}

# Functions available when dot-sourced

