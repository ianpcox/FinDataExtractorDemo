# Azure Export Pack - NetOps Handoff Guide

## Purpose

This document provides NetOps teams with the information needed to recreate the exported Azure environment in a company Azure tenant. It covers required permissions, deployment procedures, and validation checklists.

## Prerequisites

### Required Permissions

The account executing the export must have:

- **Reader** role at subscription scope (minimum)
- **Contributor** role at resource group scope (for ARM exports)
- **User Access Administrator** role (for RBAC exports)
- **Azure CLI** installed and authenticated (`az login`)
- **Bicep CLI** (optional, for Bicep decompilation)

### Target Environment Requirements

For deploying to the target tenant:

- **Contributor** or **Owner** role on target subscription(s)
- **User Access Administrator** role (for RBAC assignments)
- **Azure CLI** authenticated to target tenant
- **Bicep CLI** (recommended for deployment)

## Export Artifacts Overview

The export pack produces the following artifacts:

1. **ARM Templates** (`arm/*.json`): Ready-to-deploy ARM templates per resource group
2. **Bicep Templates** (`bicep/*.bicep`): Decompiled Bicep files (may need manual adjustment)
3. **Parameter Files** (`iac/params/*.json`): Template parameter files (to be customized)
4. **RBAC Exports** (`rbac/*.json`): Role assignments for recreation
5. **Service Configurations**: Service-specific JSON exports
6. **Inventory Files**: Complete resource inventories in JSON and CSV

## Deployment Process

### Step 1: Review and Customize Parameters

1. Navigate to `iac/params/` directory
2. Copy `dev.parameters.json` or `prod.parameters.json` template
3. Update the following values for target environment:
   - Subscription ID
   - Resource group names (if different)
   - Location/region
   - Naming prefixes/suffixes
   - SKU sizes (if different)
   - Tags

### Step 2: Deploy Resource Groups

For each resource group, deploy using either ARM or Bicep:

#### Option A: ARM Template Deployment

```powershell
# Set target subscription
az account set --subscription "<target-subscription-id>"

# Create resource group (if needed)
az group create --name "<target-rg-name>" --location "<location>"

# Deploy ARM template
az deployment group create `
    --resource-group "<target-rg-name>" `
    --template-file "out/YYYYMMDD-HHMMSS/subscription_<name>/resourceGroups/<rg-name>/arm/<rg-name>.json" `
    --parameters "@iac/params/prod.parameters.json" `
    --name "export-rebuild-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

#### Option B: Bicep Template Deployment

```powershell
# Set target subscription
az account set --subscription "<target-subscription-id>"

# Create resource group (if needed)
az group create --name "<target-rg-name>" --location "<location>"

# Deploy Bicep template
az deployment group create `
    --resource-group "<target-rg-name>" `
    --template-file "out/YYYYMMDD-HHMMSS/subscription_<name>/resourceGroups/<rg-name>/bicep/<rg-name>.bicep" `
    --parameters "@iac/params/prod.parameters.json" `
    --name "export-rebuild-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

### Step 3: Apply RBAC Assignments

RBAC assignments must be recreated manually or via script:

