# Target Rebuild Guide

## Overview

This guide provides step-by-step instructions for rebuilding the exported Azure environment in a target Azure tenant. It assumes you have the export artifacts from the Azure Export Pack.

## Prerequisites

### Tools Required

- Azure CLI (latest version)
- Bicep CLI (recommended)
- PowerShell 5.1+ or PowerShell 7+
- kubectl (if AKS clusters are present)
- helm (if Helm charts are used)

### Permissions Required

- **Contributor** or **Owner** role on target subscription(s)
- **User Access Administrator** role (for RBAC assignments)
- Ability to create resource groups
- Ability to create service principals (if needed)

### Pre-Deployment Checklist

- [ ] Azure CLI authenticated to target tenant (`az login`)
- [ ] Target subscription selected (`az account set --subscription <id>`)
- [ ] Export artifacts reviewed and understood
- [ ] Parameter files customized for target environment
- [ ] Target naming conventions determined
- [ ] Target regions/locations identified
- [ ] Network address spaces planned (if VNets are present)

## Step-by-Step Rebuild Process

### Phase 1: Preparation

#### 1.1 Review Export Summary

```powershell
# Review export summary
$summary = Get-Content "out/YYYYMMDD-HHMMSS/export_summary.json" | ConvertFrom-Json
$summary | ConvertTo-Json -Depth 10
```

Identify:
- Number of subscriptions to recreate
- Resource groups and their purposes
- Critical services that need special attention
- Any errors or warnings from export

#### 1.2 Customize Parameter Files

1. Navigate to `iac/params/`
2. Copy appropriate template (`dev.parameters.json` or `prod.parameters.json`)
3. Create target-specific parameter file:

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "subscriptionId": {
      "value": "<target-subscription-id>"
    },
    "resourceGroupName": {
      "value": "<target-rg-name>"
    },
    "location": {
      "value": "<target-region>"
    },
    "namingPrefix": {
      "value": "<target-prefix>"
    },
    "tags": {
      "value": {
        "Environment": "Production",
        "ManagedBy": "NetOps",
        "ExportedFrom": "<source-subscription>"
      }
    }
  }
}
```

#### 1.3 Plan Resource Dependencies

Review resource dependencies in exported templates. Common dependency order:

1. Resource Groups
2. Managed Identities
3. Key Vaults (structure)
4. Virtual Networks
5. Storage Accounts
6. SQL Servers
7. Other data services
8. Compute resources (AKS, VMs)
9. Application services
10. Monitoring and alerts

### Phase 2: Foundation Deployment

#### 2.1 Create Resource Groups

```powershell
# For each resource group in export
az group create `
    --name "<target-rg-name>" `
    --location "<target-region>" `
    --tags Environment=Production ManagedBy=NetOps
```

#### 2.2 Apply RBAC (Foundation)

Create foundational RBAC assignments before deploying resources:

```powershell
# Read RBAC export
$rbac = Get-Content "out/.../rbac/subscription_assignments.json" | ConvertFrom-Json

# For each assignment (adjust principal IDs for target tenant)
foreach ($assignment in $rbac) {
    # Note: Principal IDs will differ in target tenant
    # You may need to map source principals to target principals
    
    az role assignment create `
        --role $assignment.roleDefinitionName `
        --assignee "<target-principal-id>" `
        --scope "/subscriptions/<target-sub-id>"
}
```

### Phase 3: Networking

#### 3.1 Deploy Virtual Networks

```powershell
# Deploy VNet template
az deployment group create `
    --resource-group "<target-rg-name>" `
    --template-file "out/.../resourceGroups/<rg>/bicep/<rg>.bicep" `
    --parameters "@iac/params/target.parameters.json" `
    --name "vnet-deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

**Validation**:
- [ ] VNets created with correct address spaces
- [ ] Subnets configured correctly
- [ ] Network Security Groups attached
- [ ] Route tables applied (if any)

#### 3.2 Configure Private Endpoints (if applicable)

Private endpoints may need manual configuration if DNS zones differ:

```powershell
# Create private DNS zones if needed
az network private-dns zone create `
    --resource-group "<target-rg-name>" `
    --name "privatelink.<service>.azure.com"
```

### Phase 4: Identity and Security

#### 4.1 Deploy Key Vaults

```powershell
# Deploy Key Vault from template
az deployment group create `
    --resource-group "<target-rg-name>" `
    --template-file "out/.../resourceGroups/<rg>/bicep/<rg>.bicep" `
    --parameters "@iac/params/target.parameters.json"
