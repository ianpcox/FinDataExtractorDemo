# Azure Export Pack - Dry Run Output

**Date:** 2025-12-19 14:17:07  
**Command:** `.\export_all.ps1 -Subscriptions @("Development","Production") -DryRun`

## Summary

The dry run successfully processed **2 subscriptions**:
- **Development** (1e73b158-8845-4984-9a19-fbc26936e3b5)
- **Production** (f27c3dc6-1db4-4279-86cc-6226071c07be)

## Execution Results

### Prerequisites Check
-  Azure CLI: Available
-  Bicep CLI: Available (optional)
-  kubectl: Available (optional, for AKS workloads)
-  helm: Available (optional, for Helm charts)

### Subscription Processing

#### Development Subscription
- **Subscription ID:** 1e73b158-8845-4984-9a19-fbc26936e3b5
- **Status:**  Successfully processed
- **Resource Groups:** 0 found
- **Actions Performed:**
  - Set Azure subscription context
  - Listed resource groups
  - Checked for service-specific resources

#### Production Subscription
- **Subscription ID:** f27c3dc6-1db4-4279-86cc-6226071c07be
- **Status:**  Successfully processed
- **Resource Groups:** 0 found
- **Actions Performed:**
  - Set Azure subscription context
  - Listed resource groups
  - Checked for service-specific resources

## Export Summary

| Metric | Count |
|--------|-------|
| Subscriptions Processed | 2 |
| Resource Groups Found | 0 |
| Total Resources | 0 |
| Services Exported | 0 |
| Errors | 0 |

## Detailed Log Output

```
[INFO] Azure Export Pack - Starting export
  Timestamp: 20251219-141659
  DryRun: True
  OutputPath: .\out\20251219-141659

[INFO] Subscriptions to export
  Count: 2
  Subscriptions: 1e73b158-8845-4984-9a19-fbc26936e3b5, f27c3dc6-1db4-4279-86cc-6226071c07be

[INFO] Setting Azure subscription
  SubscriptionId: 1e73b158-8845-4984-9a19-fbc26936e3b5

[INFO] Processing subscription
  SubscriptionName: Development
  SubscriptionId: 1e73b158-8845-4984-9a19-fbc26936e3b5

[INFO] Setting Azure subscription
  SubscriptionId: 1e73b158-8845-4984-9a19-fbc26936e3b5

[INFO] Listing resource groups
  SubscriptionId: 1e73b158-8845-4984-9a19-fbc26936e3b5

[INFO] Filtered resource groups
  Found: 
  Requested: 

[INFO] Setting Azure subscription
  SubscriptionId: f27c3dc6-1db4-4279-86cc-6226071c07be

[INFO] Processing subscription
  SubscriptionName: Production
  SubscriptionId: f27c3dc6-1db4-4279-86cc-6226071c07be

[INFO] Setting Azure subscription
  SubscriptionId: f27c3dc6-1db4-4279-86cc-6226071c07be

[INFO] Listing resource groups
  SubscriptionId: f27c3dc6-1db4-4279-86cc-6226071c07be

[INFO] Filtered resource groups
  Found: 
  Requested: 

[INFO] Dry run completed - no files were written

========================================
Export Summary
========================================
Subscriptions: 2
Resource Groups: 0
Total Resources: 0
Services Exported: 0
```

## Notes

-  **Dry Run Mode:** No files were written to disk
-  **Authentication:** Successfully authenticated to Azure CLI
-  **Subscription Resolution:** Successfully resolved subscription names to IDs
-  **Tool Detection:** All required and optional tools detected
-  **Resource Groups:** No resource groups were found in either subscription
  - This may be expected if:
    - The subscriptions are empty
    - Resource groups are in different locations
    - Permissions don't allow listing resource groups

## What Would Be Exported (Actual Run)

If you run the export without `-DryRun`, the following would be created:

1. **Resource Inventories**
   - JSON inventory of all resources
   - CSV summary of resources
   - Resource type summary

2. **ARM Templates**
   - One ARM template per resource group
   - Ready for deployment to target tenant

3. **Bicep Files**
   - Decompiled Bicep templates (if Bicep CLI available)
   - May require manual adjustment

4. **RBAC Exports**
   - Role assignments at subscription level
   - Role assignments at resource group level
   - CSV summaries

5. **Service-Specific Exports**
   - AKS cluster configurations and workloads
   - Azure AI Search service configs
   - Azure OpenAI account configs
   - SQL Server configs and firewall rules
   - Storage account configs
   - Redis cache configs
   - Monitor/Log Analytics resources

6. **Operator-Assisted Scripts**
   - Search schema export scripts
   - OpenAI deployment export scripts
   - SQL data export scripts
   - Storage migration scripts

## Next Steps

To perform an actual export (without `-DryRun`), run:

```powershell
cd export-pack\scripts
.\export_all.ps1 -Subscriptions @("Development","Production")
```

Or with additional options:

```powershell
cd export-pack\scripts
.\export_all.ps1 `
    -Subscriptions @("Development","Production") `
    -IncludeAksWorkloads `
    -IncludeSearchSchema `
    -IncludeOpenAiDeployments `
    -OutputRoot "./exports"
```

This will create export artifacts in the `out/` directory (or custom `OutputRoot` if specified).

## Files Generated

The actual export would create:
- `out/YYYYMMDD-HHMMSS/export_summary.json` - Overall export summary
- `out/YYYYMMDD-HHMMSS/logs/` - Structured logs and transcript
- `out/YYYYMMDD-HHMMSS/subscription_*/` - Per-subscription exports
- `out/YYYYMMDD-HHMMSS/subscription_*/resourceGroups/*/` - Per-resource-group exports

See `docs/RUNBOOK.md` for complete details on the export structure.
