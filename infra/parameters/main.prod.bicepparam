using '../main.bicep'

param environmentName = 'prod'
param location = readEnvironmentVariable('AZURE_LOCATION', 'Central US')
param uniqueSuffix = readEnvironmentVariable('AZURE_UNIQUE_SUFFIX', 'prod001')
param dbAdminUsername = 'pantrypilot_admin'
param dbAdminPassword = readEnvironmentVariable('DB_ADMIN_PASSWORD')
param secretKey = readEnvironmentVariable('SECRET_KEY')
