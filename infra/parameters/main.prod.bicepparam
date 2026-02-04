using '../main.bicep'

param environmentName = 'prod'
param location = readEnvironmentVariable('AZURE_LOCATION', 'Central US')
param uniqueSuffix = readEnvironmentVariable('AZURE_UNIQUE_SUFFIX', 'prod001')
param dbAdminUsername = 'pantrypilot_admin'
param dbAdminPassword = readEnvironmentVariable('DB_ADMIN_PASSWORD')
param secretKey = readEnvironmentVariable('SECRET_KEY')
param upstashRedisRestUrl = readEnvironmentVariable('UPSTASH_REDIS_REST_URL', '')
param upstashRedisRestToken = readEnvironmentVariable('UPSTASH_REDIS_REST_TOKEN', '')

// Brave Search API key for web search integration (optional - leave empty to disable)
param braveSearchApiKey = readEnvironmentVariable('BRAVE_SEARCH_API_KEY', '')

// Gemini API key for AI model access (required for production - using Gemini for chat/endpoints)
param geminiApiKey = readEnvironmentVariable('GEMINI_API_KEY', '')

// Azure OpenAI disabled in production due to subscription quota limitations
param deployAzureOpenAI = false
param useAzureOpenAIForLLM = false
param azureOpenAILocation = readEnvironmentVariable('AZURE_OPENAI_LOCATION', 'eastus2')
param azureOpenAIApiKey = readEnvironmentVariable('AZURE_OPENAI_API_KEY', '')
param azureOpenAIEndpoint = readEnvironmentVariable('AZURE_OPENAI_ENDPOINT', '')

// Model deployment names - not used in production (using Gemini instead)
// Kept for reference if switching back to Azure OpenAI in the future
param azureChatModel = readEnvironmentVariable('AZURE_OPENAI_CHAT_MODEL', 'gpt-4.1')
param azureMultimodalModel = readEnvironmentVariable('AZURE_OPENAI_MULTIMODAL_MODEL', 'gpt-5-mini')
param azureTextModel = readEnvironmentVariable('AZURE_OPENAI_TEXT_MODEL', 'gpt-5-nano')
param azureEmbeddingModel = readEnvironmentVariable('AZURE_OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')

// Azure OpenAI deployments - not used in production (using Gemini instead)
param azureOpenAIDeployments = []
