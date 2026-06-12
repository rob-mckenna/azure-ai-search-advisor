using './main.bicep'

// Update principalId before deploying or pass it on the CLI with:
//   --parameters principalId=$(az ad signed-in-user show --query id -o tsv)
param location = 'eastus'
param projectName = 'searchadvisor'
param principalId = ''
param principalType = 'User'
param modelDeploymentName = 'gpt-4o'
param modelName = 'gpt-4o'
param modelVersion = '2024-05-13'
param modelCapacity = 10
