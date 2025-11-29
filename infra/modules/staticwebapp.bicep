@description('The name of the Static Web App')
param name string

@description('The location where the Static Web App will be deployed')
param location string = 'West US 2'

@description('The SKU of the Static Web App (Free or Standard)')
@allowed(['Free', 'Standard'])
param sku string = 'Free'

@description('Tags to be applied to the resource')
param tags object = {}

@description('The GitHub repository URL')
param repositoryUrl string

@description('The branch to deploy from')
param branch string = 'main'

@description('The location of the app source code')
param appLocation string = '/apps/frontend'

@description('The location of the build output')
param buildLocation string = '/dist'

@description('The backend API URL to connect to (optional, can be set after Container Apps deploys)')
param backendApiUrl string = ''

@description('Enable staging environments for pull requests')
param allowConfigFileUpdates bool = true

// Static Web App resource
resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
    tier: sku
  }
  properties: {
    buildProperties: {
      appLocation: appLocation
      apiLocation: ''
      outputLocation: buildLocation
      skipGithubActionWorkflowGeneration: true // We'll manage GitHub Actions ourselves
    }
    repositoryUrl: repositoryUrl
    branch: branch
    allowConfigFileUpdates: allowConfigFileUpdates
    stagingEnvironmentPolicy: 'Enabled'
    enterpriseGradeCdnStatus: 'Disabled'
  }
}

// Configure app settings for the Static Web App (only if backendApiUrl is provided)
resource staticWebAppSettings 'Microsoft.Web/staticSites/config@2023-12-01' = if (!empty(backendApiUrl)) {
  parent: staticWebApp
  name: 'appsettings'
  properties: {
    VITE_API_URL: backendApiUrl
    NODE_ENV: contains(name, 'prod') ? 'production' : 'development'
    VITE_APP_NAME: 'PantryPilot'
    VITE_APP_VERSION: '1.0.0'
    VITE_API_TIMEOUT: '30000'
  }
}

// Custom domain configuration (optional, can be added later)
// resource customDomain 'Microsoft.Web/staticSites/customDomains@2023-12-01' = if (!empty(customDomainName)) {
//   parent: staticWebApp
//   name: customDomainName
//   properties: {
//     validationMethod: 'dns-txt-token'
//   }
// }

// Outputs for use in other modules
@description('The default hostname of the Static Web App')
output defaultHostname string = staticWebApp.properties.defaultHostname

@description('The resource ID of the Static Web App')
output id string = staticWebApp.id

@description('The name of the Static Web App')
output name string = staticWebApp.name

@description('The URL of the Static Web App')
output url string = 'https://${staticWebApp.properties.defaultHostname}'
