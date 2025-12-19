# Azure Key Vault Secret Exporter (Opt-In)
# Generates operator-assisted scripts to export Key Vault secrets

. "$PSScriptRoot\common.ps1"

function Export-KeyVaultSecrets {
    param(
        [string]$VaultName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Generating Key Vault secret export script" @{
        VaultName = $VaultName
        ResourceGroup = $ResourceGroupName
        SubscriptionId = $SubscriptionId
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $keyvaultPath = Join-Path $OutputPath "keyvault" (Get-SafeFileName $VaultName)
    if (-not (Test-Path $keyvaultPath)) {
        New-Item -ItemType Directory -Path $keyvaultPath -Force | Out-Null
    }
    
    # Get vault details
    try {
        $vault = az keyvault show --name $VaultName --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0) {
            $redacted = Remove-SecretsFromObject $vault
            Save-JsonFile -Path (Join-Path $keyvaultPath "vault.json") -Data $redacted -RedactSecrets
            Write-Log "SUCCESS" "Key Vault configuration exported"
        }
        else {
            Write-Log "ERROR" "Failed to get Key Vault details"
            return
        }
    }
    catch {
        Write-Log "ERROR" "Failed to export Key Vault" @{ Error = $_.Exception.Message }
        return
    }
    
    # Get secret names (list only, no values)
    try {
        $secrets = az keyvault secret list --vault-name $VaultName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $secrets) {
            # Save secret names only
            $secretNames = $secrets | Select-Object @{Name='id'; Expression={$_.id}}, `
                @{Name='name'; Expression={$_.name}}, `
                @{Name='contentType'; Expression={$_.contentType}}, `
                @{Name='attributes'; Expression={$_.attributes}}
            
            Save-JsonFile -Path (Join-Path $keyvaultPath "secret_names.json") -Data $secretNames
            Write-Log "SUCCESS" "Secret names exported" @{ Count = $secretNames.Count }
            
            # Generate operator-assisted export script
            Generate-KeyVaultSecretExportScript -VaultName $VaultName -ResourceGroupName $ResourceGroupName `
                -SubscriptionId $SubscriptionId -SecretNames $secretNames -OutputPath $keyvaultPath
        }
        else {
            Write-Log "INFO" "No secrets found in vault or list failed" @{ VaultName = $VaultName }
            # Still generate script template
            Generate-KeyVaultSecretExportScript -VaultName $VaultName -ResourceGroupName $ResourceGroupName `
                -SubscriptionId $SubscriptionId -SecretNames @() -OutputPath $keyvaultPath
        }
    }
    catch {
        Write-Log "WARN" "Failed to list secrets" @{ Error = $_.Exception.Message }
        # Still generate script template
        Generate-KeyVaultSecretExportScript -VaultName $VaultName -ResourceGroupName $ResourceGroupName `
            -SubscriptionId $SubscriptionId -SecretNames @() -OutputPath $keyvaultPath
    }
}

function Generate-KeyVaultSecretExportScript {
    param(
        [string]$VaultName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [array]$SecretNames,
        [string]$OutputPath
    )
    
    $scriptPath = Join-Path $OutputPath "export_secrets.ps1"
    
    $secretList = if ($SecretNames.Count -gt 0) {
        $SecretNames | ForEach-Object { "        '$($_.name)'" } | Out-String
        $SecretNames | ForEach-Object { "        '$($_.name)'" } -join ",`n"
    } else {
        "# No secrets detected - script will attempt to list all secrets"
    }
    
    $scriptContent = @"
# Key Vault Secret Export Script
# WARNING: This script exports secret VALUES. Handle with extreme care.
# DO NOT commit the output JSON file to source control.
# DO NOT share the output file via insecure channels.

param(
    [Parameter(Mandatory=`$true)]
    [string]`$VaultName = "$VaultName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$ResourceGroupName = "$ResourceGroupName",
    
    [Parameter(Mandatory=`$true)]
    [string]`$SubscriptionId = "$SubscriptionId",
    
    [switch]`$EncryptOutput
)

`$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Red
Write-Host "Key Vault Secret Export" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""
Write-Host "WARNING: This script will export SECRET VALUES." -ForegroundColor Yellow
Write-Host "The output file contains sensitive data." -ForegroundColor Yellow
Write-Host "DO NOT commit to source control." -ForegroundColor Yellow
Write-Host "DO NOT share via insecure channels." -ForegroundColor Yellow
Write-Host ""

`$confirm = Read-Host "Type 'EXPORT' to continue (case-sensitive)"
if (`$confirm -ne "EXPORT") {
    Write-Host "Export cancelled." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "Setting Azure subscription..." -ForegroundColor Cyan
az account set --subscription `$SubscriptionId | Out-Null

Write-Host "Listing secrets in vault..." -ForegroundColor Cyan
`$secrets = az keyvault secret list --vault-name `$VaultName --output json | ConvertFrom-Json

if (-not `$secrets -or `$secrets.Count -eq 0) {
    Write-Host "No secrets found in vault." -ForegroundColor Yellow
    exit 0
}

Write-Host "Found `$(`$secrets.Count) secrets. Exporting values..." -ForegroundColor Cyan
Write-Host ""

`$exportedSecrets = @()

foreach (`$secret in `$secrets) {
    `$secretName = `$secret.name
    Write-Host "Exporting secret: `$secretName" -ForegroundColor Gray
    
    try {
        `$secretValue = az keyvault secret show --vault-name `$VaultName --name `$secretName --query value -o tsv
        
        `$secretInfo = az keyvault secret show --vault-name `$VaultName --name `$secretName --output json | ConvertFrom-Json
        
        `$exportedSecrets += @{
            name = `$secretName
            id = `$secretInfo.id
            value = `$secretValue
            contentType = `$secretInfo.contentType
            attributes = `$secretInfo.attributes
            tags = `$secretInfo.tags
        }
        
        Write-Host "  ✓ Exported" -ForegroundColor Green
    }
    catch {
        Write-Host "  ✗ Failed: `$(`$_.Exception.Message)" -ForegroundColor Red
    }
}

`$outputFile = Join-Path `$PSScriptRoot "secrets_exported_`$(Get-Date -Format 'yyyyMMdd-HHmmss').json"

if (`$EncryptOutput) {
    Write-Host ""
    Write-Host "Encrypting output file..." -ForegroundColor Cyan
    `$jsonContent = `$exportedSecrets | ConvertTo-Json -Depth 10
    `$secureString = ConvertTo-SecureString `$jsonContent -AsPlainText -Force
    `$encryptedFile = `$outputFile + ".encrypted"
    `$secureString | Export-Clixml -Path `$encryptedFile
    Write-Host "Encrypted file saved to: `$encryptedFile" -ForegroundColor Green
    Write-Host "To decrypt: `$decrypted = Import-Clixml `$encryptedFile | ConvertFrom-SecureString -AsPlainText" -ForegroundColor Yellow
}
else {
    `$exportedSecrets | ConvertTo-Json -Depth 10 | Set-Content -Path `$outputFile -Encoding UTF8
    Write-Host ""
    Write-Host "Secrets exported to: `$outputFile" -ForegroundColor Green
    Write-Host "WARNING: This file contains sensitive data. Handle with care." -ForegroundColor Red
}

Write-Host ""
Write-Host "Export completed. Exported `$(`$exportedSecrets.Count) secrets." -ForegroundColor Green
"@
    
    Set-Content -Path $scriptPath -Value $scriptContent -Encoding UTF8
    Write-Log "INFO" "Generated Key Vault secret export script" @{ Path = $scriptPath }
}

# Functions available when dot-sourced

