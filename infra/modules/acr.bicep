@description('The name of the Azure Container Registry')
param name string

@description('The location where the ACR will be deployed')
param location string

@description('The SKU of the ACR (Basic, Standard, Premium)')
@allowed(['Basic', 'Standard', 'Premium'])
param sku string = 'Basic'

@description('Tags to be applied to the resource')
param tags object = {}

@description('Enable admin user for simplified authentication with GitHub Actions')
param adminUserEnabled bool = true

// Azure Container Registry resource
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    adminUserEnabled: adminUserEnabled
    publicNetworkAccess: 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
  }
}

// Outputs for use in other modules
@description('The login server for the Azure Container Registry')
output loginServer string = acr.properties.loginServer

@description('The resource ID of the Azure Container Registry')
output id string = acr.id

@description('The name of the Azure Container Registry')
output name string = acr.name

@description('The principal ID of the ACR for role assignments')
output principalId string = acr.identity.principalId
