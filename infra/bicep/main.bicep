targetScope = 'resourceGroup'

@description('Azure region for the Microsoft Foundry resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Logical project name used to derive the Microsoft Foundry project and supporting resource names.')
@minLength(3)
@maxLength(16)
param projectName string = 'searchadvisor'

@description('Optional override for the Azure AI Services account name. Leave empty to derive from project name.')
param aiServicesAccountName string = ''

@description('Optional override for the Microsoft Foundry project name. Leave empty to derive from project name.')
param aiProjectName string = ''

@description('Microsoft Entra object ID of the deploying user or managed identity that should receive the Cognitive Services OpenAI User role assignment.')
param principalId string = ''

@description('Principal type for the role assignment. Use User for local development and ServicePrincipal for automation identities.')
@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
param principalType string = 'User'

@description('Default model deployment name to create in Azure AI Services for the project.')
param modelDeploymentName string = 'gpt-4o'

@description('Foundation model name to deploy into the Azure AI Services account.')
param modelName string = 'gpt-4o'

@description('Foundation model version to deploy. Update this if your target region requires a different supported version.')
param modelVersion string = '2024-05-13'

@description('Capacity units to allocate for the default model deployment.')
@minValue(1)
param modelCapacity int = 10

@description('Whether to deploy the default model during infrastructure provisioning.')
param deployDefaultModel bool = true

@description('SKU name for the Azure AI Services account.')
param aiServicesSkuName string = 'S0'

@description('Tags to apply to all provisioned infrastructure resources.')
param tags object = {
  workload: 'azure-ai-search-advisor'
  provisioner: 'bicep'
}

var resourceSuffix = uniqueString(subscription().subscriptionId, resourceGroup().id, projectName)
var resolvedAiServicesAccountName = !empty(aiServicesAccountName) ? aiServicesAccountName : take('${projectName}-foundry-${take(resourceSuffix, 6)}', 64)
var resolvedAiProjectName = !empty(aiProjectName) ? aiProjectName : take('${projectName}-project', 33)

module aiFoundry './modules/ai-foundry.bicep' = {
  name: 'ai-foundry-${uniqueString(resourceGroup().id, resolvedAiServicesAccountName, resolvedAiProjectName)}'
  params: {
    location: location
    aiServicesAccountName: resolvedAiServicesAccountName
    aiProjectName: resolvedAiProjectName
    modelDeploymentName: modelDeploymentName
    modelName: modelName
    modelVersion: modelVersion
    modelCapacity: modelCapacity
    deployDefaultModel: deployDefaultModel
    aiServicesSkuName: aiServicesSkuName
    tags: tags
  }
}

module openAiUserRole './modules/role-assignment.bicep' = if (!empty(principalId)) {
  name: 'openai-user-${uniqueString(resolvedAiServicesAccountName, principalId)}'
  params: {
    aiServicesAccountName: aiFoundry.outputs.aiServicesAccountName
    principalId: principalId
    principalType: principalType
  }
}

@description('Microsoft Foundry project endpoint that can be copied into AZURE_AI_FOUNDRY_ENDPOINT.')
output projectEndpoint string = aiFoundry.outputs.projectEndpoint

@description('Microsoft Foundry project resource name.')
output foundryProjectName string = aiFoundry.outputs.aiProjectName

@description('Azure AI Services account name backing the Foundry project.')
output aiServicesAccountName string = aiFoundry.outputs.aiServicesAccountName

@description('Default model deployment name available to the application after provisioning.')
output defaultModelDeploymentName string = modelDeploymentName
