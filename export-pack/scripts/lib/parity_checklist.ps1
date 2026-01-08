# Environment Parity Checklist Generator
# Generates comprehensive checklist of all operator-required actions

. "$PSScriptRoot\common.ps1"

function Generate-ParityChecklist {
    param(
        [hashtable]$ExportSummary,
        [string]$OutputPath,
        [hashtable]$Options = @{}
    )
    
    Write-Log "INFO" "Generating environment parity checklist"
    
    $checklistPath = Join-Path $OutputPath "ENVIRONMENT_PARITY_CHECKLIST.md"
    
    $checklistItems = @{
        Infrastructure = @()
        DataMigration = @()
        Secrets = @()
        Identity = @()
        Networking = @()
        Monitoring = @()
        Validation = @()
    }
    
    # Analyze export summary to build checklist
    foreach ($sub in $ExportSummary.Subscriptions) {
        foreach ($rg in $sub.ResourceGroups) {
            $rgPath = "subscription_$($sub.SubscriptionName)/resourceGroups/$($rg.Name)"
            
            # Infrastructure deployment
            $checklistItems.Infrastructure += @{
                Item = "Deploy ARM/Bicep templates for resource group: $($rg.Name)"
                Path = "$rgPath/arm/ or $rgPath/bicep/"
                Status = "Pending"
            }
            
            $checklistItems.Infrastructure += @{
                Item = "Apply RBAC assignments for resource group: $($rg.Name)"
                Path = "$rgPath/rbac/"
                Status = "Pending"
            }
        }
    }
    
    # Services requiring operator actions
    $services = $ExportSummary.ServicesExported
    
    # Search schemas
    if ($services.ContainsKey("Search") -and $services.Search -gt 0) {
        $checklistItems.DataMigration += @{
            Item = "Export and import Azure AI Search schemas (indexes, indexers, datasources, skillsets)"
            Path = "search/<service-name>/export_schema.ps1"
            Count = $services.Search
            Status = "Pending"
        }
    }
    
    # OpenAI deployments
    if ($services.ContainsKey("OpenAI") -and $services.OpenAI -gt 0) {
        $checklistItems.DataMigration += @{
            Item = "Export and recreate Azure OpenAI model deployments"
            Path = "openai/<account-name>/export_deployments.ps1"
            Count = $services.OpenAI
            Status = "Pending"
        }
    }
    
    # SQL data
    if ($services.ContainsKey("SQL") -and $services.SQL -gt 0) {
        $checklistItems.DataMigration += @{
            Item = "Export SQL databases as BACPAC and import to target"
            Path = "sql/<server-name>/export_data.ps1"
            Count = $services.SQL
            Status = "Pending"
        }
    }
    
    # Storage data
    if ($services.ContainsKey("Storage") -and $services.Storage -gt 0) {
        $checklistItems.DataMigration += @{
            Item = "Migrate storage account data using AzCopy"
            Path = "storage/<account-name>/migrate_data.ps1"
            Count = $services.Storage
            Status = "Pending"
        }
    }
    
    # Key Vault secrets
    if ($Options.ExportKeyVaultSecrets -and $services.ContainsKey("KeyVault")) {
        $checklistItems.Secrets += @{
            Item = "Export Key Vault secrets (opt-in, secure)"
            Path = "keyvault/<vault-name>/export_secrets.ps1"
            Count = $services.KeyVault
            Status = "Pending"
            Warning = "WARNING: Secret values will be exported. Handle with extreme care."
        }
    }
    elseif ($services.ContainsKey("KeyVault")) {
        $checklistItems.Secrets += @{
            Item = "Manually export or regenerate Key Vault secrets"
            Path = "keyvault/<vault-name>/"
            Count = $services.KeyVault
            Status = "Pending"
            Note = "Secret export scripts not generated (use -ExportKeyVaultSecrets to generate)"
        }
    }
    
    # AAD apps
    if ($Options.ExportAADStubs) {
        $checklistItems.Identity += @{
            Item = "Recreate Azure AD app registrations and service principals"
            Path = "metadata/identity_stubs.json"
            Status = "Pending"
        }
    }
    
    # Networking
    if ($Options.ExportNetworkGaps) {
        $checklistItems.Networking += @{
            Item = "Configure private endpoints and DNS zones"
            Path = "network_gaps_report.md"
            Status = "Pending"
        }
        $checklistItems.Networking += @{
            Item = "Recreate VNet peerings (if cross-subscription/tenant)"
            Path = "network_gaps_report.md"
            Status = "Pending"
        }
        $checklistItems.Networking += @{
            Item = "Apply route tables and NSG rules"
            Path = "network_gaps_report.md"
            Status = "Pending"
        }
    }
    
    # Monitoring
    if ($Options.ExportWorkbooks) {
        $checklistItems.Monitoring += @{
            Item = "Export and import Log Analytics workbooks"
            Path = "monitor/<workspace>/workbooks/"
            Status = "Pending"
        }
        $checklistItems.Monitoring += @{
            Item = "Export and import saved searches/queries"
            Path = "monitor/<workspace>/savedsearches/"
            Status = "Pending"
        }
    }
    
    # Quota/SKU checks
    if ($Options.ExportQuotaCheck) {
        $checklistItems.Infrastructure += @{
            Item = "Validate quotas and SKU availability in target region"
            Path = "quota_sku_checklist.md"
            Status = "Pending"
        }
    }
    
    # Classic resources
    if ($Options.ExportClassicReport) {
        $checklistItems.Infrastructure += @{
            Item = "Review and migrate classic/ASM resources"
            Path = "classic_resources_report.md"
            Status = "Pending"
        }
    }
    
    # Validation steps
    $checklistItems.Validation += @{
        Item = "Verify all resources deployed successfully"
        Status = "Pending"
    }
    $checklistItems.Validation += @{
        Item = "Test connectivity between services"
        Status = "Pending"
    }
    $checklistItems.Validation += @{
        Item = "Update application connection strings and endpoints"
        Status = "Pending"
    }
    $checklistItems.Validation += @{
        Item = "Regenerate keys/secrets in target environment"
        Status = "Pending"
    }
    $checklistItems.Validation += @{
        Item = "Configure diagnostic settings and monitoring"
        Status = "Pending"
    }
    $checklistItems.Validation += @{
        Item = "Test end-to-end workflows"
        Status = "Pending"
    }
    
    # Generate markdown
    $markdown = Generate-ChecklistMarkdown -Items $checklistItems -Summary $ExportSummary -Options $Options
    
    if (-not (Test-Path (Split-Path $checklistPath -Parent))) {
        New-Item -ItemType Directory -Path (Split-Path $checklistPath -Parent) -Force | Out-Null
    }
    
    Set-Content -Path $checklistPath -Value $markdown -Encoding UTF8
    Write-Log "SUCCESS" "Environment parity checklist generated" @{ Path = $checklistPath }
    
    return $checklistPath
}