```powershell
# Read RBAC export
$assignments = Get-Content "out/.../rbac/rg_assignments.json" | ConvertFrom-Json

# For each assignment, recreate in target
foreach ($assignment in $assignments) {
    az role assignment create `
        --role $assignment.roleDefinitionName `
        --assignee $assignment.principalName `
        --scope "/subscriptions/<target-sub-id>/resourceGroups/<target-rg-name>"
}
```

**Note**: Principal names (users, service principals) must exist in target tenant or be created first.

### Step 4: Deploy Service-Specific Configurations

#### AKS Clusters

1. Review `aks/<cluster-name>/cluster.json` for configuration
2. Deploy cluster using exported configuration or Bicep template
3. Apply workloads from `aks/<cluster-name>/workloads/`:
   ```powershell
   # Get kubeconfig
   az aks get-credentials --name <cluster-name> --resource-group <rg-name>
   
   # Apply workloads (example)
   kubectl apply -f workloads/deployments.json
   kubectl apply -f workloads/services.json
   # Note: Secrets must be manually created
   ```

#### Azure AI Search

1. Deploy Search service from ARM/Bicep template
2. Run operator-assisted schema export script:
   ```powershell
   cd "search/<service-name>"
   .\export_schema.ps1
   ```
3. Import schemas to target service using Search REST API or Azure Portal

#### Azure OpenAI

1. Deploy OpenAI account from ARM/Bicep template
2. Run deployments export script:
   ```powershell
   cd "openai/<account-name>"
   .\export_deployments.ps1
   ```
3. Create model deployments in target account

#### SQL Databases

1. Deploy SQL Server and databases from templates
2. Apply firewall rules from `sql/<server-name>/firewall_rules.json`
3. For data migration, run:
   ```powershell
   cd "sql/<server-name>"
   .\export_data.ps1
   ```
4. Import BACPAC files to target SQL Server

#### Storage Accounts

1. Deploy storage accounts from templates
2. For data migration:
   ```powershell
   cd "storage/<account-name>"
   .\migrate_data.ps1
   ```
3. Review and execute generated AzCopy commands

#### Redis Caches

1. Deploy Redis cache from template
2. Regenerate access keys in target environment
3. Update application connection strings

### Step 5: Configure Monitoring

1. Deploy Log Analytics workspaces
2. Apply Data Collection Rules (DCR) from `monitor/data_collection_rules.json`
3. Recreate alert rules from `monitor/metric_alerts.json`
4. Configure action groups from `monitor/action_groups.json`

## Deployment Validation Checklist

### Infrastructure Validation

- [ ] All resource groups created
- [ ] All resources deployed successfully
- [ ] Resource names match target naming conventions
- [ ] Tags applied correctly
- [ ] Locations/regions correct

### Networking Validation

- [ ] Virtual networks created with correct address spaces
- [ ] Network Security Groups rules applied
- [ ] Public IPs and Load Balancers configured
- [ ] Private Endpoints created (if applicable)
- [ ] DNS zones configured (if applicable)

### Identity & Access Validation

- [ ] RBAC assignments recreated
- [ ] Managed identities assigned to resources
- [ ] Service principals created (if needed)
- [ ] Key Vaults accessible with correct permissions

### Data Services Validation

- [ ] Storage accounts accessible
- [ ] SQL databases accessible and data migrated
- [ ] Redis caches accessible with new keys
- [ ] Connection strings updated in applications

### AI Services Validation

- [ ] Azure AI Search indexes created and populated
- [ ] Azure OpenAI deployments created
- [ ] Endpoints accessible and tested

### Container Services Validation

- [ ] AKS clusters running
- [ ] Node pools configured correctly
- [ ] Workloads deployed and running
- [ ] Container Registry accessible

### Monitoring Validation

- [ ] Log Analytics workspaces receiving data
- [ ] Diagnostic settings configured
- [ ] Alert rules active
- [ ] Action groups tested

## Common Deployment Issues

### Issue: Template Validation Fails

**Resolution**: 
- Review parameter file for required values
- Check for hardcoded subscription/resource group references in templates
- Ensure target location supports all resource types

### Issue: RBAC Assignment Fails

**Resolution**:
- Verify principal exists in target tenant
- Check that principal ID format matches target tenant (may differ)
- Ensure User Access Administrator role for assigner

### Issue: AKS Deployment Fails

**Resolution**:
- Verify service principal has required permissions
- Check node pool SKU availability in target region
- Review network plugin compatibility

### Issue: Service-Specific Configuration Missing

**Resolution**:
- Check if operator-assisted scripts were executed
- Review `LIMITATIONS.md` for known export gaps
- Manually recreate configurations from exported JSON

## Post-Deployment Tasks

1. **Update Application Configurations**
   - Connection strings
   - Endpoints
   - Keys and secrets (regenerated)

2. **Configure Backups**
   - Backup policies
   - Retention settings
   - Recovery points

3. **Set Up Monitoring**
   - Diagnostic settings
   - Custom dashboards
   - Alert rules

4. **Security Hardening**
   - Enable Defender for Cloud
   - Apply security policies
   - Review and update NSG rules

5. **Documentation**
   - Update runbooks
   - Document new resource IDs
   - Update architecture diagrams

## Support and Escalation

- **Export Issues**: Review `RUNBOOK.md` and export logs
- **Deployment Issues**: Check Azure deployment logs: `az deployment group show --name <deployment-name> --resource-group <rg-name>`
- **Template Issues**: Review ARM/Bicep templates and parameter files
- **Service-Specific Issues**: Refer to service-specific export folders and documentation

## Additional Resources

- [Azure Resource Manager Templates](https://docs.microsoft.com/azure/azure-resource-manager/templates/)
- [Bicep Documentation](https://docs.microsoft.com/azure/azure-resource-manager/bicep/)
- [Azure CLI Reference](https://docs.microsoft.com/cli/azure/)

