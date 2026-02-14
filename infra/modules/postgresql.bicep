@description('The name of the PostgreSQL Flexible Server')
param name string

@description('The location where the PostgreSQL server will be deployed')
param location string

@description('The administrator login name for the server')
param administratorLogin string

@description('The administrator password for the server')
@secure()
param administratorPassword string

@description('The SKU name for the server (e.g., Standard_B1ms, Standard_B2s)')
param skuName string = 'Standard_B1ms'

@description('The storage size in GB')
param storageSizeGB int = 32

@description('The PostgreSQL version')
param version string = '15'

@description('Tags to be applied to the resource')
param tags object = {}

@description('Backup retention days (7-35)')
@minValue(7)
@maxValue(35)
param backupRetentionDays int = 7

@description('Enable geo-redundant backup')
param geoRedundantBackup string = 'Disabled'

@description('Enable high availability')
param highAvailability string = 'Disabled'

@description('List of allowed IP ranges for firewall rules')
param allowedIpRanges array = []

// PostgreSQL Flexible Server resource
resource postgreSQLServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: startsWith(skuName, 'Standard_B')
      ? 'Burstable'
      : (startsWith(skuName, 'Standard_D') ? 'GeneralPurpose' : 'MemoryOptimized')
  }
  properties: {
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    version: version
    storage: {
      storageSizeGB: storageSizeGB
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: geoRedundantBackup
    }
    highAvailability: {
      mode: highAvailability
    }
    network: {
      // Allow Azure services to connect
      delegatedSubnetResourceId: null
      privateDnsZoneArmResourceId: null
    }
    authConfig: {
      activeDirectoryAuth: 'Disabled'
      passwordAuth: 'Enabled' // pragma: allowlist secret
      tenantId: subscription().tenantId
    }
  }
}

// Enable required PostgreSQL extensions
// Note: This must complete before other configuration changes to avoid ServerIsBusy errors
resource postgresExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-06-01-preview' = {
  parent: postgreSQLServer
  name: 'azure.extensions'
  properties: {
    value: 'pg_trgm,uuid-ossp,vector'
    source: 'user-override'
  }
}

// Create the PantryPilot database
// Depends on extensions to serialize operations and avoid ServerIsBusy errors
resource postgreSQLDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: postgreSQLServer
  name: 'pantrypilot'
  dependsOn: [postgresExtensions]
  properties: {
    charset: 'UTF8'
    collation: 'en_US.UTF8'
  }
}

// Allow Azure services to connect
// Depends on database to serialize operations and avoid ServerIsBusy errors
resource postgreSQLFirewallRule 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = {
  parent: postgreSQLServer
  name: 'AllowAzureServices'
  dependsOn: [postgreSQLDatabase]
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Additional firewall rules for specific IP ranges
// Depends on the base firewall rule to serialize operations
resource additionalFirewallRules 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = [
  for (ipRange, index) in allowedIpRanges: {
    parent: postgreSQLServer
    name: 'AllowedRange${index}'
    dependsOn: [postgreSQLFirewallRule]
    properties: {
      startIpAddress: ipRange.startIp
      endIpAddress: ipRange.endIp
    }
  }
]

// Outputs for use in other modules
@description('The fully qualified domain name of the PostgreSQL server')
output fqdn string = postgreSQLServer.properties.fullyQualifiedDomainName

@description('The resource ID of the PostgreSQL server')
output id string = postgreSQLServer.id

@description('The name of the PostgreSQL server')
output name string = postgreSQLServer.name

@description('The name of the PostgreSQL database')
output databaseName string = postgreSQLDatabase.name
