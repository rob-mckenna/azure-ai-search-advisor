@description('Name of the Azure Container App instance.')
param name string

@description('Azure region for the Azure Container App instance.')
param location string

@description('Resource ID of the Azure Container Apps environment that hosts the application.')
param containerAppsEnvironmentId string

@description('Azure Container Registry login server used when the image name is relative to the registry.')
param containerRegistryLoginServer string

@description('Name of the Azure Container Registry that stores deployment images.')
param containerRegistryName string

@description('Container image repository:tag or fully qualified image reference used during provisioning.')
param imageName string

@description('Tags to apply to the Azure Container App instance.')
param tags object = {}

@description('Environment variables exposed to the Azure Container App container.')
param env array = []

var resolvedImageName = contains(first(split(imageName, '/')), '.') ? imageName : '${containerRegistryLoginServer}/${imageName}'

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: containerRegistryName
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: containerRegistryLoginServer
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: resolvedImageName
          env: env
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, containerApp.name, 'AcrPull')
  scope: containerRegistry
  properties: {
    principalId: containerApp.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}

@description('Azure Container App fully qualified domain name.')
output fqdn string = containerApp.properties.configuration.ingress.fqdn

@description('Managed identity principal ID for the Azure Container App.')
output identityPrincipalId string = containerApp.identity.principalId

@description('Azure Container App resource name.')
output name string = containerApp.name

@description('HTTPS URI for the Azure Container App ingress endpoint.')
output uri string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
