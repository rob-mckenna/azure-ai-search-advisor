# Deploy with Azure Developer CLI

Use `azd` when you want the full application stack, not just the backend resources.

## What `azd up` deploys

The subscription-scoped template under `infra/main.bicep` provisions:

- a resource group named `rg-<environmentName>`
- Azure AI Services + Microsoft Foundry project
- Azure Container Registry
- Azure Container Apps environment + API container app
- Azure Static Web App for the React UI
- RBAC assignments for the deployer and API managed identity

`azure.yaml` maps the services like this:

- `api` -> project `.` -> host `containerapp`
- `web` -> project `./ui` -> host `staticwebapp`

## Prerequisites

- Azure Developer CLI (`azd`)
- Azure CLI (`az`)
- Bicep support in Azure CLI
- A subscription with these providers registered:
  - `Microsoft.CognitiveServices`
  - `Microsoft.MachineLearningServices`
  - `Microsoft.App`
  - `Microsoft.ContainerRegistry`
  - `Microsoft.Web`

## Step-by-step

### 1. Sign in

```bash
az login
```

### 2. Capture your Microsoft Entra object ID

```bash
AZURE_PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv)
```

This value is passed into the infrastructure so the deployer receives the `Cognitive Services OpenAI User` role.

### 3. Create or select an azd environment

```bash
azd env new
```

`azd` will prompt for an environment name. That name flows into `AZURE_ENV_NAME` and becomes part of resource names.

### 4. Store the deployer principal ID in the environment

```bash
azd env set AZURE_PRINCIPAL_ID "$AZURE_PRINCIPAL_ID"
```

### 5. Provision and deploy

```bash
azd up
```

## Outputs and post-provision hook

After provisioning, `infra/hooks/postprovision.sh` prints:

- Microsoft Foundry endpoint
- API endpoint
- Web endpoint

It also attempts to add the `Cognitive Services OpenAI User` role to the API managed identity.

## Useful follow-up commands

```bash
azd env get-values
azd deploy
azd down
```

## Tips

- Set `AZURE_LOCATION` in the azd environment if you want a region other than the default prompt choice.
- Keep `AZURE_AI_FOUNDRY_ENDPOINT` and `AZURE_AI_FOUNDRY_MODEL` from the deployment outputs for local troubleshooting.
- Use the checked-in API and UI deployment workflows for GitHub-based deployments after initial provisioning.
