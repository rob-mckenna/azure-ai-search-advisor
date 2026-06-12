@description('Name of the Azure AI Services account that will receive the RBAC assignment scope.')
param aiServicesAccountName string

@description('Microsoft Entra object ID for the principal that should receive access to the Azure AI Services account.')
param principalId string

@description('Principal type for the RBAC assignment.')
@allowed([
  'User'
  'ServicePrincipal'
  'Group'
])
param principalType string = 'User'

@description('Role definition ID for the RBAC role to assign. Defaults to Cognitive Services OpenAI User.')
param roleDefinitionId string = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')

resource aiServices 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: aiServicesAccountName
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiServices.id, principalId, roleDefinitionId)
  scope: aiServices
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: roleDefinitionId
  }
}

@description('Role assignment resource ID.')
output roleAssignmentId string = roleAssignment.id
