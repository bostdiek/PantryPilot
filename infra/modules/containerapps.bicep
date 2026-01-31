@description('The name of the Container Apps environment')
param environmentName string

@description('The name of the backend Container App')
param backendAppName string

@description('The location where the Container Apps will be deployed')
param location string

@description('The container image for the backend app')
param containerImage string

@description('Minimum number of replicas')
param minReplicas int = 0

@description('Maximum number of replicas')
param maxReplicas int = 5

@description('vCPU allocation for the container (e.g., 0.25, 0.5, 1)')
param containerCpu string = '0.5'

@description('Memory allocation for the container (e.g., 0.5Gi, 1Gi)')
param containerMemory string = '1Gi'

@description('The URI of the Key Vault containing secrets')
param keyVaultUri string

@description('The container registry server')
param registryServer string

@description('The container registry username')
param registryUsername string

@description('The container registry password')
@secure()
param registryPassword string

@description('Tags to be applied to the resources')
param tags object = {}

@description('Allowed CORS origins for the backend API')
param corsOrigins array = []

@description('Upstash Redis REST URL for rate limiting (optional)')
param upstashRedisRestUrl string = ''

@description('Upstash Redis REST Token for rate limiting (optional)')
@secure()
param upstashRedisRestToken string = ''

@description('Email sender address for Azure Communication Services (e.g., DoNotReply@domain.com)')
param emailSenderAddress string = ''

@description('Frontend URL for email links (password reset, verification). Include https:// protocol.')
param frontendUrl string = ''

@description('Brave Search API key for web search integration (optional)')
@secure()
param braveSearchApiKey string = ''

@description('Gemini API key for AI model access (optional - leave empty to disable)')
@secure()
param geminiApiKey string = ''

@description('Azure OpenAI endpoint URL (optional - set when using Azure OpenAI)')
param azureOpenAIEndpoint string = ''

@description('Azure OpenAI API key (optional - set when using Azure OpenAI)')
@secure()
param azureOpenAIApiKey string = ''

@description('LLM provider to use: "gemini" or "azure_openai"')
param llmProvider string = 'gemini'

@description('Enable observability (Application Insights + OpenTelemetry)')
param enableObservability bool = true

// Log Analytics Workspace for Container Apps
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2025-07-01' = {
  name: '${environmentName}-logs'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

// Application Insights for backend observability
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${environmentName}-appinsights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    Request_Source: 'rest'
    RetentionInDays: 30
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-10-02-preview' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    workloadProfiles: [
      {
        workloadProfileType: 'Consumption'
        name: 'Consumption'
      }
    ]
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
  }
}