function Generate-ChecklistMarkdown {
    param(
        [hashtable]$Items,
        [hashtable]$Summary,
        [hashtable]$Options
    )
    
    $md = @"
# Environment Parity Checklist

**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  
**Export Timestamp:** $($Summary.Timestamp)

## Overview

This checklist summarizes all operator-required actions to achieve environment parity between source and target Azure tenants.

**Total Subscriptions:** $($Summary.Subscriptions.Count)  
**Total Resource Groups:** $($Summary.TotalResourceGroups)  
**Total Resources:** $($Summary.TotalResources)

---

## ✅ Infrastructure Deployment

"@
    
    foreach ($item in $Items.Infrastructure) {
        $count = if ($item.Count) { " ($($item.Count) items)" } else { "" }
        $path = if ($item.Path) { " - See: `$item.Path" } else { "" }
        $md += @"
- [ ] $($item.Item)$count$path
"@
    }
    
    $md += @"

---

## 📦 Data Migration

"@
    
    foreach ($item in $Items.DataMigration) {
        $count = if ($item.Count) { " ($($item.Count) items)" } else { "" }
        $path = if ($item.Path) { " - See: `$item.Path" } else { "" }
        $md += @"
- [ ] $($item.Item)$count$path
"@
    }
    
    $md += @"

---

## 🔒 Secrets and Keys

"@
    
    foreach ($item in $Items.Secrets) {
        $count = if ($item.Count) { " ($($item.Count) vaults)" } else { "" }
        $path = if ($item.Path) { " - See: `$item.Path" } else { "" }
        $warning = if ($item.Warning) { "`n  ⚠️  **$($item.Warning)**" } else { "" }
        $note = if ($item.Note) { "`n  ℹ️  *$($item.Note)*" } else { "" }
        $md += @"
- [ ] $($item.Item)$count$path$warning$note
"@
    }
    
    $md += @"

---

## 👤 Identity and Access

"@
    
    foreach ($item in $Items.Identity) {
        $path = if ($item.Path) { " - See: `$item.Path" } else { "" }
        $md += @"
- [ ] $($item.Item)$path
"@
    }
    
    $md += @"

---

## 🌐 Networking

"@
    
    foreach ($item in $Items.Networking) {
        $path = if ($item.Path) { " - See: `$item.Path" } else { "" }
        $md += @"
- [ ] $($item.Item)$path
"@
    }
    
    $md += @"

---

## 📊 Monitoring and Observability

"@
    
    foreach ($item in $Items.Monitoring) {
        $path = if ($item.Path) { " - See: `$item.Path" } else { "" }
        $md += @"
- [ ] $($item.Item)$path
"@
    }
    
    $md += @"

---

## ✔️ Validation and Testing

"@
    
    foreach ($item in $Items.Validation) {
        $md += @"
- [ ] $($item.Item)
"@
    }
    
    $md += @"

---

## Notes

- Review all operator-assisted scripts before execution
- Never commit secret values to source control
- Validate all deployments in non-production first
- Update connection strings and endpoints after migration
- Regenerate all keys and secrets in target environment

## Related Documentation

- [RUNBOOK.md](docs/RUNBOOK.md) - Detailed export process
- [NETOPS_HANDOFF.md](docs/NETOPS_HANDOFF.md) - Deployment guide
- [TARGET_REBUILD_GUIDE.md](docs/TARGET_REBUILD_GUIDE.md) - Step-by-step rebuild
- [LIMITATIONS.md](docs/LIMITATIONS.md) - Known limitations

---

**Last Updated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
"@
    
    return $md
}

# Functions available when dot-sourced

