// Azure Bicep template for FinDataExtractorVanilla infrastructure
// Simplified version - no Redis, no complex services

@description('The Azure region for deployment (Canada East or Central)')
param location string = 'canadaeast'

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Department prefix')
param departmentPrefix string = 'dio'

@description('Project name')
param projectName string = 'findataextractorvanilla'

@description('Region abbreviation')
param regionAbbrev string = 'cace'

// Build resource names
var storageAccountName = 'sadio${projectName}${regionAbbrev}${environment}'
var sqlServerName = 'sql-${departmentPrefix}-${projectName}-${regionAbbrev}-${environment}'
var sqlDatabaseName = '${projectName}'
var keyVaultName = 'kv${departmentPrefix}${projectName}${regionAbbrev}${environment}'
var formRecognizerName = 'fr-${departmentPrefix}-${projectName}-${regionAbbrev}-${environment}'
var acrName = 'acr${departmentPrefix}${projectName}${regionAbbrev}${environment}'
var appServicePlanName = 'asp-${departmentPrefix}-${projectName}-${regionAbbrev}-${environment}'
var appServiceName = 'app-${departmentPrefix}-${projectName}-${regionAbbrev}-${environment}'

// Storage Account for invoices
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

// Blob containers (vanilla- prefixed)
resource vanillaInvoicesRawContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: 'vanilla-invoices-raw'
  parent: storageAccount::storageAccount.default
  properties: {
    publicAccess: 'None'
  }
}

resource vanillaInvoicesProcessedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: 'vanilla-invoices-processed'
  parent: storageAccount::storageAccount.default
  properties: {
    publicAccess: 'None'
  }
}

// Azure SQL Database (optional - can use SQLite for dev)
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: sqlServerName
  location: location
  properties: {
    administratorLogin: 'sqladmin'
    administratorLoginPassword: '@Microsoft.KeyVault(SecretUriWithVersion)'
    version: '12.0'
    minimalTlsVersion: '1.2'
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  name: sqlDatabaseName
  parent: sqlServer
  location: location
  sku: {
    name: environment == 'prod' ? 'S2' : 'Basic'
    tier: environment == 'prod' ? 'Standard' : 'Basic'
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: environment == 'prod' ? 268435456000 : 2147483648 // 250 GB for prod, 2 GB for dev
  }
}

// Azure Key Vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enabledForDeployment: false
    enabledForTemplateDeployment: true
    enabledForDiskEncryption: false
    enableRbacAuthorization: true
    publicNetworkAccess: 'Enabled'
  }
}

// Azure Document Intelligence (Form Recognizer)
resource formRecognizer 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: formRecognizerName
  location: location
  kind: 'FormRecognizer'
  sku: {
    name: environment == 'prod' ? 'S0' : 'F0' // Free tier for dev
  }
  properties: {
    apiProperties: {}
  }
}

// Azure Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// App Service Plan (for container deployment)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  kind: 'linux'
  properties: {
    reserved: true
  }
  sku: {
    name: environment == 'prod' ? 'B2' : 'B1' // Basic tier
    tier: 'Basic'
  }
}

// App Service (optional - for container deployment)
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: appServiceName
  location: location
  kind: 'app,linux,container'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|${containerRegistry.loginServer}/${projectName}:latest'
      alwaysOn: environment == 'prod'
      http20Enabled: true
      minTlsVersion: '1.2'
    }
    httpsOnly: true
  }
}

// Outputs
output storageAccountName string = storageAccount.name
output storageAccountConnectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
output sqlServerName string = sqlServer.name
output sqlDatabaseName string = sqlDatabase.name
output sqlConnectionString string = 'Server=tcp:${sqlServer.properties.fullyQualifiedDomainName},1433;Initial Catalog=${sqlDatabaseName};Persist Security Info=False;User ID=sqladmin;Password=@Microsoft.KeyVault(SecretUriWithVersion);MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;'
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
output formRecognizerEndpoint string = 'https://${location}.api.cognitive.microsoft.com/'
output formRecognizerName string = formRecognizer.name
output containerRegistryName string = containerRegistry.name
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output appServiceName string = appService.name
output appServiceUrl string = 'https://${appService.properties.defaultHostName}'

