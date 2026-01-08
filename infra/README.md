# Infrastructure as Code

This directory contains infrastructure as code templates for deploying FinDataExtractorVanilla to Azure.

## Files

- `main.bicep` - Main Bicep template for Azure resources
- `deploy.ps1` - PowerShell deployment script
- `README.md` - This file

## Prerequisites

- Azure CLI installed
- Azure subscription with appropriate permissions
- PowerShell (for Windows deployment script)

## Resources Created

The Bicep template creates:

- **Storage Account**: For invoice PDFs
  - Containers: `vanilla-invoices-raw`, `vanilla-invoices-processed`
- **Azure SQL Database**: For application data (optional - can use SQLite for dev)
- **Azure Key Vault**: For secrets management
- **Azure Document Intelligence**: For invoice extraction
- **Azure Container Registry**: For Docker images
- **App Service Plan & App Service**: For container deployment (optional)

## Deployment

### Using PowerShell Script (Recommended)

```powershell
# Navigate to infra directory
cd infra

# Deploy to dev environment
.\deploy.ps1 -Environment dev

# Deploy to production
.\deploy.ps1 -Environment prod -ResourceGroupName "rg-dio-findataextractorvanilla-cace-prod"
```

### Using Azure CLI Directly

```bash
# Login to Azure
az login

# Set subscription
az account set --subscription "Your Subscription Name"

# Create resource group (if not exists)
az group create --name rg-dio-findataextractorvanilla-cace --location canadaeast

# Deploy infrastructure
az deployment group create \
  --resource-group rg-dio-findataextractorvanilla-cace \
  --template-file infra/main.bicep \
  --parameters environment=dev location=canadaeast
```

### Using GitHub Actions

The infrastructure can be deployed automatically via GitHub Actions when pushing to `main` branch. See `.github/workflows/ci-cd.yml`.

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `location` | Azure region | `canadaeast` |
| `environment` | Environment name (dev, staging, prod) | `dev` |
| `departmentPrefix` | Department prefix | `dio` |
| `projectName` | Project name | `findataextractorvanilla` |
| `regionAbbrev` | Region abbreviation | `cace` |

## Configuration

After infrastructure is deployed:

1. **Store secrets in Key Vault:**
   ```powershell
   az keyvault secret set --vault-name <key-vault-name> --name "document-intelligence-endpoint" --value "https://canadaeast.api.cognitive.microsoft.com/"
   az keyvault secret set --vault-name <key-vault-name> --name "document-intelligence-key" --value "<your-key>"
   az keyvault secret set --vault-name <key-vault-name> --name "storage-connection-string" --value "<connection-string>"
   ```

2. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

3. **Deploy application:**
   - Build and push Docker image to Container Registry
   - Deploy to App Service or Container Apps

## Outputs

The deployment outputs include:
- Storage account name and connection string
- SQL server and database connection string
- Key Vault name and URI
- Document Intelligence endpoint
- Container Registry name
- App Service URL

## Cost Optimization

For development environments:
- SQL Database: Basic tier (2 GB)
- Document Intelligence: Free tier (F0)
- App Service Plan: Basic B1

For production:
- SQL Database: Standard S2 (250 GB)
- Document Intelligence: Standard S0
- App Service Plan: Basic B2

## Security

- All storage accounts have public access disabled
- SQL Server enforces TLS 1.2 minimum
- Key Vault uses RBAC authorization
- App Service enforces HTTPS only

## Next Steps

1. Configure Application Insights for monitoring
2. Set up networking and security groups (if needed)
3. Configure backup policies
4. Set up alerts and monitoring