```

**Post-Deployment**:
- [ ] Add secrets manually (exported vaults don't contain secret values)
- [ ] Configure access policies
- [ ] Enable diagnostic settings

#### 4.2 Create/Map Service Principals

Service principals from source tenant won't exist in target. Options:

1. **Create New Service Principals**:
   ```powershell
   az ad sp create-for-rbac --name "<sp-name>" --role Contributor
   ```

2. **Update Templates**: Replace service principal IDs in templates with new ones

### Phase 5: Data Services

#### 5.1 Deploy Storage Accounts

```powershell
# Deploy storage account
az deployment group create `
    --resource-group "<target-rg-name>" `
    --template-file "out/.../resourceGroups/<rg>/bicep/<rg>.bicep" `
    --parameters "@iac/params/target.parameters.json"
```

**Post-Deployment**:
- [ ] Regenerate storage account keys
- [ ] Update connection strings in applications
- [ ] Run data migration script if needed: `storage/<account>/migrate_data.ps1`

#### 5.2 Deploy SQL Servers and Databases

```powershell
# Deploy SQL Server
az deployment group create `
    --resource-group "<target-rg-name>" `
    --template-file "out/.../resourceGroups/<rg>/bicep/<rg>.bicep" `
    --parameters "@iac/params/target.parameters.json"
```

**Post-Deployment**:
- [ ] Apply firewall rules from `sql/<server>/firewall_rules.json`
- [ ] Reset SQL admin password
- [ ] Run data export/import script: `sql/<server>/export_data.ps1`
- [ ] Update connection strings

#### 5.3 Deploy Redis Caches

```powershell
# Deploy Redis cache
az deployment group create `
    --resource-group "<target-rg-name>" `
    --template-file "out/.../resourceGroups/<rg>/bicep/<rg>.bicep" `
    --parameters "@iac/params/target.parameters.json"
```

**Post-Deployment**:
- [ ] Regenerate access keys
- [ ] Update connection strings
- [ ] Re-populate cache data (if needed)

### Phase 6: AI Services

#### 6.1 Deploy Azure AI Search

```powershell
# Deploy Search service
az deployment group create `
    --resource-group "<target-rg-name>" `
    --template-file "out/.../resourceGroups/<rg>/bicep/<rg>.bicep" `
    --parameters "@iac/params/target.parameters.json"
```

**Post-Deployment**:
- [ ] Run schema export script: `search/<service>/export_schema.ps1`
- [ ] Import indexes, indexers, datasources, skillsets
- [ ] Update credentials in skillsets
- [ ] Re-index data (if needed)

#### 6.2 Deploy Azure OpenAI

```powershell
# Deploy OpenAI account
az deployment group create `
    --resource-group "<target-rg-name>" `
    --template-file "out/.../resourceGroups/<rg>/bicep/<rg>.bicep" `
    --parameters "@iac/params/target.parameters.json"
```

**Post-Deployment**:
- [ ] Run deployments export script: `openai/<account>/export_deployments.ps1`
- [ ] Create model deployments in target account
- [ ] Update application endpoints

### Phase 7: Container Services

#### 7.1 Deploy Azure Container Registry

```powershell
# Deploy ACR
az deployment group create `
    --resource-group "<target-rg-name>" `
    --template-file "out/.../resourceGroups/<rg>/bicep/<rg>.bicep" `
    --parameters "@iac/params/target.parameters.json"
```

**Post-Deployment**:
- [ ] Migrate container images (if needed)
- [ ] Update image references in applications

#### 7.2 Deploy AKS Clusters

```powershell
# Deploy AKS cluster
az deployment group create `
    --resource-group "<target-rg-name>" `
    --template-file "out/.../resourceGroups/<rg>/bicep/<rg>.bicep" `
    --parameters "@iac/params/target.parameters.json"
```

**Post-Deployment**:
- [ ] Verify node pools: `az aks nodepool list --cluster-name <name> --resource-group <rg>`
- [ ] Get kubeconfig: `az aks get-credentials --name <name> --resource-group <rg>`
- [ ] Deploy workloads from `aks/<cluster>/workloads/`:
  ```powershell
  kubectl apply -f workloads/deployments.json
  kubectl apply -f workloads/services.json
  kubectl apply -f workloads/configmaps.json
  # Note: Secrets must be manually created
  ```
