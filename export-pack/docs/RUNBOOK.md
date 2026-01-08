# Azure Export Pack - Runbook

## Overview

This runbook documents the Azure Export & Rebuild Pack execution process, what was exported, where artifacts are stored, and how to interpret the results.

## Export Process

The export pack performs the following operations in sequence:

1. **Prerequisites Check**: Verifies Azure CLI, Bicep, kubectl, and helm availability
2. **Subscription Discovery**: Lists and processes specified subscriptions
3. **Resource Group Inventory**: Enumerates all resources in each resource group
4. **ARM Template Export**: Exports ARM templates for each resource group
5. **Bicep Decompilation**: Converts ARM templates to Bicep format
6. **RBAC Export**: Captures role assignments at subscription and resource group scopes
7. **Service-Specific Exports**: Exports configuration for specialized services (AKS, Search, OpenAI, SQL, Storage, Redis, Monitor)
8. **Summary Generation**: Creates export summary with statistics and error tracking

## Output Structure

```
out/
└── YYYYMMDD-HHMMSS/
    ├── export_summary.json          # Overall export summary
    ├── ENVIRONMENT_PARITY_CHECKLIST.md  # Auto-generated checklist (NEW)
    ├── logs/
    │   ├── export_YYYYMMDD-HHMMSS.jsonl  # Structured log
    │   └── export_YYYYMMDD-HHMMSS.txt     # Transcript
    └── subscription_<name>_<id>/
        ├── metadata/
        │   ├── subscription_metadata.json
        │   ├── identity_stubs.json (if -ExportAADStubs)  # NEW
        │   └── recreate_aad_apps.ps1 (if -ExportAADStubs)  # NEW
        ├── network_gaps_report.md (if -ExportNetworkGaps)  # NEW
        ├── quota_sku_checklist.md (if -ExportQuotaCheck)  # NEW
        └── resourceGroups/
            └── <resource-group-name>/
                ├── inventory/
                │   ├── resources.json
                │   ├── resources.csv
                │   ├── resource_type_summary.json
                │   └── identified_services.json
                ├── arm/
                │   └── <rg-name>.json
                ├── bicep/
                │   └── <rg-name>.bicep
                ├── deployments/
                │   └── deployments.json
                ├── rbac/
                │   ├── rg_assignments.json
                │   └── rg_assignments.csv
                ├── aks/
                │   └── <cluster-name>/
                │       ├── cluster.json
                │       ├── nodepools.json
                │       └── workloads/ (if included)
                ├── search/
                │   └── <service-name>/
                │       ├── service.json
                │       └── export_schema.ps1 (operator-assisted)
                ├── openai/
                │   └── <account-name>/
                │       ├── account.json
                │       └── export_deployments.ps1 (operator-assisted)
                ├── sql/
                │   └── <server-name>/
                │       ├── server.json
                │       ├── firewall_rules.json
                │       ├── databases.json
                │       └── export_data.ps1 (operator-assisted, enhanced)
                ├── storage/
                │   └── <account-name>/
                │       ├── account.json
                │       ├── migrate_data.ps1 (operator-assisted, enhanced)
                │       └── azcopy_migrate_enhanced.ps1 (NEW)
                ├── redis/
                │   └── <cache-name>/
                │       └── cache.json
                ├── monitor/
                │   ├── workspaces/
                │   │   └── <workspace>/
                │   │       ├── workbooks/ (if -ExportWorkbooks)  # NEW
                │   │       │   └── export_workbooks.ps1
                │   │       └── savedsearches/ (if -ExportWorkbooks)  # NEW
                │   │           └── export_saved_searches.ps1
                │   ├── data_collection_rules.json
                │   ├── metric_alerts.json
                │   └── action_groups.json
                ├── keyvault/ (if -ExportKeyVaultSecrets)  # NEW
                │   └── <vault-name>/
                │       ├── vault.json
                │       ├── secret_names.json
                │       └── export_secrets.ps1 (operator-assisted)
                ├── network/ (if -ExportNetworkGaps)  # NEW
                │   ├── network_gaps.json
                │   └── network_gaps_report.md
                └── classic_resources_report.md (if -ExportClassicReport)  # NEW
```

## What Was Exported

###  Fully Automated Exports

