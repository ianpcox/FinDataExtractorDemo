# Azure Export & Rebuild Pack

A production-grade PowerShell toolkit for exporting Azure environments and generating artifacts for NetOps teams to recreate resources in target Azure tenants.

## Overview

This pack provides comprehensive, read-only export capabilities for Azure resources, generating:
- ARM templates and Bicep decompilations
- Resource inventories and service-specific configurations
- RBAC exports
- Operator-assisted scripts for services requiring secrets
- Complete documentation for handoff and rebuild

## Features

✅ **Comprehensive Export**
- Resource inventories (JSON + CSV)
- ARM templates per resource group
- Bicep decompilation
- Service-specific configurations (AKS, Search, OpenAI, SQL, Storage, Redis, Monitor)
- RBAC assignments

✅ **Security-First**
- Never exports secrets or keys
- Redacts sensitive data from outputs
- Operator-assisted scripts for secret-requiring operations
- Secure input handling

✅ **Production-Ready**
- Comprehensive error handling and retries
- Structured logging (JSON + transcript)
- Idempotent operations
- Dry-run mode

✅ **Service Coverage**
- AKS clusters and workloads
- Azure AI Search
- Azure OpenAI
- Azure SQL (servers, databases, firewall rules)
- Storage Accounts
- Redis Caches
- Log Analytics and Monitor resources

## Quick Start

### Prerequisites

- Azure CLI installed and authenticated (`az login`)
- PowerShell 5.1+ or PowerShell 7+
- Bicep CLI (optional, for Bicep decompilation)
- kubectl (optional, for AKS workload export)
- helm (optional, for Helm chart export)

### Basic Usage

```powershell
# Export current subscription
.\scripts\export_all.ps1

# Export specific subscriptions
.\scripts\export_all.ps1 -Subscriptions "Development", "Production"

# Export all subscriptions
.\scripts\export_all.ps1 -AllSubscriptions

# Export specific resource groups
.\scripts\export_all.ps1 -Subscriptions "Development" -ResourceGroups "rg-app", "rg-data"

# Include AKS workloads (requires kubectl)
.\scripts\export_all.ps1 -IncludeAksWorkloads

# Dry run (see what would be exported)
.\scripts\export_all.ps1 -DryRun
```

### Example: Export Two Subscriptions

```powershell
.\scripts\export_all.ps1 `
    -Subscriptions "Development", "Production" `
    -IncludeAksWorkloads `
    -IncludeSearchSchema `
    -OutputRoot "./exports"
```

## Command Reference

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `-Subscriptions` | string[] | Current sub | Subscription IDs or names to export |
| `-AllSubscriptions` | switch | false | Export all accessible subscriptions |
| `-ResourceGroups` | string[] | All RGs | Specific resource groups to export |
| `-IncludeAksWorkloads` | switch | true | Export AKS workloads (requires kubectl) |
| `-IncludeSearchSchema` | switch | false | Export Search schemas (requires admin key) |
| `-IncludeOpenAiDeployments` | switch | false | Export OpenAI deployments |
| `-IncludeSqlConfig` | switch | true | Export SQL configuration |
| `-IncludeStorageInventory` | switch | true | Export storage inventory |
| `-OutputRoot` | string | "./out" | Root directory for export output |
| `-UseAdminKubeconfig` | switch | false | Use admin kubeconfig for AKS |
| `-DryRun` | switch | false | Print commands without executing |

## Output Structure

```
out/
└── YYYYMMDD-HHMMSS/
    ├── export_summary.json
    ├── logs/
    │   ├── export_*.jsonl
    │   └── export_*.txt
    └── subscription_<name>_<id>/
        ├── metadata/
        └── resourceGroups/
            └── <rg-name>/
                ├── inventory/
                ├── arm/
                ├── bicep/
                ├── rbac/
                ├── aks/
                ├── search/
                ├── openai/
                ├── sql/
                ├── storage/
                ├── redis/
                └── monitor/
```

## Documentation

- **[RUNBOOK.md](docs/RUNBOOK.md)**: Detailed export process documentation
- **[NETOPS_HANDOFF.md](docs/NETOPS_HANDOFF.md)**: Guide for NetOps teams
- **[LIMITATIONS.md](docs/LIMITATIONS.md)**: Known limitations and workarounds
- **[TARGET_REBUILD_GUIDE.md](docs/TARGET_REBUILD_GUIDE.md)**: Step-by-step rebuild instructions

## Security

### What is NOT Exported

- Key Vault secret values
- Storage account keys
- SQL server passwords
- Redis access keys
- Service principal secrets
- Kubernetes secret data (names only)
- Connection strings with embedded secrets

### Operator-Assisted Scripts

For services requiring secrets, the pack generates operator-assisted scripts that:
- Prompt for secrets at runtime (never stored)
- Use secure input methods
- Clear secrets from memory after use
- Generate migration commands without embedding secrets

## Service-Specific Exports

### AKS
- Cluster configuration
- Node pools
- Workloads (deployments, services, ingresses)
- ConfigMaps
- Secret names (no data)
- Helm releases (if available)

### Azure AI Search
- Service configuration
- Indexes, indexers, datasources, skillsets (via operator script)

### Azure OpenAI
- Account configuration
- Model deployments (via operator script)

### Azure SQL
- Server configuration
- Firewall rules
- Database inventory
- Data export scripts (BACPAC)

### Storage Accounts
- Account configuration
- Container/share listing scripts
- AzCopy command generation

### Redis
- Cache configuration (no keys)

### Monitor
- Log Analytics workspaces
- Data Collection Rules/Endpoints
- Alert rules
- Action groups

## Troubleshooting

### Common Issues

1. **ARM Export Fails**
   - Check logs for specific resource errors
   - Some classic resources cannot be exported
   - Review `export_summary.json` for details

2. **Bicep Decompilation Warnings**
   - Generated Bicep may need manual adjustment
   - ARM templates are still valid for deployment

3. **Missing Service Exports**
   - Check `identified_services.json` in inventory
   - Verify service is in expected resource group

4. **RBAC Export Empty**
   - Ensure account has `Reader` role at subscription scope
   - Check `User Access Administrator` role for assignments

5. **AKS Workload Export Fails**
   - Install kubectl or use `-UseAdminKubeconfig`
   - Verify cluster access permissions

## Best Practices

1. **Review Before Deploying**
   - Always review exported templates
   - Customize parameter files for target environment
   - Test in non-production first

2. **Incremental Migration**
   - Start with foundation (RGs, networking)
   - Then data services
   - Finally applications and workloads

3. **Security**
   - Never commit secrets to source control
   - Regenerate all keys in target environment
   - Review RBAC assignments carefully

4. **Validation**
   - Validate all deployments
   - Test connectivity between services
   - Verify monitoring and alerts

## Support

- Review export logs: `out/.../logs/export_*.jsonl`
- Check export summary: `out/.../export_summary.json`
- Consult documentation in `docs/` directory
- Review service-specific export folders

## License

This toolkit is provided as-is for Azure environment migration purposes.

## Contributing

This is a production toolkit. Modify scripts as needed for your environment, but maintain:
- Read-only operations
- No secret export
- Comprehensive logging
- Error handling

