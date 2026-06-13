@description('Name of the Azure Static Web App instance.')
param name string

@description('Azure region for the Azure Static Web App instance.')
param location string

@description('Tags to apply to the Azure Static Web App instance.')
param tags object = {}

resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: name
  location: location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  tags: tags
  properties: {}
}

@description('Azure Static Web App resource name.')
output name string = staticWebApp.name

@description('HTTPS URI for the Azure Static Web App default hostname.')
output uri string = 'https://${staticWebApp.properties.defaultHostname}'

@description('Azure Static Web App default hostname.')
output defaultHostname string = staticWebApp.properties.defaultHostname
