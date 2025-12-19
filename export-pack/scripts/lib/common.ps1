# Common utilities for Azure Export Pack
# Provides logging, error handling, and helper functions

#region Logging Functions

$script:LogFile = $null
$script:TranscriptFile = $null
$script:StartTime = Get-Date

function Initialize-Logging {
    param(
        [string]$OutputRoot,
        [string]$Timestamp
    )
    
    $logDir = Join-Path $OutputRoot "logs"
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    
    $script:LogFile = Join-Path $logDir "export_$Timestamp.jsonl"
    $script:TranscriptFile = Join-Path $logDir "export_$Timestamp.txt"
    
    Start-Transcript -Path $script:TranscriptFile -Append
    
    Write-Log "INFO" "Logging initialized" @{
        LogFile = $script:LogFile
        TranscriptFile = $script:TranscriptFile
    }
}

function Write-Log {
    param(
        [string]$Level,
        [string]$Message,
        [hashtable]$Data = @{}
    )
    
    $logEntry = @{
        Timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ")
        Level = $Level
        Message = $Message
        Data = $Data
    } | ConvertTo-Json -Compress
    
    if ($script:LogFile) {
        Add-Content -Path $script:LogFile -Value $logEntry
    }
    
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN" { "Yellow" }
        "INFO" { "Cyan" }
        "SUCCESS" { "Green" }
        default { "White" }
    }
    
    Write-Host "[$Level] $Message" -ForegroundColor $color
    if ($Data.Count -gt 0) {
        $Data.GetEnumerator() | ForEach-Object {
            Write-Host "  $($_.Key): $($_.Value)" -ForegroundColor Gray
        }
    }
}

function Stop-Logging {
    $duration = (Get-Date) - $script:StartTime
    Write-Log "INFO" "Export completed" @{
        Duration = $duration.ToString()
        DurationSeconds = [math]::Round($duration.TotalSeconds, 2)
    }
    Stop-Transcript
}

#endregion

#region Error Handling

function Invoke-SafeCommand {
    param(
        [scriptblock]$Command,
        [string]$ErrorMessage = "Command failed",
        [int]$Retries = 3,
        [int]$RetryDelaySeconds = 5
    )
    
    $attempt = 0
    $lastError = $null
    
    while ($attempt -lt $Retries) {
        try {
            $result = & $Command
            Write-Log "SUCCESS" "Command succeeded" @{
                Attempt = $attempt + 1
            }
            return $result
        }
        catch {
            $lastError = $_
            $attempt++
            Write-Log "WARN" "$ErrorMessage (Attempt $attempt/$Retries)" @{
                Error = $_.Exception.Message
            }
            
            if ($attempt -lt $Retries) {
                Start-Sleep -Seconds $RetryDelaySeconds
            }
        }
    }
    
    Write-Log "ERROR" "$ErrorMessage after $Retries attempts" @{
        FinalError = $lastError.Exception.Message
    }
    throw $lastError
}

#endregion

#region File Utilities

function Get-SafeFileName {
    param([string]$Name)
    
    $invalidChars = [System.IO.Path]::GetInvalidFileNameChars()
    $safeName = $Name
    foreach ($char in $invalidChars) {
        $safeName = $safeName.Replace($char, '_')
    }
    return $safeName
}

function Save-JsonFile {
    param(
        [string]$Path,
        [object]$Data,
        [switch]$RedactSecrets
    )
    
    $dir = Split-Path -Path $Path -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    
    $json = if ($RedactSecrets) {
        $redacted = Remove-SecretsFromObject $Data
        $redacted | ConvertTo-Json -Depth 20
    } else {
        $Data | ConvertTo-Json -Depth 20
    }
    
    Set-Content -Path $Path -Value $json -Encoding UTF8
    Write-Log "INFO" "Saved JSON file" @{ Path = $Path }
}

function Remove-SecretsFromObject {
    param([object]$Object)
    
    if ($null -eq $Object) { return $null }
    
    if ($Object -is [PSCustomObject] -or $Object -is [hashtable]) {
        $result = if ($Object -is [hashtable]) { @{} } else { [PSCustomObject]@{} }
        
        $props = if ($Object -is [hashtable]) {
            $Object.Keys
        } else {
            $Object.PSObject.Properties.Name
        }
        
        foreach ($prop in $props) {
            $value = if ($Object -is [hashtable]) {
                $Object[$prop]
            } else {
                $Object.$prop
            }
            
            $lowerProp = $prop.ToLower()
            if ($lowerProp -match '(key|secret|password|token|connectionstring|sas|apikey|accesskey)' -and 
                $value -is [string] -and $value.Length -gt 0) {
                # Redact the value
                $value = "***REDACTED***"
            }
            elseif ($value -is [PSCustomObject] -or $value -is [hashtable] -or $value -is [array]) {
                $value = Remove-SecretsFromObject $value
            }
            
            if ($result -is [hashtable]) {
                $result[$prop] = $value
            } else {
                $result | Add-Member -MemberType NoteProperty -Name $prop -Value $value
            }
        }
        
        return $result
    }
    elseif ($Object -is [array]) {
        return $Object | ForEach-Object { Remove-SecretsFromObject $_ }
    }
    else {
        return $Object
    }
}

