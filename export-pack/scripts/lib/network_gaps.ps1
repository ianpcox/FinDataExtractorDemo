# Network Gaps Report Generator
# Identifies private endpoints, DNS zones, peerings, route tables

. "$PSScriptRoot\common.ps1"

function Export-NetworkGaps {
    param(
        [string]$SubscriptionId,
        [string]$ResourceGroupName,
        [string]$OutputPath
    )
    
    Write-Log "INFO" "Exporting network gaps report" @{
        SubscriptionId = $SubscriptionId
        ResourceGroup = $ResourceGroupName
    }
    
    Set-AzureSubscription -SubscriptionId $SubscriptionId
    
    $networkPath = Join-Path $OutputPath "network"
    if (-not (Test-Path $networkPath)) {
        New-Item -ItemType Directory -Path $networkPath -Force | Out-Null
    }
    
    $gaps = @{
        PrivateEndpoints = @()
        PrivateDnsZones = @()
        VNetPeerings = @()
        RouteTables = @()
        NetworkSecurityGroups = @()
    }
    
    # Export private endpoints
    try {
        if ($ResourceGroupName) {
            $endpoints = az network private-endpoint list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        } else {
            $endpoints = az network private-endpoint list --output json 2>&1 | ConvertFrom-Json
        }
        if ($LASTEXITCODE -eq 0 -and $endpoints) {
            $gaps.PrivateEndpoints = $endpoints | Select-Object name, id, location, `
                @{Name='privateLinkServiceConnections'; Expression={$_.privateLinkServiceConnections}}, `
                @{Name='subnet'; Expression={$_.networkInterfaces[0].id -split '/subnets/' | Select-Object -Last 1}}
            Write-Log "SUCCESS" "Private endpoints exported" @{ Count = $endpoints.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export private endpoints" @{ Error = $_.Exception.Message }
    }
    
    # Export private DNS zones
    try {
        if ($ResourceGroupName) {
            $zones = az network private-dns zone list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        } else {
            $zones = az network private-dns zone list --output json 2>&1 | ConvertFrom-Json
        }
        if ($LASTEXITCODE -eq 0 -and $zones) {
            $gaps.PrivateDnsZones = $zones | Select-Object name, id, location, numberOfRecords
            Write-Log "SUCCESS" "Private DNS zones exported" @{ Count = $zones.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export private DNS zones" @{ Error = $_.Exception.Message }
    }
    
    # Export VNet peerings
    try {
        $vnets = if ($ResourceGroupName) {
            az network vnet list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        } else {
            az network vnet list --output json 2>&1 | ConvertFrom-Json
        }
        if ($vnets) {
            foreach ($vnet in $vnets) {
                $peerings = az network vnet peering list --resource-group $vnet.resourceGroup --vnet-name $vnet.name --output json 2>&1 | ConvertFrom-Json
                if ($peerings) {
                    foreach ($peering in $peerings) {
                        $gaps.VNetPeerings += @{
                            VNetName = $vnet.name
                            VNetResourceGroup = $vnet.resourceGroup
                            PeeringName = $peering.name
                            RemoteVNetId = $peering.remoteVirtualNetwork.id
                            AllowForwardedTraffic = $peering.allowForwardedTraffic
                            AllowGatewayTransit = $peering.allowGatewayTransit
                            UseRemoteGateways = $peering.useRemoteGateways
                        }
                    }
                }
            }
            Write-Log "SUCCESS" "VNet peerings exported" @{ Count = $gaps.VNetPeerings.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export VNet peerings" @{ Error = $_.Exception.Message }
    }
    
    # Export route tables
    try {
        if ($ResourceGroupName) {
            $routeTables = az network route-table list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        } else {
            $routeTables = az network route-table list --output json 2>&1 | ConvertFrom-Json
        }
        if ($LASTEXITCODE -eq 0 -and $routeTables) {
            foreach ($rt in $routeTables) {
                $routes = az network route-table route list --resource-group $rt.resourceGroup --route-table-name $rt.name --output json 2>&1 | ConvertFrom-Json
                $gaps.RouteTables += @{
                    Name = $rt.name
                    ResourceGroup = $rt.resourceGroup
                    Location = $rt.location
                    Routes = $routes | Select-Object name, addressPrefix, nextHopType, nextHopIpAddress
                }
            }
            Write-Log "SUCCESS" "Route tables exported" @{ Count = $routeTables.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export route tables" @{ Error = $_.Exception.Message }
    }
    
    # Export NSG summaries
    try {
        if ($ResourceGroupName) {
            $nsgs = az network nsg list --resource-group $ResourceGroupName --output json 2>&1 | ConvertFrom-Json
        } else {
            $nsgs = az network nsg list --output json 2>&1 | ConvertFrom-Json
        }
        if ($LASTEXITCODE -eq 0 -and $nsgs) {
            foreach ($nsg in $nsgs) {
                $rules = az network nsg rule list --resource-group $nsg.resourceGroup --nsg-name $nsg.name --output json 2>&1 | ConvertFrom-Json
                $gaps.NetworkSecurityGroups += @{
                    Name = $nsg.name
                    ResourceGroup = $nsg.resourceGroup
                    Location = $nsg.location
                    RuleCount = if ($rules) { $rules.Count } else { 0 }
                }
            }
            Write-Log "SUCCESS" "NSGs exported" @{ Count = $nsgs.Count }
        }
    }
    catch {
        Write-Log "WARN" "Failed to export NSGs" @{ Error = $_.Exception.Message }
    }
    
    # Save JSON
    Save-JsonFile -Path (Join-Path $networkPath "network_gaps.json") -Data $gaps -RedactSecrets
    
    # Generate markdown report
    Generate-NetworkGapsReport -Gaps $gaps -OutputPath $networkPath -ResourceGroup $ResourceGroupName
    
    Write-Log "SUCCESS" "Network gaps report generated" @{ Path = $networkPath }
    
    return $gaps
}

function Generate-NetworkGapsReport {
    param(
        [hashtable]$Gaps,
        [string]$OutputPath,
        [string]$ResourceGroup
    )
    
    $reportPath = Join-Path $OutputPath "network_gaps_report.md"
    
    $md = @"
# Network Gaps Report

**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  
**Resource Group:** $(if ($ResourceGroup) { $ResourceGroup } else { "All" })

This report identifies network resources that may require manual configuration in the target environment.

---

## Private Endpoints

**Count:** $($Gaps.PrivateEndpoints.Count)

"@
    
    if ($Gaps.PrivateEndpoints.Count -gt 0) {
        foreach ($ep in $Gaps.PrivateEndpoints) {
            $md += @"
### $($ep.name)

- **Location:** $($ep.location)
- **Subnet:** $($ep.subnet)
- **Private Link Connections:** $($ep.privateLinkServiceConnections.Count)

**Manual Steps Required:**
1. Create private endpoint in target VNet
2. Configure private DNS zone integration
3. Update DNS records

**Bicep Snippet:**
``````bicep
resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: '$($ep.name)'
  location: '$($ep.location)'
  properties: {
    subnet: {
      id: '<target-subnet-id>'
    }
    privateLinkServiceConnections: [
      // Configure based on source
    ]
  }
}
``````

"@
        }
    } else {
        $md += "*No private endpoints found*`n`n"
    }
    
    $md += @"
---

## Private DNS Zones

**Count:** $($Gaps.PrivateDnsZones.Count)

"@
    
    if ($Gaps.PrivateDnsZones.Count -gt 0) {
        foreach ($zone in $Gaps.PrivateDnsZones) {
            $md += @"
### $($zone.name)

- **Location:** $($zone.location)
- **Records:** $($zone.numberOfRecords)

**Manual Steps Required:**
1. Create private DNS zone in target
2. Link to target VNets
3. Create A records for private endpoints

"@
        }
    } else {
        $md += "*No private DNS zones found*`n`n"
    }
    
    $md += @"
---

## VNet Peerings

**Count:** $($Gaps.VNetPeerings.Count)

"@
    
    if ($Gaps.VNetPeerings.Count -gt 0) {
        foreach ($peering in $Gaps.VNetPeerings) {
            $md += @"
### $($peering.PeeringName)

- **VNet:** $($peering.VNetName) (RG: $($peering.VNetResourceGroup))
- **Remote VNet:** $($peering.RemoteVNetId)
- **Allow Forwarded Traffic:** $($peering.AllowForwardedTraffic)
- **Allow Gateway Transit:** $($peering.AllowGatewayTransit)

**Manual Steps Required:**
1. Verify remote VNet exists in target (may be different subscription/tenant)
2. Create peering in both directions
3. Configure transit settings

"@
        }
    } else {
        $md += "*No VNet peerings found*`n`n"
    }
    
    $md += @"
---

## Route Tables

**Count:** $($Gaps.RouteTables.Count)

"@
    
    if ($Gaps.RouteTables.Count -gt 0) {
        foreach ($rt in $Gaps.RouteTables) {
            $md += @"
### $($rt.Name)

- **Resource Group:** $($rt.ResourceGroup)
- **Location:** $($rt.Location)
- **Routes:** $($rt.Routes.Count)

**Routes:**
"@
            foreach ($route in $rt.Routes) {
                $md += @"
- **$($route.name):** $($route.addressPrefix) → $($route.nextHopType) $($route.nextHopIpAddress)
"@
            }
            $md += "`n"
        }
    } else {
        $md += "*No route tables found*`n`n"
    }
    
    $md += @"
---

## Network Security Groups

**Count:** $($Gaps.NetworkSecurityGroups.Count)

"@
    
    if ($Gaps.NetworkSecurityGroups.Count -gt 0) {
        foreach ($nsg in $Gaps.NetworkSecurityGroups) {
            $md += @"
- **$($nsg.Name)** (RG: $($nsg.ResourceGroup)) - $($nsg.RuleCount) rules
"@
        }
        $md += "`n"
        $md += @"
**Note:** NSG rules are exported in ARM templates. Review and adjust as needed.
"@
    } else {
        $md += "*No NSGs found*`n`n"
    }
    
    $md += @"

---

## Recommendations

1. **Private Endpoints:** Ensure private DNS zones are linked to target VNets
2. **VNet Peerings:** Verify cross-subscription/tenant peerings are recreated
3. **Route Tables:** Associate with correct subnets in target
4. **NSG Rules:** Review and test security rules after deployment

See `network_gaps.json` for detailed JSON data.
"@
    
    Set-Content -Path $reportPath -Value $md -Encoding UTF8
    Write-Log "INFO" "Network gaps report generated" @{ Path = $reportPath }
}

# Functions available when dot-sourced

