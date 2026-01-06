# Azure Export Pack - Known Limitations

This document lists known limitations and gaps in the Azure export process. These limitations are inherent to Azure's export capabilities and security model.

## General Limitations

### ARM Template Export Limitations

1. **Classic Resources**: Classic (ASM) resources cannot be exported via ARM templates
   - **Workaround**: Manually document and recreate using ARM templates

2. **Some Resource Types**: Certain resource types are not fully exportable:
   - Azure AD resources (App Registrations, Service Principals)
   - Subscription-level resources (some policies, blueprints)
   - Management Group resources
   - Tenant-level configurations

3. **Resource Dependencies**: ARM exports may not capture all implicit dependencies
   - **Workaround**: Review exported templates and add missing dependencies

4. **Parameterization**: Exported templates may contain hardcoded values
   - **Workaround**: Manually parameterize templates before deployment

### Bicep Decompilation Limitations

1. **Imperfect Translation**: Some ARM template constructs don't translate perfectly to Bicep
   - **Workaround**: Review and manually adjust generated Bicep files

2. **Complex Expressions**: Complex ARM template expressions may require manual conversion
   - **Workaround**: Use ARM templates directly or manually rewrite expressions

## Service-Specific Limitations

### Azure Kubernetes Service (AKS)

1. **Workload Export**: Requires kubectl and cluster access
   - **Limitation**: If kubectl unavailable or access denied, workloads not exported
   - **Workaround**: Manual export or use `-UseAdminKubeconfig` switch

2. **Secrets**: Kubernetes Secrets are exported as names only (no data)
   - **Workaround**: Manually recreate secrets in target cluster

3. **Helm Charts**: Helm chart source not exported, only values
   - **Workaround**: Re-download charts from source or use exported values

4. **Custom Resource Definitions (CRDs)**: May not be fully captured
   - **Workaround**: Manually export CRD definitions

### Azure AI Search

1. **Schema Export**: Requires admin key (not automatically available)
   - **Limitation**: Default export only captures ARM-level properties
   - **Workaround**: Run operator-assisted script `export_schema.ps1`

2. **Index Data**: Index content/data is not exported
   - **Workaround**: Re-index from source data or use Search indexer

3. **Skillset Credentials**: Embedded credentials in skillsets are redacted
   - **Workaround**: Manually update credentials in target environment

### Azure OpenAI

1. **Deployment Export**: May require management API access
   - **Limitation**: Some deployments may not export via CLI
   - **Workaround**: Use operator-assisted script or Azure Portal

2. **Model Access**: Custom models not exported
   - **Workaround**: Re-upload custom models to target account

3. **Fine-Tuned Models**: Fine-tuning data and models not exported
   - **Workaround**: Re-run fine-tuning in target environment

### Azure SQL

1. **Database Data**: Data export requires storage SAS token
   - **Limitation**: BACPAC export not automated
   - **Workaround**: Run operator-assisted script `export_data.ps1`

2. **Backup Retention**: Backup retention policies may not be fully captured
   - **Workaround**: Manually configure in target environment

3. **Audit Logs**: Audit log configurations exported, but historical logs not migrated
   - **Workaround**: Export audit logs separately if needed

### Azure Storage

1. **Data Migration**: Requires storage keys or SAS tokens
   - **Limitation**: Data not automatically migrated
   - **Workaround**: Run operator-assisted script `migrate_data.ps1`

2. **File Share Snapshots**: Snapshots not exported
   - **Workaround**: Manually create snapshots in target if needed

3. **Blob Lifecycle Policies**: May not be fully captured
   - **Workaround**: Review and manually recreate policies

### Azure Cache for Redis

1. **Access Keys**: Keys never exported (security requirement)
   - **Workaround**: Regenerate keys in target environment

2. **Data**: Cache data not exported
   - **Workaround**: Cache will be empty in target environment

3. **Persistence**: RDB/AOF persistence files not exported
   - **Workaround**: Re-populate cache from source data

### Azure Monitor / Log Analytics

1. **Log Data**: Historical log data not exported
   - **Workaround**: Export logs separately if retention required

