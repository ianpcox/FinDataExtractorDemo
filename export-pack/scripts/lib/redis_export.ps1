# Azure Cache for Redis Exporter
# Exports Redis cache configuration (no keys/secrets)

. "$PSScriptRoot\common.ps1"

function Export-RedisCache {
    param(
        [string]$CacheName,
        [string]$ResourceGroupName,
        [string]$SubscriptionId,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting Azure Cache for Redis" @{
        CacheName = $CacheName
        ResourceGroup = $ResourceGroupName
        SubscriptionId = $SubscriptionId
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $redisPath = Join-Path $OutputPath "redis" (Get-SafeFileName $CacheName)
    if (-not (Test-Path $redisPath)) {
        New-Item -ItemType Directory -Path $redisPath -Force | Out-Null
    }
    
    # Export cache configuration
    try {
        $cache = az redis show --name $CacheName --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0) {
            $redacted = Remove-SecretsFromObject $cache
            Save-JsonFile -Path (Join-Path $redisPath "cache.json") -Data $redacted -RedactSecrets
            Write-Log "SUCCESS" "Redis cache configuration exported"
            
            # Extract key configuration details
            $config = @{
                Name = $cache.name
                Location = $cache.location
                Sku = $cache.sku
                RedisVersion = $cache.redisVersion
                EnableNonSslPort = $cache.enableNonSslPort
                MinimumTlsVersion = $cache.minimumTlsVersion
                SubnetId = $cache.subnetId
                StaticIP = $cache.staticIP
                Port = $cache.port
                SslPort = $cache.sslPort
                ShardCount = $cache.shardCount
            }
            
            Save-JsonFile -Path (Join-Path $redisPath "configuration.json") -Data $config
            Write-Log "INFO" "Redis configuration summary exported"
        }
        else {
            Write-Log "ERROR" "Failed to get Redis cache details"
            return
        }
    }
    catch {
        Write-Log "ERROR" "Failed to export Redis cache" @{ Error = $_.Exception.Message }
        return
    }
    
    # Note: We do NOT export keys (az redis list-keys is forbidden per requirements)
    Write-Log "INFO" "Redis keys not exported (per security requirements)" @{
        Note = "Keys must be regenerated or migrated separately in target environment"
    }
}

# Functions available when dot-sourced

