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
param deployAzureOpenAI = true
param azureOpenAIApiKey = readEnvironmentVariable('AZURE_OPENAI_API_KEY', '')
param azureOpenAIDeployments = [
  // Chat/completion model for chat agent, recipe extraction, and title generation
  {
    name: 'gpt-4.1'
    model: 'gpt-4.1'
    version: '2025-02-24-preview'
    capacity: 10
  }
  // Multimodal model for image-based recipe extraction (reasoning model with low effort)
  {
    name: 'gpt-5-mini'
    model: 'gpt-5-mini'
    version: '2025-02-24-preview'
    capacity: 5
  }
  // Text model for fast text tasks like context generation (reasoning model with low effort)
  {
    name: 'gpt-5-nano'
    model: 'gpt-5-nano'
    version: '2025-02-24-preview'
    capacity: 10
  }
  // Embedding model for semantic search (1536 dimensions)
  {
    name: 'text-embedding-3-small'
    model: 'text-embedding-3-small'
    version: '1'
    capacity: 50
  }
]