2. **Saved Queries**: Some saved queries may not export
   - **Workaround**: Manually recreate in target workspace

3. **Workbooks**: Workbooks may require manual export
   - **Workaround**: Export workbooks separately via Azure Portal or API

4. **Custom Metrics**: Custom metric definitions may not be fully captured
   - **Workaround**: Review and manually recreate

## Security and Secrets

### Never Exported (By Design)

1. **Key Vault Secrets**: Secret values never exported
   - **Workaround**: Manually export secrets or regenerate in target

2. **Storage Account Keys**: Never exported
   - **Workaround**: Regenerate keys in target environment

3. **SQL Server Passwords**: Never exported
   - **Workaround**: Reset passwords in target environment

4. **Service Principal Secrets**: Never exported
   - **Workaround**: Create new service principals or reset secrets

5. **Managed Identity Credentials**: Automatically handled (no export needed)

6. **Connection Strings with Secrets**: Redacted in exports
   - **Workaround**: Manually update with new keys/secrets

### Partially Exported

1. **Key Vault Structure**: Vaults and secret names exported, values not
   - **Workaround**: Manually export secret values or regenerate

2. **Application Insights Connection Strings**: May be redacted
   - **Workaround**: Regenerate connection strings in target

## Networking Limitations

1. **Private Endpoint DNS**: DNS zone configurations may need manual setup
   - **Workaround**: Manually configure private DNS zones

2. **Route Tables**: Custom routes may not be fully captured
   - **Workaround**: Review and manually recreate routes

3. **Virtual Network Peerings**: Cross-subscription peerings may need manual recreation
   - **Workaround**: Recreate peerings in target environment

4. **ExpressRoute Circuits**: Circuit configurations exported, but physical connections not
   - **Workaround**: Coordinate with network team for circuit provisioning

## Identity and Access Limitations

1. **Azure AD Resources**: Not exported (separate tenant)
   - **Workaround**: Manually recreate App Registrations, Service Principals
   - **Note**: Principal IDs will differ in target tenant

2. **Custom Role Definitions**: May need manual recreation
   - **Workaround**: Export role definitions separately and recreate

3. **Conditional Access Policies**: Not exported
   - **Workaround**: Manually recreate in target tenant

## Data and Backup Limitations

1. **Backup Vaults**: Configuration exported, but recovery points not migrated
   - **Workaround**: Perform new backups in target environment

2. **Snapshot Data**: VM snapshots, disk snapshots not exported
   - **Workaround**: Create new snapshots in target if needed

3. **Archive Storage**: Archived blob data not automatically migrated
   - **Workaround**: Use AzCopy or Storage migration script

## Application-Specific Limitations

1. **App Service Configurations**: Some app settings with secrets may be redacted
   - **Workaround**: Manually update app settings in target

2. **Function App Keys**: Function keys not exported
   - **Workaround**: Regenerate keys in target environment

3. **API Management**: Some configurations may require manual export
   - **Workaround**: Use APIM export/import tools separately

4. **Container Instances**: Environment variables with secrets redacted
   - **Workaround**: Manually update in target environment

## Regional and SKU Limitations

1. **SKU Availability**: Some SKUs may not be available in target region
   - **Workaround**: Use equivalent SKUs or different regions

2. **Feature Availability**: Some features may not be available in target region
   - **Workaround**: Review feature availability and adjust configurations

3. **Quota Limits**: Target subscription may have different quota limits
   - **Workaround**: Request quota increases or adjust resource sizes

## Best Practices to Mitigate Limitations

1. **Review Exports**: Always review exported templates and configurations
2. **Test Deployments**: Test deployments in non-production environment first
3. **Document Gaps**: Document any missing configurations during export
4. **Manual Follow-Up**: Plan for manual configuration of services requiring secrets
5. **Validation**: Validate all deployments against source environment
6. **Incremental Migration**: Consider phased migration for complex environments

## Getting Help

- Review export logs: `logs/export_*.jsonl`
- Check export summary: `export_summary.json`
- Refer to service-specific documentation
- Consult Azure documentation for specific services

