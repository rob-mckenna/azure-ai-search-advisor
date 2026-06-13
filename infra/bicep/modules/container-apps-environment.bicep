@description('Name of the Azure Container Apps environment.')
param name string

@description('Azure region for the Azure Container Apps environment.')
param location string

@description('Name of the Log Analytics workspace used by the Azure Container Apps environment.')
param logAnalyticsName string

@description('Tags to apply to the Azure Container Apps environment and Log Analytics workspace.')
param tags object = {}

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      searchVersion: 1
      legacy: 0
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: listKeys(logAnalyticsWorkspace.id, '2023-09-01').primarySharedKey
      }
    }
  }
}

@description('Azure Container Apps environment resource ID.')
output id string = containerAppsEnvironment.id

@description('Azure Container Apps environment resource name.')
output name string = containerAppsEnvironment.name

@description('Default DNS suffix assigned to the Azure Container Apps environment.')
output defaultDomain string = containerAppsEnvironment.properties.defaultDomain
