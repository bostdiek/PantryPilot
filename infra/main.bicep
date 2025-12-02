targetScope = 'resourceGroup'

@description('Environment name (dev or prod)')
@allowed(['dev', 'prod'])
param environmentName string

@description('Location for all resources')
param location string = resourceGroup().location

@description('Unique suffix for resource naming')
param uniqueSuffix string = substring(uniqueString(resourceGroup().id), 0, 6)

@description('Database admin username')
param dbAdminUsername string = 'pantrypilot_admin'

@description('Database admin password')
@secure()
param dbAdminPassword string

@description('Application secret key for JWT signing')
@secure()
param secretKey string

@description('Upstash Redis REST URL for rate limiting (optional)')
param upstashRedisRestUrl string = ''

@description('Upstash Redis REST Token for rate limiting (optional)')
@secure()
param upstashRedisRestToken string = ''

@description('Use Microsoft quickstart placeholder image for initial deployment (before CI/CD pushes real image)')
param useQuickstartImage bool = false

// Environment-specific settings
var environmentSettings = {
  dev: {
    // Cost-optimized settings for development
    acrSku: 'Basic'
    dbSku: 'Standard_B1ms'
    dbStorageSize: 32
    containerMinReplicas: 0
    containerMaxReplicas: 5
    staticWebAppSku: 'Free'
    keyVaultSku: 'standard'
  }
  prod: {
    // Production-optimized settings
    acrSku: 'Standard'
    dbSku: 'Standard_B2s'
    dbStorageSize: 128
    containerMinReplicas: 1
    containerMaxReplicas: 10
    staticWebAppSku: 'Free'
    keyVaultSku: 'standard'
  }
}

var currentSettings = environmentSettings[environmentName]

// Resource naming convention
// Key Vault: 3-24 alphanumeric chars, no consecutive hyphens
// ACR: 5-50 alphanumeric chars only (no hyphens)
var resourceNames = {
  acr: 'pantrypilotacr${environmentName}${uniqueSuffix}'
  keyVault: 'ppkv${environmentName}${uniqueSuffix}'
  postgreSQL: 'pantrypilot-db-${environmentName}-${uniqueSuffix}'
  containerAppsEnv: 'pantrypilot-env-${environmentName}-${uniqueSuffix}'
  containerAppBackend: 'pantrypilot-backend-${environmentName}'
  staticWebApp: 'pantrypilot-frontend-${environmentName}-${uniqueSuffix}'
  emailService: 'pantrypilot-email-${environmentName}-${uniqueSuffix}'
  communicationService: 'pantrypilot-acs-${environmentName}-${uniqueSuffix}'
}

// Tags for resource organization
var commonTags = {
  Environment: environmentName
  Project: 'PantryPilot'
  ManagedBy: 'Bicep'
  CostCenter: 'Development'
}

// Azure Container Registry module
module acr 'modules/acr.bicep' = {
  params: {
    name: resourceNames.acr
    location: location
    sku: currentSettings.acrSku
    tags: commonTags
  }
}

// Key Vault module for secrets management
module keyVault 'modules/keyvault.bicep' = {
  params: {
    name: resourceNames.keyVault
    location: location
    sku: currentSettings.keyVaultSku
    tags: commonTags
    secrets: {
      dbAdminPassword: dbAdminPassword
      secretKey: secretKey
      dbConnectionString: 'postgresql://${dbAdminUsername}:${dbAdminPassword}@${postgresql.outputs.fqdn}:5432/pantrypilot?sslmode=require'
      upstashRedisRestUrl: upstashRedisRestUrl
      upstashRedisRestToken: upstashRedisRestToken
    }
  }
}

// PostgreSQL Flexible Server module
module postgresql 'modules/postgresql.bicep' = {
  params: {
    name: resourceNames.postgreSQL
    location: location
    administratorLogin: dbAdminUsername
    administratorPassword: dbAdminPassword
    skuName: currentSettings.dbSku
    storageSizeGB: currentSettings.dbStorageSize
    tags: commonTags
  }
}

// Container Apps Environment and Backend App
// Use quickstart placeholder for initial deployment, or ACR image after CI/CD builds
var containerImage = useQuickstartImage
  ? 'mcr.microsoft.com/k8se/quickstart:latest'
  : '${acr.outputs.loginServer}/pantrypilot-backend:latest'

// Reference existing ACR to get admin credentials (only needed when using ACR image)
resource acrResource 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: resourceNames.acr
}