#endregion

#region Tool Detection

function Test-Prerequisites {
    $tools = @{
        "az" = @{
            Command = "az"
            Test = { az version --output none 2>&1 }
            Required = $true
        }
        "bicep" = @{
            Command = "az bicep"
            Test = { az bicep version 2>&1 }
            Required = $false
        }
        "kubectl" = @{
            Command = "kubectl"
            Test = { kubectl version --client --output json 2>&1 }
            Required = $false
        }
        "helm" = @{
            Command = "helm"
            Test = { helm version --short 2>&1 }
            Required = $false
        }
    }
    
    $results = @{}
    
    foreach ($toolName in $tools.Keys) {
        $tool = $tools[$toolName]
        try {
            $null = & $tool.Test
            $results[$toolName] = @{
                Available = $true
                Required = $tool.Required
            }
            Write-Log "INFO" "Tool available: $toolName" @{ Required = $tool.Required }
        }
        catch {
            $results[$toolName] = @{
                Available = $false
                Required = $tool.Required
            }
            if ($tool.Required) {
                Write-Log "ERROR" "Required tool missing: $toolName"
            } else {
                Write-Log "WARN" "Optional tool missing: $toolName"
            }
        }
    }
    
    $missingRequired = $results.GetEnumerator() | Where-Object { 
        $_.Value.Required -and -not $_.Value.Available 
    }
    
    if ($missingRequired) {
        Write-Log "ERROR" "Missing required tools" @{
            Missing = ($missingRequired | ForEach-Object { $_.Key }) -join ", "
        }
        throw "Missing required tools: $($missingRequired | ForEach-Object { $_.Key })"
    }
    
    return $results
}

#endregion

#region Azure Utilities

function Get-AzureSubscriptionId {
    param([string]$SubscriptionNameOrId)
    
    try {
        $sub = az account show --name $SubscriptionNameOrId --output json 2>&1 | ConvertFrom-Json
        if ($sub.id) {
            return $sub.id
        }
    }
    catch {
        # Try as ID directly
        try {
            $sub = az account show --subscription $SubscriptionNameOrId --output json 2>&1 | ConvertFrom-Json
            if ($sub.id) {
                return $sub.id
            }
        }
        catch {
            # Assume it's already an ID
            return $SubscriptionNameOrId
        }
    }
    
    return $SubscriptionNameOrId
}

function Set-AzureSubscription {
    param([string]$SubscriptionId)
    
    Write-Log "INFO" "Setting Azure subscription" @{ SubscriptionId = $SubscriptionId }
    az account set --subscription $SubscriptionId | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to set subscription: $SubscriptionId"
    }
}

function Get-AzureResourceGroups {
    param([string]$SubscriptionId)
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    Write-Log "INFO" "Listing resource groups" @{ SubscriptionId = $SubscriptionId }
    $rgs = az group list --output json 2>&1 | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERROR" "Failed to list resource groups"
        return @()
    }
    
    return $rgs
}

function Get-AzureResources {
    param(
        [string]$ResourceGroupName,
        [string]$SubscriptionId
    )
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    Write-Log "INFO" "Listing resources in resource group" @{
        ResourceGroup = $ResourceGroupName
    }
    
    $resources = az resource list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        Write-Log "WARN" "Failed to list resources in RG: $ResourceGroupName"
        return @()
    }
    
    return $resources
}

#endregion

#region Export Path Utilities

function Get-ExportPath {
    param(
        [string]$OutputRoot,
        [string]$Timestamp,
        [string]$SubscriptionNameOrId,
        [string]$ResourceGroupName = "",
        [string]$ServiceType = "",
        [string]$ResourceName = ""
    )
    
    $safeSub = Get-SafeFileName $SubscriptionNameOrId
    $path = Join-Path $OutputRoot $Timestamp
    $path = Join-Path $path "subscription_$safeSub"
    
    if ($ResourceGroupName) {
        $safeRg = Get-SafeFileName $ResourceGroupName
        $path = Join-Path $path "resourceGroups" $safeRg
    }
    
    if ($ServiceType) {
        $path = Join-Path $path $ServiceType
    }
    
    if ($ResourceName) {
        $safeName = Get-SafeFileName $ResourceName
        $path = Join-Path $path $safeName
    }
    
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
    
    return $path
}

#endregion

# Note: Functions are available in parent scope when dot-sourced
# No Export-ModuleMember needed for dot-sourced scripts