- **Resource Inventory**: Complete JSON and CSV inventory of all resources
- **ARM Templates**: Full ARM templates for each resource group
- **Bicep Files**: Decompiled Bicep templates (if Bicep CLI available)
- **RBAC Assignments**: Role assignments at subscription and resource group scopes
- **AKS Configuration**: Cluster config, node pools, addon profiles
- **AKS Workloads**: Namespaces, deployments, services, ingresses (if kubectl available)
- **SQL Configuration**: Server config, firewall rules, database inventory
- **Redis Configuration**: Cache configuration (no keys)
- **Monitor Resources**: Log Analytics workspaces, DCR/DCE, alert rules, action groups
- **Storage Account Config**: Account properties (no keys/SAS)

###  Operator-Assisted Exports (Require Manual Steps)

These exports require secrets/keys that cannot be automatically retrieved. Helper scripts are generated for manual execution:

1. **Azure AI Search Schemas**
   - Location: `search/<service-name>/export_schema.ps1`
   - Requires: Search admin key (prompted at runtime)
   - Exports: Indexes, indexers, datasources, skillsets

2. **Azure OpenAI Deployments**
   - Location: `openai/<account-name>/export_deployments.ps1`
   - Requires: Contributor/Reader role (uses Azure CLI token)
   - Exports: Model deployments and configuration

3. **SQL Database Data**
   - Location: `sql/<server-name>/export_data.ps1` (enhanced with validation)
   - Requires: Storage SAS token, SQL admin credentials
   - Exports: BACPAC files for database migration
   - Includes: Import commands and validation steps

4. **Storage Data Migration**
   - Location: `storage/<account-name>/migrate_data.ps1` (enhanced)
   - Requires: Source storage key/SAS, target storage SAS
   - Generates: AzCopy command stubs with checksum verification
   - Includes: Enhanced migration script with progress tracking

5. **Key Vault Secrets** (Opt-In: `-ExportKeyVaultSecrets`)
   - Location: `keyvault/<vault-name>/export_secrets.ps1`
   - Requires: Key Vault access permissions
   - Exports: Secret values to local JSON (encrypted option available)
   -  **WARNING**: Exports secret VALUES. Handle with extreme care.

6. **Monitor Workbooks** (Opt-In: `-ExportWorkbooks`)
   - Location: `monitor/workspaces/<workspace>/workbooks/export_workbooks.ps1`
   - Requires: Log Analytics workspace access
   - Exports: Workbooks and saved searches to JSON

## What Cannot Be Exported Automatically

### 🔒 Secrets and Keys (Never Exported)

- **Key Vault Secrets**: Secret names only (if visible in ARM export)
- **Storage Account Keys**: Never exported
- **SQL Server Passwords**: Never exported
- **Redis Access Keys**: Never exported
- **Service Principal Secrets**: Never exported
- **Kubernetes Secrets**: Names only, no data

### 📋 Manual Follow-Up Required

1. **Key Vault Secrets**: Must be manually exported or regenerated in target
2. **Application Insights Connection Strings**: May need regeneration
3. **Managed Identity Credentials**: Automatically handled in target tenant
4. **Custom Script Extensions**: May contain embedded secrets
5. **Azure AD App Registrations**: Not exported (separate process required)
6. **Private Endpoint DNS Zones**: May need manual configuration
7. **Backup Vaults**: Configuration exported, but restore points not migrated

## Interpreting Export Results

### Export Summary (`export_summary.json`)

```json
{
  "Timestamp": "20240101-120000",
  "Subscriptions": [...],
  "TotalResourceGroups": 10,
  "TotalResources": 150,
  "ServicesExported": {
    "AKS": 2,
    "SQL": 3,
    "Storage": 5,
    ...
  },
  "Errors": [...],
  "Warnings": [...]
}
```

### Common Issues and Resolutions

1. **ARM Export Fails**
   - **Cause**: Resource group may contain resources that cannot be exported (e.g., classic resources)
   - **Resolution**: Check logs for specific resource errors. Some resources may need manual recreation.

2. **Bicep Decompilation Warnings**
   - **Cause**: ARM templates may contain constructs that don't perfectly translate to Bicep
   - **Resolution**: Review generated Bicep files and manually adjust if needed. ARM templates are still valid.

