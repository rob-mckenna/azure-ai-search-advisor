@description('Azure region for the Microsoft Foundry resources.')
param location string = resourceGroup().location

@description('Name of the Azure AI Services account that backs the Microsoft Foundry project.')
param aiServicesAccountName string

@description('Name of the Microsoft Foundry project.')
param aiProjectName string

@description('Name of the model deployment to create in the Azure AI Services account.')
param modelDeploymentName string = 'gpt-4o'

@description('Model name to deploy into Azure AI Services.')
param modelName string = 'gpt-4o'

@description('Model version to deploy into Azure AI Services.')
param modelVersion string = '2024-05-13'

@description('Capacity units to allocate for the default model deployment.')
@minValue(1)
param modelCapacity int = 10

@description('Whether to create the default model deployment.')
param deployDefaultModel bool = true

@description('SKU name for the Azure AI Services account.')
param aiServicesSkuName string = 'S0'

@description('Tags to apply to all provisioned resources.')
param tags object = {}

// Microsoft Foundry flat architecture: project endpoint is on the AI Services account directly
var projectEndpoint = 'https://${aiServicesAccountName}.services.ai.azure.com/'

// --- Azure AI Services account (the core resource backing Microsoft Foundry) ---
resource aiServices 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: aiServicesAccountName
  location: location
  kind: 'AIServices'
  sku: {
    name: aiServicesSkuName
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
  properties: {
    customSubDomainName: aiServicesAccountName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

// --- Model deployment within the AI Services account ---
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = if (deployDefaultModel) {
  parent: aiServices
  name: modelDeploymentName
  sku: {
    name: 'Standard'
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      publisher: 'OpenAI'
      source: 'OpenAI'
      version: modelVersion
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
  }
}

// --- Microsoft Foundry project (flat architecture — no Hub required) ---
resource aiProject 'Microsoft.MachineLearningServices/workspaces@2025-06-01' = {
  name: aiProjectName
  location: location
  kind: 'Project'
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
  properties: {
    friendlyName: aiProjectName
    publicNetworkAccess: 'Enabled'
    // Flat project — no hubResourceId. Connects directly to AI Services.
  }
}

// --- Connection from the project to the AI Services account ---
resource aiServicesConnection 'Microsoft.MachineLearningServices/workspaces/connections@2025-06-01' = {
  parent: aiProject
  name: '${aiServicesAccountName}-connection'
  properties: {
    category: 'AIServices'
    target: aiServices.properties.endpoint
    authType: 'AAD'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: aiServices.id
    }
    useWorkspaceManagedIdentity: true
  }
}

@description('Resource ID of the Azure AI Services account.')
output aiServicesAccountId string = aiServices.id

@description('Name of the Azure AI Services account.')
output aiServicesAccountName string = aiServices.name

@description('Microsoft Foundry project name.')
output aiProjectName string = aiProject.name

@description('Microsoft Foundry project endpoint suitable for AZURE_AI_FOUNDRY_ENDPOINT.')
output projectEndpoint string = projectEndpoint

@description('Azure AI Services endpoint connected to the project.')
output aiServicesEndpoint string = aiServices.properties.endpoint