// Backend Container App
resource backendApp 'Microsoft.App/containerApps@2024-10-02-preview' = {
  name: backendAppName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
        corsPolicy: {
          allowCredentials: true
          allowedOrigins: empty(corsOrigins) ? ['*'] : corsOrigins
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']
          allowedHeaders: ['*']
        }
      }
      // Only configure ACR registry if using custom image (not quickstart placeholder)
      registries: empty(registryServer)
        ? []
        : [
            {
              server: registryServer
              username: registryUsername
              passwordSecretRef: 'acr-password' // pragma: allowlist secret
            }
          ]
      secrets: concat(
        // pragma: allowlist secret
        // ACR password only needed when using ACR
        empty(registryPassword)
          ? []
          : [
              {
                name: 'acr-password'
                value: registryPassword
              }
            ],
        // Key Vault secrets always needed, and optionally Upstash secrets if provided
        concat(
          [
            {
              name: 'database-connection-string'
              keyVaultUrl: '${keyVaultUri}secrets/dbConnectionString'
              identity: 'system'
            }
            {
              name: 'secret-key'
              keyVaultUrl: '${keyVaultUri}secrets/secretKey'
              identity: 'system'
            }
            {
              name: 'acs-connection-string'
              keyVaultUrl: '${keyVaultUri}secrets/acsConnectionString'
              identity: 'system'
            }
          ],
          // Optional Gemini API key for AI model access
          empty(geminiApiKey)
            ? []
            : [
                {
                  name: 'gemini-api-key'
                  keyVaultUrl: '${keyVaultUri}secrets/geminiApiKey'
                  identity: 'system'
                }
              ],
          // Optional Brave Search API key for web search
          empty(braveSearchApiKey)
            ? []
            : [
                {
                  name: 'brave-search-api-key'
                  keyVaultUrl: '${keyVaultUri}secrets/braveSearchApiKey'
                  identity: 'system'
                }
              ],
          // Optional Azure OpenAI API key for AI model access
          empty(azureOpenAIApiKey)
            ? []
            : [
                {
                  name: 'azure-openai-api-key'
                  keyVaultUrl: '${keyVaultUri}secrets/azureOpenAIApiKey'
                  identity: 'system'
                }
              ],
          // Optional Application Insights connection string for observability
          // Note: Uses inline value since App Insights is created by this same module
          enableObservability
            ? [
                {
                  name: 'appinsights-connection-string'
                  value: appInsights.properties.ConnectionString
                }
              ]
            : [],
          empty(upstashRedisRestUrl) || empty(upstashRedisRestToken)
            ? []
            : [
                {
                  name: 'upstash-redis-url'
                  value: upstashRedisRestUrl
                }
                {
                  name: 'upstash-redis-token'
                  value: upstashRedisRestToken
                }
              ]
        )
      )
    }
    template: {
      containers: [
        {
          image: containerImage
          name: 'pantrypilot-backend'
          resources: {
            cpu: json(containerCpu)
            memory: containerMemory
          }
          env: concat(
            [
              {
                name: 'DATABASE_URL'
                secretRef: 'database-connection-string' // pragma: allowlist secret
              }
              {
                name: 'SECRET_KEY'
                secretRef: 'secret-key' // pragma: allowlist secret
              }
              {
                name: 'ENVIRONMENT'
                value: contains(environmentName, 'prod') ? 'production' : 'development'
              }
              {
                name: 'LOG_LEVEL'
                value: 'INFO'
              }
              {
                name: 'API_V1_STR'
                value: '/api/v1'
              }
              {
                name: 'PROJECT_NAME'
                value: 'PantryPilot'
              }
              {
                name: 'VERSION'
                value: '0.1.0'
              }
              {
                name: 'ALGORITHM'
                value: 'HS256'
              }
              {
                name: 'ACCESS_TOKEN_EXPIRE_MINUTES'
                value: '30'
              }
              {
                name: 'PORT'
                value: '8000'
              }
              {
                name: 'PYTHONPATH'
                value: '/app/src'
              }
              {
                name: 'CORS_ORIGINS'
                value: join(corsOrigins, ',')
              }
              {
                name: 'AZURE_COMMUNICATION_CONNECTION_STRING'
                secretRef: 'acs-connection-string' // pragma: allowlist secret
              }
              {
                name: 'EMAIL_SENDER_ADDRESS'
                value: emailSenderAddress
              }
              {
                name: 'FRONTEND_URL'
                value: frontendUrl
              }
            ],
            empty(upstashRedisRestUrl) || empty(upstashRedisRestToken)
              ? []
              : [
                  {
                    name: 'UPSTASH_REDIS_REST_URL'
                    secretRef: 'upstash-redis-url' // pragma: allowlist secret
                  }
                  {
                    name: 'UPSTASH_REDIS_REST_TOKEN'
                    secretRef: 'upstash-redis-token' // pragma: allowlist secret
                  }
                ],
            // Optional Gemini API key for AI model access
            empty(geminiApiKey)
              ? []
              : [
                  {
                    name: 'GEMINI_API_KEY'
                    secretRef: 'gemini-api-key' // pragma: allowlist secret
                  }
                ],
            // Optional Brave Search API key for web search
            empty(braveSearchApiKey)
              ? []
              : [
                  {
                    name: 'BRAVE_SEARCH_API_KEY'
                    secretRef: 'brave-search-api-key' // pragma: allowlist secret
                  }
                ],
            // Optional Azure OpenAI for AI features (replaces Gemini when configured)
            empty(azureOpenAIEndpoint) || empty(azureOpenAIApiKey)
              ? []
              : [
                  {
                    name: 'LLM_PROVIDER'
                    value: llmProvider
                  }
                  {
                    name: 'AZURE_OPENAI_ENDPOINT'
                    value: azureOpenAIEndpoint
                  }
                  {
                    name: 'AZURE_OPENAI_API_KEY'
                    secretRef: 'azure-openai-api-key' // pragma: allowlist secret
                  }
                ],
            // Optional Application Insights for observability
            enableObservability
              ? [
                  {
                    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
                    secretRef: 'appinsights-connection-string' // pragma: allowlist secret
                  }
                  {
                    name: 'ENABLE_OBSERVABILITY'
                    value: 'true'
                  }
                  {
                    name: 'OTEL_SERVICE_NAME'
                    value: 'pantrypilot-backend'
                  }
                ]
              : []
          )
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/api/v1/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 30
              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/api/v1/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 10
              timeoutSeconds: 3
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling-rule'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

// Outputs for use in other modules
@description('The fully qualified domain name of the backend app')
output backendUrl string = 'https://${backendApp.properties.configuration.ingress.fqdn}'

@description('The resource ID of the backend Container App')
output backendAppId string = backendApp.id

@description('The system-assigned principal ID of the backend app')
output backendPrincipalId string = backendApp.identity.principalId

@description('The name of the Container Apps environment')
output environmentName string = containerAppsEnvironment.name

@description('The resource ID of the Container Apps environment')
output environmentId string = containerAppsEnvironment.id

@description('The Application Insights connection string for observability')
output appInsightsConnectionString string = enableObservability ? appInsights.properties.ConnectionString : ''

@description('The Application Insights instrumentation key (legacy, use connection string instead)')
output appInsightsInstrumentationKey string = enableObservability ? appInsights.properties.InstrumentationKey : ''
