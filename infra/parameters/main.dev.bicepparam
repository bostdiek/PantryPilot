using '../main.bicep'

param environmentName = 'dev'
param location = readEnvironmentVariable('AZURE_LOCATION', 'Central US')
param uniqueSuffix = readEnvironmentVariable('AZURE_UNIQUE_SUFFIX', 'dev001')
param dbAdminUsername = 'pantrypilot_admin'
param dbAdminPassword = readEnvironmentVariable('DB_ADMIN_PASSWORD')
param secretKey = readEnvironmentVariable('SECRET_KEY')

// Upstash Rate Limiting (optional - set via Key Vault or leave empty to disable)
param upstashRedisRestUrl = readEnvironmentVariable('UPSTASH_REDIS_REST_URL', '')
param upstashRedisRestToken = readEnvironmentVariable('UPSTASH_REDIS_REST_TOKEN', '')

// Brave Search API key for web search integration (optional - leave empty to disable)
param braveSearchApiKey = readEnvironmentVariable('BRAVE_SEARCH_API_KEY', '')

// Gemini API key for AI model access (optional - leave empty to disable)
param geminiApiKey = readEnvironmentVariable('GEMINI_API_KEY', '')

// Azure OpenAI for AI features (replaces Gemini when enabled)
// Bicep is idempotent - if resources exist with matching config, deployment will pass
param deployAzureOpenAI = true
param azureOpenAILocation = readEnvironmentVariable('AZURE_OPENAI_LOCATION', 'eastus2')
param azureOpenAIApiKey = readEnvironmentVariable('AZURE_OPENAI_API_KEY', '')
param azureOpenAIEndpoint = readEnvironmentVariable('AZURE_OPENAI_ENDPOINT', '')

// Deployment names used by the backend when LLM_PROVIDER=azure_openai
// These MUST match the deployment names configured in Azure OpenAI.
param azureChatModel = readEnvironmentVariable('AZURE_OPENAI_CHAT_MODEL', 'gpt-4.1')
param azureMultimodalModel = readEnvironmentVariable('AZURE_OPENAI_MULTIMODAL_MODEL', 'gpt-5-mini')
param azureTextModel = readEnvironmentVariable('AZURE_OPENAI_TEXT_MODEL', 'gpt-5-nano')
param azureEmbeddingModel = readEnvironmentVariable('AZURE_OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
param azureOpenAIDeployments = [
  // Chat/completion model for chat agent, recipe extraction, and title generation
  {
    name: 'gpt-4.1'
    model: 'gpt-4.1'
    // Use regional quota (per-region) instead of GlobalStandard
    sku: 'Standard'
    capacity: 1000
  }
  // Multimodal model for image-based recipe extraction
  {
    name: 'gpt-5-mini'
    model: 'gpt-5-mini'
    version: '2025-08-07'
    sku: 'GlobalStandard'
    capacity: 50
  }
  // Fast text model for context generation
  {
    name: 'gpt-5-nano'
    model: 'gpt-5-nano'
    version: '2025-08-07'
    sku: 'GlobalStandard'
    capacity: 50
  }
  // Embedding model for semantic search (1536 dimensions)
  {
    name: 'text-embedding-3-small'
    model: 'text-embedding-3-small'
    version: '1'
    sku: 'Standard'
    capacity: 50
  }
]
