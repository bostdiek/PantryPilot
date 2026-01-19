@description('The name of the Key Vault')
param name string

@description('The location where the Key Vault will be deployed')
param location string

@description('The SKU of the Key Vault')
@allowed(['standard', 'premium'])
param sku string = 'standard'

@description('Tags to be applied to the resource')
param tags object = {}

@description('Secrets to store in the Key Vault')
@secure()
param secrets object = {}

@description('Enable RBAC authorization for Key Vault access')
param enableRbacAuthorization bool = true

@description('Enable soft delete for Key Vault')
param enableSoftDelete bool = true

@description('Soft delete retention days')
param softDeleteRetentionInDays int = 90

@description('Principal IDs that need access to the Key Vault secrets')
param principalIds array = []

// Key Vault resource
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: sku
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: enableRbacAuthorization
    enableSoftDelete: enableSoftDelete
    softDeleteRetentionInDays: softDeleteRetentionInDays
    enablePurgeProtection: true // Protect against accidental deletion
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow' // Can be restricted to specific networks if needed
    }
    accessPolicies: enableRbacAuthorization
      ? []
      : [
          // Access policies if RBAC is not enabled
          {
            tenantId: subscription().tenantId
            objectId: '' // This would need to be populated if not using RBAC
            permissions: {
              secrets: [
                'get'
                'list'
                'set'
                'delete'
              ]
            }
          }
        ]
  }
}

// Key Vault Secrets User role assignment for Container Apps and other services
resource keyVaultSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for principalId in principalIds: {
    name: guid(keyVault.id, principalId, 'Key Vault Secrets User')
    scope: keyVault
    properties: {
      roleDefinitionId: subscriptionResourceId(
        'Microsoft.Authorization/roleDefinitions',
        '4633458b-17de-408a-b874-0445c86b69e6'
      ) // Key Vault Secrets User
      principalId: principalId
      principalType: 'ServicePrincipal'
    }
  }
]

// Create secrets in the Key Vault
// Only create/update secrets with non-empty values to preserve existing secrets
// This prevents accidentally overwriting secrets when empty strings are passed
resource secretResources 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = [
  for secretName in filter(items(secrets), item => !empty(item.value)): {
    parent: keyVault
    name: secretName.key
    properties: {
      value: secretName.value
      attributes: {
        enabled: true
      }
    }
  }
]

// Outputs for use in other modules
@description('The name of the Key Vault')
output name string = keyVault.name

@description('The resource ID of the Key Vault')
output id string = keyVault.id

@description('The URI of the Key Vault')
output vaultUri string = keyVault.properties.vaultUri

@description('Secret references for Container Apps environment variables')
output secretReferences object = {
  databasePassword: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=database-password)'
  jwtSecretKey: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=jwt-secret-key)'
}