3. **Missing Service Exports**
   - **Cause**: Service may not be identified correctly or may be in a different resource group
   - **Resolution**: Check `identified_services.json` in inventory folder. Manually export if needed.

4. **RBAC Export Returns Empty**
   - **Cause**: Insufficient permissions to read role assignments
   - **Resolution**: Ensure account has `Reader` role at subscription/resource group scope.

5. **AKS Workload Export Fails**
   - **Cause**: kubectl not available or cluster access denied
   - **Resolution**: Install kubectl or use `-UseAdminKubeconfig` switch if admin access is available.

## Recommended Rebuild Order

When recreating resources in the target tenant, follow this order:

1. **Foundation**
   - Create resource groups
   - Apply RBAC assignments
   - Set up tags and naming conventions

2. **Networking**
   - Virtual Networks
   - Network Security Groups
   - Public IPs and Load Balancers
   - Private Endpoints

3. **Identity & Access**
   - Managed Identities
   - Service Principals (if needed)
   - Key Vaults (structure only, secrets added later)

4. **Monitoring & Logging**
   - Log Analytics Workspaces
   - Data Collection Rules/Endpoints
   - Action Groups
   - Alert Rules

5. **Data Services**
   - Storage Accounts (structure)
   - SQL Servers and Databases (structure)
   - Redis Caches
   - Data migration scripts executed

6. **AI Services**
   - Azure AI Search (structure)
   - Azure OpenAI accounts
   - Deployments and schemas

7. **Container Services**
   - Azure Container Registry
   - AKS Clusters
   - Node Pools

8. **Workloads**
   - AKS workloads (deployments, services, etc.)
   - Application configurations
   - Secrets (manually created)

9. **Finalization**
   - Diagnostic settings
   - Backup configurations
   - Private endpoint DNS
   - Custom domains and certificates

## New Features (Enhanced Exports)

### Environment Parity Checklist
- **Location**: `ENVIRONMENT_PARITY_CHECKLIST.md` (in output root)
- **Purpose**: Comprehensive checklist of all operator-required actions
- **Includes**: Infrastructure, data migration, secrets, identity, networking, monitoring, validation
- **Auto-generated**: Based on detected services and enabled export options

### Key Vault Secret Export (Opt-In)
- **Enable**: Use `-ExportKeyVaultSecrets` switch
- **Output**: Per-vault scripts in `keyvault/<vault-name>/export_secrets.ps1`
- **Security**: Requires explicit confirmation, secure prompts, optional encryption
- **Warning**: Exports secret VALUES - handle with extreme care

### Azure AD App Stubs (Opt-In)
- **Enable**: Use `-ExportAADStubs` switch
- **Output**: `metadata/identity_stubs.json` and `recreate_aad_apps.ps1`
- **Purpose**: Document discovered app registrations/service principals for recreation

### Network Gaps Report (Opt-In)
- **Enable**: Use `-ExportNetworkGaps` switch
- **Output**: `network_gaps_report.md` per subscription
- **Includes**: Private endpoints, DNS zones, VNet peerings, route tables, NSG summaries

### Quota/SKU Checklist (Opt-In)
- **Enable**: Use `-ExportQuotaCheck` switch
- **Output**: `quota_sku_checklist.md` per subscription
- **Purpose**: Validate target region quotas and SKU availability before deployment

### Classic Resource Detection (Opt-In)
- **Enable**: Use `-ExportClassicReport` switch
- **Output**: `classic_resources_report.md` per resource group
- **Purpose**: Identify classic/ASM resources requiring migration

## Next Steps

1. Review `export_summary.json` for overall status
2. Review `ENVIRONMENT_PARITY_CHECKLIST.md` for complete action list
3. Check logs in `logs/` directory for detailed execution history
4. Review identified services in each resource group's `inventory/identified_services.json`
5. Execute operator-assisted scripts for services requiring secrets
6. Review network gaps and quota checklists if generated
7. Review ARM/Bicep templates for parameterization needs
8. Follow `TARGET_REBUILD_GUIDE.md` for deployment instructions

## Support and Troubleshooting

- **Logs**: Check `logs/export_*.jsonl` for structured logs and `logs/export_*.txt` for transcript
- **Errors**: Review `export_summary.json` errors array for specific failures
- **Limitations**: See `LIMITATIONS.md` for known Azure export gaps

