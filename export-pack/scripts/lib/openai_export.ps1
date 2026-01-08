# Azure OpenAI / Cognitive Services Exporter
# Exports OpenAI account configuration and model deployments

. "$PSScriptRoot\common.ps1"

function Export-OpenAIService {
    param(
        [string]$AccountName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath,
        [switch]$IncludeDeployments
    )
    
    Write-Log "INFO" "Exporting Azure OpenAI service" @{
        AccountName = $AccountName
        ResourceGroup = $ResourceGroupName
        SubscriptionId = $SubscriptionId
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $openaiPath = Join-Path $OutputPath "openai" (Get-SafeFileName $AccountName)
    if (-not (Test-Path $openaiPath)) {
        New-Item -ItemType Directory -Path $openaiPath -Force | Out-Null
    }
    
    # Export account properties
    try {
        $account = az resource show `
            --name $AccountName `
            --resource-group $ResourceGroupName `
            --resource-type "Microsoft.CognitiveServices/accounts" `
            --output json 2>&1 | ConvertFrom-Json
        
        if ($LASTEXITCODE -eq 0) {
            # Check if this is an OpenAI account
            $isOpenAI = $account.kind -eq "OpenAI" -or 
                       ($account.properties.capabilities | Where-Object { $_.name -eq "OpenAI" })
            
            if (-not $isOpenAI) {
                Write-Log "INFO" "Account is not an OpenAI service, exporting as Cognitive Services" @{
                    Kind = $account.kind
                }
            }
            
            $redacted = Remove-SecretsFromObject $account
            Save-JsonFile -Path (Join-Path $openaiPath "account.json") -Data $redacted -RedactSecrets
            Write-Log "SUCCESS" "OpenAI account configuration exported"
        }
        else {
            Write-Log "ERROR" "Failed to get OpenAI account details"
            return
        }
    }
    catch {
        Write-Log "ERROR" "Failed to export OpenAI account" @{ Error = $_.Exception.Message }
        return
    }
    
    # Export deployments if requested
    if ($IncludeDeployments) {
        Export-OpenAIDeployments -AccountName $AccountName -ResourceGroupName $ResourceGroupName `
            -SubscriptionId $SubscriptionId -OutputPath $openaiPath
    }
    else {
        # Generate operator-assisted script
        Generate-OpenAIDeploymentsScript -AccountName $AccountName -ResourceGroupName $ResourceGroupName `
            -SubscriptionId $SubscriptionId -OutputPath $openaiPath
    }
}

function Export-OpenAIDeployments {
    param(
        [string]$AccountName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting OpenAI deployments (requires API key)" @{ Account = $AccountName }
    
    # Try to get deployments via management API
    try {
        Set-AzureSubscription -SubscriptionId $SubscriptionId
        
        # Use REST API to list deployments
        $subId = $SubscriptionId
        $uri = "https://management.azure.com/subscriptions/$subId/resourceGroups/$ResourceGroupName/providers/Microsoft.CognitiveServices/accounts/$AccountName/deployments?api-version=2023-05-01"
        
        $token = az account get-access-token --query accessToken -o tsv
        if ($token) {
            $headers = @{
                "Authorization" = "Bearer $token"
                "Content-Type" = "application/json"
            }
            
            $deployments = Invoke-RestMethod -Uri $uri -Method Get -Headers $headers
            if ($deployments.value) {
                Save-JsonFile -Path (Join-Path $outputPath "deployments.json") -Data $deployments.value -RedactSecrets
                Write-Log "SUCCESS" "Deployments exported via management API" @{ Count = $deployments.value.Count }
                return
            }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export deployments via management API" @{ Error = $_.Exception.Message }
    }
    
    # Fallback: generate operator-assisted script
    Generate-OpenAIDeploymentsScript -AccountName $AccountName -ResourceGroupName $ResourceGroupName `
        -SubscriptionId $SubscriptionId -OutputPath $OutputPath
}

function Generate-OpenAIDeploymentsScript {
    param(
        [string]$AccountName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    $scriptPath = Join-Path $OutputPath "export_deployments.ps1"
    
    # Get endpoint from account if possible
    try {
        Set-AzureSubscription -SubscriptionId $SubscriptionId
        $account = az resource show `
            --name $AccountName `
            --resource-group $ResourceGroupName `
            --resource-type "Microsoft.CognitiveServices/accounts" `
            --output json 2>&1 | ConvertFrom-Json
        
        $endpoint = $account.properties.endpoint
    }
    catch {
        $endpoint = "https://$AccountName.openai.azure.com"
    }
    
    $scriptContent = @"
# Operator-assisted OpenAI deployments export script
# This script exports model deployments using the management API
# Requires Contributor or Reader role on the resource

param(
    [Parameter(Mandatory=`$true)]
    [string]`$AccountName = "$AccountName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$ResourceGroupName = "$ResourceGroupName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$SubscriptionId = "$SubscriptionId",
    
    [string]`$Endpoint = "$endpoint"
)

`$ErrorActionPreference = "Stop"

Write-Host "Exporting OpenAI deployments for `$AccountName..." -ForegroundColor Cyan

# Set subscription
az account set --subscription `$SubscriptionId | Out-Null

# Get access token
`$token = az account get-access-token --query accessToken -o tsv
if (-not `$token) {
    Write-Error "Failed to get access token"
    exit 1
}

`$uri = "https://management.azure.com/subscriptions/`$SubscriptionId/resourceGroups/`$ResourceGroupName/providers/Microsoft.CognitiveServices/accounts/`$AccountName/deployments?api-version=2023-05-01"

`$headers = @{
    "Authorization" = "Bearer `$token"
    "Content-Type" = "application/json"
}

try {
    `$deployments = Invoke-RestMethod -Uri `$uri -Method Get -Headers `$headers
    if (`$deployments.value) {
        `$deployments.value | ConvertTo-Json -Depth 20 | Set-Content -Path (Join-Path `$PSScriptRoot "deployments.json") -Encoding UTF8
        Write-Host "Exported `$(`$deployments.value.Count) deployments" -ForegroundColor Green
        
        # Create summary
        `$summary = `$deployments.value | Select-Object `
            @{Name='Name'; Expression={`$_.name}}, `
            @{Name='Model'; Expression={`$_.properties.model.name}}, `
            @{Name='ModelVersion'; Expression={`$_.properties.model.version}}, `
            @{Name='ScaleType'; Expression={`$_.properties.scaleSettings.scaleType}}, `
            @{Name='Capacity'; Expression={`$_.properties.scaleSettings.capacity}}, `
            @{Name='Status'; Expression={`$_.properties.provisioningState}}
        
        `$summary | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path `$PSScriptRoot "deployments_summary.json") -Encoding UTF8
        `$summary | Export-Csv -Path (Join-Path `$PSScriptRoot "deployments_summary.csv") -NoTypeInformation -Encoding UTF8
    }
    else {
        Write-Host "No deployments found" -ForegroundColor Yellow
    }
}
catch {
    Write-Error "Failed to export deployments: `$(`$_.Exception.Message)"
    exit 1
}

Write-Host "Deployment export completed. Files saved to: `$PSScriptRoot" -ForegroundColor Green
"@
    
    Set-Content -Path $scriptPath -Value $scriptContent -Encoding UTF8
    Write-Log "INFO" "Generated operator-assisted deployments export script" @{ Path = $scriptPath }
}

# Functions available when dot-sourced

