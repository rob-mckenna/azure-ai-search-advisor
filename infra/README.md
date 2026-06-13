# Infrastructure

This directory contains Infrastructure as Code to provision the Microsoft Foundry backend used by Azure AI Search Advisor.

```
infra/
├── main.bicep          # azd subscription-scoped orchestrator
├── main.parameters.json
├── hooks/
│   └── postprovision.sh
├── bicep/              # Standalone Azure Bicep templates
│   ├── main.bicep
│   ├── main.bicepparam
│   └── modules/
│       ├── ai-foundry.bicep
│       ├── container-app.bicep
│       ├── container-apps-environment.bicep
│       ├── container-registry.bicep
│       ├── role-assignment.bicep
│       └── static-web-app.bicep
└── terraform/          # Terraform configuration
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    ├── ai-services.tf
    ├── foundry-project.tf
    ├── role-assignment.tf
    ├── terraform.tfvars.example
    └── README.md
```

## What gets created

All supported deployment paths provision the Microsoft Foundry backend. The azd entry point additionally provisions the application hosting resources:

- Azure AI Services account (`Microsoft.CognitiveServices/accounts`) with local auth disabled
- Microsoft Foundry project (`Microsoft.MachineLearningServices/workspaces`, `kind: Project`) — flat architecture, no Hub
- Default `gpt-4o` model deployment on the AI Services account
- Connection from the project to the AI Services account (AAD-authenticated)
- `Cognitive Services OpenAI User` RBAC assignment for the deploying principal and API managed identity
- Azure Container Registry, Azure Container Apps environment, and Azure Container App for the API
- Azure Static Web App for the React UI

> **Note:** This uses Microsoft Foundry's flat project architecture. The deprecated Hub + Project model is not used.

Authentication is Microsoft Entra ID only through `DefaultAzureCredential`. No API keys are required or enabled.

## Choose your tool

| | azd | Bicep | Terraform |
|---|---|---|---|
| **Path** | `azure.yaml` + `infra/` | `infra/bicep/` | `infra/terraform/` |
| **Docs** | Below | Below | [`infra/terraform/README.md`](terraform/README.md) |
| **Prerequisites** | Azure Developer CLI + Azure CLI | Azure CLI with Bicep | Terraform CLI + azurerm/azapi providers |
| **State** | azd environment + ARM | ARM (server-side) | Local or remote backend |

---

## Deploy with azd

### Prerequisites

- Azure Developer CLI (`azd`)
- Azure CLI (`az`) with Bicep support
- Azure subscription with `Microsoft.CognitiveServices`, `Microsoft.MachineLearningServices`, `Microsoft.App`, `Microsoft.ContainerRegistry`, and `Microsoft.Web` registered

### Steps

```bash
az login
AZURE_PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv)
azd env new
azd env set AZURE_PRINCIPAL_ID "$AZURE_PRINCIPAL_ID"
azd up
```

The azd flow provisions Microsoft Foundry, Azure Container Apps for the API, Azure Static Web Apps for the UI, and prints the deployed endpoints from `infra/hooks/postprovision.sh`.

---

## Deploy with Bicep

### Prerequisites

- Azure CLI (`az`) with Bicep support
- Azure subscription with `Microsoft.CognitiveServices` and `Microsoft.MachineLearningServices` registered

### Steps

```bash
az login
az group create --name rg-search-advisor --location eastus

RESOURCE_GROUP=rg-search-advisor
AZURE_PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv)

az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/bicep/main.bicep \
  --parameters @infra/bicep/main.bicepparam \
  --parameters principalId="$AZURE_PRINCIPAL_ID"
```

---

## Deploy with Terraform

See [`infra/terraform/README.md`](terraform/README.md) for full instructions.

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
terraform init
terraform plan
terraform apply
```

---

## App configuration

After deployment (any tool), copy the output endpoint into `.env`:

```
AZURE_AI_FOUNDRY_ENDPOINT=<projectEndpoint output value>
AZURE_AI_FOUNDRY_MODEL=gpt-4o
```

The app authenticates with `DefaultAzureCredential` — no API keys needed.
