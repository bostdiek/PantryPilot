@description('The name of the Azure OpenAI resource')
param name string

@description('The location where the Azure OpenAI resource will be deployed')
param location string

@description('The SKU of the Azure OpenAI resource')
@allowed(['S0'])
param sku string = 'S0'

@description('Tags to be applied to the resource')
param tags object = {}

@description('Enable public network access')
param publicNetworkAccess bool = true

@description('Custom subdomain name for the Azure OpenAI resource (required for token-based auth)')
param customSubDomainName string = name

@description('Model deployments to create')
param deployments array = []

// Azure OpenAI resource (Cognitive Services account with kind=OpenAI)
resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  kind: 'OpenAI'
  tags: tags
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: customSubDomainName
    publicNetworkAccess: publicNetworkAccess ? 'Enabled' : 'Disabled'
    networkAcls: {
      defaultAction: publicNetworkAccess ? 'Allow' : 'Deny'
      bypass: 'AzureServices'
    }
    // Allow key-based auth for development. For production, consider:
    // - Setting disableLocalAuth: true to enforce Azure AD authentication only
    // - Using managed identity instead of API keys for better security
    disableLocalAuth: false
  }
}

// Model deployments (e.g., gpt-4o-mini, gpt-4.1)
resource modelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = [
  for deployment in deployments: {
    parent: openai
    name: deployment.name
    sku: {
      name: 'Standard'
      capacity: deployment.?capacity ?? 10
    }
    properties: {
      model: {
        format: 'OpenAI'
        name: deployment.model
        version: deployment.?version ?? null
      }
      versionUpgradeOption: deployment.?versionUpgradeOption ?? 'OnceNewDefaultVersionAvailable'
    }
  }
]

// Outputs for use in other modules
@description('The endpoint URL for the Azure OpenAI resource')
output endpoint string = openai.properties.endpoint

@description('The resource ID of the Azure OpenAI resource')
output id string = openai.id

@description('The name of the Azure OpenAI resource')
output name string = openai.name

@description('The principal ID of the Azure OpenAI managed identity')
output principalId string = openai.identity.principalId

@description('The deployed model names')
output deploymentNames array = [for (deployment, i) in deployments: modelDeployments[i].name]

// Do not output API keys (secrets) from Bicep modules.
// The root template should store keys in Key Vault (or use managed identity).