// Azure Communication Services for transactional email
module communication 'modules/communication.bicep' = {
  params: {
    emailServiceName: resourceNames.emailService
    communicationServiceName: resourceNames.communicationService
    location: 'global'
    dataLocation: 'United States'
    domainManagement: environmentName == 'prod' ? 'CustomerManaged' : 'AzureManaged'
    customDomainName: environmentName == 'prod' ? 'mail.smartmealplanner.app' : ''
    tags: commonTags
  }
}

// Reference the existing Communication Service to get connection string for Key Vault
resource communicationServiceResource 'Microsoft.Communication/communicationServices@2023-04-01' existing = {
  name: resourceNames.communicationService
  dependsOn: [communication]
}

// Store ACS connection string in Key Vault (after both Key Vault and ACS are created)
// The secret is stored as 'acsConnectionString' for backend email integration
resource acsConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVaultResource
  name: 'acsConnectionString'
  properties: {
    value: communicationServiceResource.listKeys().primaryConnectionString
    attributes: {
      enabled: true
    }
  }
  dependsOn: [keyVault, communication]
}

// Deploy Static Web App FIRST to get its actual hostname for CORS
module staticWebApp 'modules/staticwebapp.bicep' = {
  params: {
    name: resourceNames.staticWebApp
    location: 'West US 2' // Static Web Apps have limited region availability
    sku: currentSettings.staticWebAppSku
    repositoryUrl: 'https://github.com/bostdiek/PantryPilot'
    branch: environmentName == 'prod' ? 'production' : 'main'
    appLocation: '/apps/frontend'
    buildLocation: '/dist'
    // backendApiUrl will be set after Container Apps deploys
    tags: commonTags
  }
}

// CORS origins for the backend API
// Use the ACTUAL Static Web App hostname (not the resource name pattern)
var corsOrigins = [
  'https://${staticWebApp.outputs.defaultHostname}'
  'http://localhost:5173'
  'http://127.0.0.1:5173'
]

module containerApps 'modules/containerapps.bicep' = {
  params: {
    environmentName: resourceNames.containerAppsEnv
    backendAppName: resourceNames.containerAppBackend
    location: location
    containerImage: containerImage
    minReplicas: currentSettings.containerMinReplicas
    maxReplicas: currentSettings.containerMaxReplicas
    keyVaultUri: keyVault.outputs.vaultUri
    registryServer: useQuickstartImage ? '' : acr.outputs.loginServer
    registryUsername: useQuickstartImage ? '' : acrResource.listCredentials().username
    registryPassword: useQuickstartImage ? '' : acrResource.listCredentials().passwords[0].value
    corsOrigins: corsOrigins
    tags: commonTags
  }
}

// Reference the Key Vault resource for scoping role assignment
resource keyVaultResource 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: resourceNames.keyVault
}

// Role assignment to give Container Apps access to Key Vault secrets
// Scoped to the Key Vault resource, not the resource group
resource containerAppsKeyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultResource.id, resourceNames.containerAppBackend, 'Key Vault Secrets User')
  scope: keyVaultResource
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6'
    ) // Key Vault Secrets User
    principalId: containerApps.outputs.backendPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Reference the Static Web App for child resource configuration
resource staticWebAppResource 'Microsoft.Web/staticSites@2023-12-01' existing = {
  name: resourceNames.staticWebApp
}

// Update Static Web App settings with backend URL (after Container Apps is created)
resource staticWebAppSettings 'Microsoft.Web/staticSites/config@2023-12-01' = {
  parent: staticWebAppResource
  name: 'appsettings'
  properties: {
    VITE_API_URL: containerApps.outputs.backendUrl
    NODE_ENV: environmentName == 'prod' ? 'production' : 'development'
    VITE_APP_NAME: 'PantryPilot'
    VITE_APP_VERSION: '1.0.0'
    VITE_API_TIMEOUT: '30000'
  }
}

// Outputs for use in other deployments or scripts
output acrLoginServer string = acr.outputs.loginServer
output keyVaultName string = keyVault.outputs.name
output databaseFqdn string = postgresql.outputs.fqdn
output backendUrl string = containerApps.outputs.backendUrl
output staticWebAppUrl string = staticWebApp.outputs.defaultHostname
output staticWebAppName string = staticWebApp.outputs.name

// The ACS connection string is stored in Key Vault as 'acsConnectionString' for backend email consumption
@description('The name of the Communication Service for backend email integration.')
output communicationServiceName string = communication.outputs.communicationServiceName
@description('The name of the Email Service (for Azure portal reference).')
output emailServiceName string = communication.outputs.emailServiceName
output emailFromDomain string? = communication.outputs.?fromSenderDomain