- [ ] Apply Helm releases (if any):
  ```powershell
  # Review helm_values/ directory
  helm install <release-name> <chart> -f helm_values/<release>.json
  ```

### Phase 8: Monitoring

#### 8.1 Deploy Log Analytics Workspaces

```powershell
# Deploy workspace
az deployment group create `
    --resource-group "<target-rg-name>" `
    --template-file "out/.../resourceGroups/<rg>/bicep/<rg>.bicep" `
    --parameters "@iac/params/target.parameters.json"
```

#### 8.2 Configure Data Collection

```powershell
# Apply Data Collection Rules
$dcrs = Get-Content "out/.../monitor/data_collection_rules.json" | ConvertFrom-Json
# Manually recreate DCRs or use ARM template
```

#### 8.3 Recreate Alert Rules

```powershell
# Apply metric alerts
$alerts = Get-Content "out/.../monitor/metric_alerts.json" | ConvertFrom-Json
# Recreate alerts using Azure CLI or templates
```

#### 8.4 Configure Action Groups

```powershell
# Apply action groups
$actionGroups = Get-Content "out/.../monitor/action_groups.json" | ConvertFrom-Json
# Recreate action groups (update email addresses/phone numbers for target)
```

### Phase 9: Application Configuration

#### 9.1 Update Connection Strings

For each application/service:
- [ ] Storage account connection strings
- [ ] SQL connection strings
- [ ] Redis connection strings
- [ ] Service endpoints (Search, OpenAI)
- [ ] Key Vault references

#### 9.2 Recreate Secrets

- [ ] Key Vault secrets (manually or via script)
- [ ] Kubernetes secrets
- [ ] Application settings with secrets
- [ ] Function app keys

#### 9.3 Update DNS and Certificates

- [ ] Custom domains
- [ ] SSL certificates
- [ ] Private endpoint DNS

### Phase 10: Validation and Testing

#### 10.1 Infrastructure Validation

```powershell
# Verify all resources deployed
az resource list --resource-group "<target-rg-name>" --output table

# Check deployment status
az deployment group list --resource-group "<target-rg-name>" --output table
```

#### 10.2 Service Health Checks

- [ ] AKS clusters: `kubectl get nodes`
- [ ] SQL databases: Test connection
- [ ] Storage accounts: Test read/write
- [ ] Search service: Test query
- [ ] OpenAI: Test deployment

#### 10.3 Application Testing

- [ ] Deploy test workloads
- [ ] Verify connectivity between services
- [ ] Test end-to-end workflows
- [ ] Verify monitoring and alerts

## Troubleshooting Common Issues

### Template Deployment Fails

**Check**:
- Parameter values are correct
- Target region supports resource types
- Quota limits not exceeded
- Dependencies resolved

**Resolution**:
```powershell
# Get deployment details
az deployment group show --name <deployment-name> --resource-group <rg-name>

# Check operation details
az deployment operation group list --resource-group <rg-name> --name <deployment-name>
```

### RBAC Assignment Fails

**Check**:
- Principal exists in target tenant
- Assigner has User Access Administrator role
- Scope is correct

**Resolution**:
- Verify principal ID format matches target tenant
- Create service principal if needed
- Check role definition names match

### AKS Workload Deployment Fails

**Check**:
- Cluster is running
- kubeconfig is correct
- Image pull secrets configured
- Resource quotas not exceeded

**Resolution**:
```powershell
# Verify cluster status
az aks show --name <cluster> --resource-group <rg> --query powerState

# Check node status
kubectl get nodes

# Review pod events
kubectl describe pod <pod-name>
```

## Post-Deployment Checklist

- [ ] All resources deployed successfully
- [ ] RBAC assignments applied
- [ ] Connection strings updated
- [ ] Secrets recreated
- [ ] Data migrated (if applicable)
- [ ] Monitoring configured
- [ ] Alerts tested
- [ ] Backups configured
- [ ] Documentation updated
- [ ] Team notified of new resource IDs

## Next Steps

1. **Documentation**: Update architecture diagrams and runbooks
2. **Monitoring**: Set up dashboards and alerts
3. **Backup**: Configure backup policies
4. **Security**: Enable Defender for Cloud, apply security policies
5. **Optimization**: Review and optimize resource sizes and configurations

## Support

- Review deployment logs: `az deployment group show`
- Check resource health: Azure Portal
- Review export logs: `out/.../logs/export_*.jsonl`
- Consult service-specific documentation

