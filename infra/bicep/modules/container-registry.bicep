@description('Name of the Azure Container Registry instance.')
param name string

@description('Azure region for the Azure Container Registry instance.')
param location string

@description('Tags to apply to the Azure Container Registry instance.')
param tags object = {}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  sku: {
    name: 'Basic'
  }
  tags: tags
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

@description('Azure Container Registry login server.')
output loginServer string = containerRegistry.properties.loginServer

@description('Azure Container Registry resource name.')
output name string = containerRegistry.name

@description('Azure Container Registry resource ID.')
output id string = containerRegistry.id
