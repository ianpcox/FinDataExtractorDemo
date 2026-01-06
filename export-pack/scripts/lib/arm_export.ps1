# ARM Template Export and Bicep Decompilation
# Exports ARM templates for resource groups and decompiles to Bicep

. "$PSScriptRoot\common.ps1"

function Export-ARMTemplate {
    param(
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting ARM template" @{
        ResourceGroup = $ResourceGroupName
        SubscriptionId = $SubscriptionId
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $armPath = Join-Path $OutputPath "arm"
    if (-not (Test-Path $armPath)) {
        New-Item -ItemType Directory -Path $armPath -Force | Out-Null
    }
    
    $armFile = Join-Path $armPath "$(Get-SafeFileName $ResourceGroupName).json"
    
    try {
        Write-Log "INFO" "Running ARM export command" @{ ResourceGroup = $ResourceGroupName }
        $armJson = az group export --name $ResourceGroupName --output json 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Log "WARN" "ARM export returned non-zero exit code" @{
                ExitCode = $LASTEXITCODE
                Error = ($armJson -join "`n")
            }
            # Still try to save what we got
        }
        
        # Try to parse as JSON to validate
        try {
            $armObj = $armJson | ConvertFrom-Json
            $redacted = Remove-SecretsFromObject $armObj
            Save-JsonFile -Path $armFile -Data $redacted
            Write-Log "SUCCESS" "ARM template exported" @{ Path = $armFile }
            return $armFile
        }
        catch {
            # Save raw output if JSON parse fails
            Write-Log "WARN" "ARM export output is not valid JSON, saving as text" @{
                Error = $_.Exception.Message
            }
            Set-Content -Path $armFile -Value ($armJson -join "`n") -Encoding UTF8
            return $armFile
        }
    }
    catch {
        Write-Log "ERROR" "Failed to export ARM template" @{
            ResourceGroup = $ResourceGroupName
            Error = $_.Exception.Message
        }
        return $null
    }
}

function Export-Deployments {
    param(
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting deployment history" @{
        ResourceGroup = $ResourceGroupName
        SubscriptionId = $SubscriptionId
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $deploymentsPath = Join-Path $OutputPath "deployments"
    if (-not (Test-Path $deploymentsPath)) {
        New-Item -ItemType Directory -Path $deploymentsPath -Force | Out-Null
    }
    
    try {
        $deployments = az deployment group list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $deployments) {
            Save-JsonFile -Path (Join-Path $deploymentsPath "deployments.json") -Data $deployments -RedactSecrets
            Write-Log "SUCCESS" "Deployment history exported" @{
                DeploymentCount = $deployments.Count
            }
        }
        else {
            Write-Log "INFO" "No deployments found or export failed" @{
                ResourceGroup = $ResourceGroupName
            }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export deployments" @{
            ResourceGroup = $ResourceGroupName
            Error = $_.Exception.Message
        }
    }
}

function Decompile-ToBicep {
    param(
        [string]$ArmTemplatePath,
        [string]$OutputPath
    )
    
    if (-not (Test-Path $ArmTemplatePath)) {
        Write-Log "WARN" "ARM template file not found" @{ Path = $ArmTemplatePath }
        return $null
    }
    
    Write-Log "INFO" "Decompiling ARM to Bicep" @{ ArmTemplate = $ArmTemplatePath }
    
    $bicepPath = Join-Path $OutputPath "bicep"
    if (-not (Test-Path $bicepPath)) {
        New-Item -ItemType Directory -Path $bicepPath -Force | Out-Null
    }
    
    $bicepFile = Join-Path $bicepPath ([System.IO.Path]::GetFileNameWithoutExtension($ArmTemplatePath) + ".bicep")
    
    try {
        # Check if bicep is available
        $null = az bicep version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "WARN" "Bicep CLI not available, skipping decompilation" @{ Path = $ArmTemplatePath }
            return $null
        }
        
        az bicep decompile --file $ArmTemplatePath --outfile $bicepFile 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0 -and (Test-Path $bicepFile)) {
            Write-Log "SUCCESS" "Bicep file generated" @{ Path = $bicepFile }
            return $bicepFile
        }
        else {
            Write-Log "WARN" "Bicep decompilation may have failed or produced warnings" @{
                ArmTemplate = $ArmTemplatePath
                ExitCode = $LASTEXITCODE
            }
            return $null
        }
    }
    catch {
        Write-Log "WARN" "Failed to decompile to Bicep" @{
            ArmTemplate = $ArmTemplatePath
            Error = $_.Exception.Message
        }
        return $null
    }
}

# Functions available when dot-sourced

