# Quick Start Guide

## Prerequisites Check

```powershell
# Verify Azure CLI
az version

# Verify Bicep (optional)
az bicep version

# Verify kubectl (optional, for AKS)
kubectl version --client

# Verify helm (optional, for Helm charts)
helm version
```

## Authentication

```powershell
# Login to Azure
az login

# Verify current subscription
az account show

# List available subscriptions
az account list --output table
```

## Basic Export Commands

### Export Current Subscription

```powershell
cd export-pack
.\scripts\export_all.ps1
```

### Export Specific Subscriptions

```powershell
.\scripts\export_all.ps1 -Subscriptions "Development", "Production"
```

### Export All Subscriptions

```powershell
.\scripts\export_all.ps1 -AllSubscriptions
```

### Export with All Options

```powershell
.\scripts\export_all.ps1 `
    -Subscriptions "Development", "Production" `
    -IncludeAksWorkloads `
    -IncludeSearchSchema `
    -IncludeOpenAiDeployments `
    -OutputRoot "./my-exports"
```

### Dry Run (Test Without Exporting)

```powershell
.\scripts\export_all.ps1 -Subscriptions "Development" -DryRun
```

## Example: Export "Development" and "Production" Subscriptions

```powershell
# Navigate to export-pack directory
cd export-pack

# Run export
.\scripts\export_all.ps1 `
    -Subscriptions "Development", "Production" `
    -IncludeAksWorkloads `
    -IncludeSearchSchema `
    -IncludeOpenAiDeployments `
    -OutputRoot "./exports"
```

This will:
- Export both subscriptions
- Include AKS workloads (if kubectl available)
- Generate Search schema export scripts
- Generate OpenAI deployment export scripts
- Save output to `./exports/` directory

## Output Location

Exports are saved to: `out/YYYYMMDD-HHMMSS/` (or custom `-OutputRoot`)

## Next Steps

1. Review `out/.../export_summary.json` for export status
2. Check logs in `out/.../logs/` for details
3. Review exported templates in `out/.../resourceGroups/`
4. Execute operator-assisted scripts for services requiring secrets
5. Follow `docs/TARGET_REBUILD_GUIDE.md` for deployment

## Getting Help

- **Documentation**: See `docs/` directory
- **Logs**: Check `out/.../logs/export_*.jsonl`
- **Summary**: Review `out/.../export_summary.json`

