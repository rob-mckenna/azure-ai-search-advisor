# Deploy with standalone Bicep

Use the templates in `infra/bicep/` when you want direct Azure template deployment without `azd`.

## What the Bicep deployment creates

The resource-group-scoped template in `infra/bicep/main.bicep` provisions:

- Azure AI Services account
- Microsoft Foundry project
- optional default `gpt-4o` deployment
- RBAC assignment for the provided principal

## Prerequisites

- Azure CLI (`az`)
- Bicep support (`az bicep version` should work)
- An existing or newly created resource group
- Required providers registered:
  - `Microsoft.CognitiveServices`
  - `Microsoft.MachineLearningServices`

## Parameters worth knowing

`infra/bicep/main.bicep` exposes these important parameters:

- `location`
- `projectName`
- `principalId`
- `principalType`
- `modelDeploymentName`
- `modelName`
- `modelVersion`
- `modelCapacity`
- `deployDefaultModel`

The checked-in `main.bicepparam` starts with:

```bicep
param location = 'eastus'
param projectName = 'searchadvisor'
param principalId = ''
param principalType = 'User'
param modelDeploymentName = 'gpt-4o'
```

## Step-by-step

### 1. Sign in and create a resource group

```bash
az login
az group create --name rg-search-advisor --location eastus
```

### 2. Capture your Microsoft Entra object ID

```bash
RESOURCE_GROUP=rg-search-advisor
AZURE_PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv)
```

### 3. Deploy the template

```bash
az deployment group create   --resource-group "$RESOURCE_GROUP"   --template-file infra/bicep/main.bicep   --parameters @infra/bicep/main.bicepparam   --parameters principalId="$AZURE_PRINCIPAL_ID"
```

### 4. Read outputs

The deployment returns values you can copy into `.env`:

- `projectEndpoint`
- `foundryProjectName`
- `aiServicesAccountName`
- `defaultModelDeploymentName`

## Optional validation

Compile the template before deployment:

```bash
az bicep build --file infra/bicep/main.bicep
```

## After deployment

```bash
export AZURE_AI_FOUNDRY_ENDPOINT=<projectEndpoint>
export AZURE_AI_FOUNDRY_MODEL=gpt-4o
```
