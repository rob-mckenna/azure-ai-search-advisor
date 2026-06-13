targetScope = 'subscription'

@description('The azd environment name used to derive Azure resource names.')
param environmentName string

@description('Azure region for the application and Microsoft Foundry resources.')
param location string

@description('Optional Microsoft Entra object ID for the deploying principal that should receive the Cognitive Services OpenAI User role assignment.')
param principalId string = ''

var resourceGroupName = 'rg-${environmentName}'
var normalizedEnvironmentName = toLower(replace(environmentName, '-', ''))
var uniqueSuffix = take(uniqueString(subscription().subscriptionId, environmentName, location), 6)
var baseTags = {
  workload: 'azure-ai-search-advisor'
  provisioner: 'azd'
  'azd-env-name': environmentName
}
var aiServicesAccountName = take('aifoundry${normalizedEnvironmentName}${uniqueSuffix}', 64)
var aiProjectName = take('foundry-${environmentName}', 33)
var containerRegistryName = take('cr${normalizedEnvironmentName}${uniqueSuffix}', 50)
var containerAppsEnvironmentName = 'cae-${environmentName}'
var logAnalyticsName = 'log-${environmentName}'
var containerAppName = 'api-${environmentName}'
var staticWebAppName = 'web-${environmentName}'
var defaultModelDeploymentName = 'gpt-4o'
var defaultApiImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

resource environmentResourceGroup 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: resourceGroupName
  location: location
  tags: baseTags
}

module aiFoundry 'bicep/modules/ai-foundry.bicep' = {
  name: 'ai-foundry-${uniqueString(resourceGroupName, aiServicesAccountName, aiProjectName)}'
  scope: environmentResourceGroup
  params: {
    location: location
    aiServicesAccountName: aiServicesAccountName
    aiProjectName: aiProjectName
    modelDeploymentName: defaultModelDeploymentName
    modelName: defaultModelDeploymentName
    modelVersion: '2024-05-13'
    modelCapacity: 10
    deployDefaultModel: true
    aiServicesSkuName: 'S0'
    tags: baseTags
  }
}

module containerRegistry 'bicep/modules/container-registry.bicep' = {
  name: 'container-registry-${uniqueString(resourceGroupName, containerRegistryName)}'
  scope: environmentResourceGroup
  params: {
    name: containerRegistryName
    location: location
    tags: baseTags
  }
}

module containerAppsEnvironment 'bicep/modules/container-apps-environment.bicep' = {
  name: 'container-apps-environment-${uniqueString(resourceGroupName, containerAppsEnvironmentName)}'
  scope: environmentResourceGroup
  params: {
    name: containerAppsEnvironmentName
    location: location
    logAnalyticsName: logAnalyticsName
    tags: baseTags
  }
}

module containerApp 'bicep/modules/container-app.bicep' = {
  name: 'container-app-${uniqueString(resourceGroupName, containerAppName)}'
  scope: environmentResourceGroup
  params: {
    name: containerAppName
    location: location
    containerAppsEnvironmentId: containerAppsEnvironment.outputs.id
    containerRegistryLoginServer: containerRegistry.outputs.loginServer
    containerRegistryName: containerRegistry.outputs.name
    imageName: defaultApiImage
    tags: union(baseTags, {
      'azd-service-name': 'api'
    })
    env: [
      {
        name: 'AZURE_AI_FOUNDRY_ENDPOINT'
        value: aiFoundry.outputs.projectEndpoint
      }
      {
        name: 'AZURE_AI_FOUNDRY_MODEL'
        value: defaultModelDeploymentName
      }
    ]
  }
}

module staticWebApp 'bicep/modules/static-web-app.bicep' = {
  name: 'static-web-app-${uniqueString(resourceGroupName, staticWebAppName)}'
  scope: environmentResourceGroup
  params: {
    name: staticWebAppName
    location: location
    tags: union(baseTags, {
      'azd-service-name': 'web'
    })
  }
}

module deployerOpenAiUserRole 'bicep/modules/role-assignment.bicep' = if (!empty(principalId)) {
  name: 'openai-user-deployer-${uniqueString(aiServicesAccountName, principalId)}'
  scope: environmentResourceGroup
  params: {
    aiServicesAccountName: aiFoundry.outputs.aiServicesAccountName
    principalId: principalId
  }
}

module apiOpenAiUserRole 'bicep/modules/role-assignment.bicep' = {
  name: 'openai-user-api-${uniqueString(aiServicesAccountName, containerAppName)}'
  scope: environmentResourceGroup
  params: {
    aiServicesAccountName: aiFoundry.outputs.aiServicesAccountName
    principalId: containerApp.outputs.identityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

@description('Azure Container Registry endpoint used by azd container deployments.')
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer

@description('Azure Container Registry resource name.')
output AZURE_CONTAINER_REGISTRY_NAME string = containerRegistry.outputs.name

@description('Microsoft Foundry project endpoint for the application runtime.')
output AZURE_AI_FOUNDRY_ENDPOINT string = aiFoundry.outputs.projectEndpoint

@description('Default model deployment name used by the application runtime.')
output AZURE_AI_FOUNDRY_MODEL string = defaultModelDeploymentName

@description('Fully qualified URI of the deployed API container app.')
output SERVICE_API_URI string = containerApp.outputs.uri

@description('Fully qualified URI of the deployed Static Web App.')
output SERVICE_WEB_URI string = staticWebApp.outputs.uri

@description('Resource group created for the azd environment.')
output AZURE_RESOURCE_GROUP_NAME string = resourceGroupName

@description('Azure AI Services account name backing the Microsoft Foundry project.')
output AZURE_AI_FOUNDRY_ACCOUNT_NAME string = aiFoundry.outputs.aiServicesAccountName

@description('Container app managed identity principal ID.')
output SERVICE_API_IDENTITY_PRINCIPAL_ID string = containerApp.outputs.identityPrincipalId
