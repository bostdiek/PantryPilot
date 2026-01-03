/*
  Azure Communication Services and Email Module

  Provisions ACS Email Services, domains, and Communication Services
  for transactional email (verification, password reset).
*/

metadata name = 'Azure Communication Services'
metadata description = 'Deploys Azure Communication Services and Email Services for transactional email support.'

/*
  Parameters
*/

@description('Name of the Email Service resource.')
param emailServiceName string

@description('Name of the Communication Service resource.')
param communicationServiceName string

@description('The geo-location where the resource lives. ACS resources use global location.')
param location string = 'global'

@description('The location where the service stores its data at rest.')
@allowed([
  'United States'
  'Europe'
  'UK'
  'Australia'
  'Japan'
  'France'
  'Switzerland'
])
param dataLocation string = 'United States'

@description('Resource tags.')
param tags object = {}

@description('Whether to use Azure Managed Domain (for dev) or Customer Managed Domain (for prod).')
@allowed([
  'AzureManaged'
  'CustomerManaged'
])
param domainManagement string = 'AzureManaged'

@description('Custom domain name (required if domainManagement is CustomerManaged).')
param customDomainName string = ''

@description('Enable user engagement tracking for emails.')
param userEngagementTracking bool = false

/*
  Resources
*/

// Email Service - the parent resource for email domains
resource emailService 'Microsoft.Communication/emailServices@2023-04-01' = {
  name: emailServiceName
  location: location
  tags: tags
  properties: {
    dataLocation: dataLocation
  }
}

// Azure Managed Domain - for development/testing (automatically provisioned)
resource azureManagedDomain 'Microsoft.Communication/emailServices/domains@2023-04-01' = if (domainManagement == 'AzureManaged') {
  parent: emailService
  name: 'AzureManagedDomain'
  location: location
  properties: {
    domainManagement: 'AzureManaged'
    userEngagementTracking: userEngagementTracking ? 'Enabled' : 'Disabled'
  }
}

// Customer Managed Domain - reference existing verified domain for production
// The domain must be manually created and verified in Azure Portal before deployment
resource customerManagedDomain 'Microsoft.Communication/emailServices/domains@2023-04-01' existing = if (domainManagement == 'CustomerManaged' && !empty(customDomainName)) {
  parent: emailService
  name: customDomainName
}

// Communication Service - links to email domain for sending
resource communicationService 'Microsoft.Communication/communicationServices@2023-04-01' = {
  name: communicationServiceName
  location: location
  tags: tags
  properties: {
    dataLocation: dataLocation
    linkedDomains: [
      domainManagement == 'AzureManaged' ? azureManagedDomain.id : customerManagedDomain.id
    ]
  }
}

/*
  Outputs
*/

@description('The resource ID of the Email Service.')
output emailServiceId string = emailService.id

@description('The name of the Email Service.')
output emailServiceName string = emailService.name

@description('The resource ID of the Communication Service.')
output communicationServiceId string = communicationService.id

@description('The name of the Communication Service.')
output communicationServiceName string = communicationService.name

@description('The email domain resource ID.')
output emailDomainId string = domainManagement == 'AzureManaged'
  ? azureManagedDomain.id
  : customerManagedDomain.id

@description('The sender domain (from address) for emails.')
output fromSenderDomain string? = domainManagement == 'AzureManaged'
  ? azureManagedDomain.?properties.fromSenderDomain
  : customerManagedDomain.?properties.fromSenderDomain

@description('The mail-from sender domain for the email envelope.')
output mailFromSenderDomain string? = domainManagement == 'AzureManaged'
  ? azureManagedDomain.?properties.mailFromSenderDomain
  : customerManagedDomain.?properties.mailFromSenderDomain

// WARNING: Contains sensitive DNS verification data for domain ownership.
// Only use in secure contexts. Records include SPF, DKIM, and DMARC values.
// Do NOT log or store these outputs in unsecured locations.
@description('DNS verification records for Customer Managed Domain (empty for Azure Managed). Handle securely.')
output verificationRecords object = domainManagement == 'CustomerManaged' && !empty(customDomainName)
  ? customerManagedDomain.?properties.?verificationRecords ?? {}
  : {}
