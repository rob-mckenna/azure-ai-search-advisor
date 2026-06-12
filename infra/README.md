# Infrastructure

This directory contains Infrastructure as Code to provision the Microsoft Foundry backend used by Azure AI Search Advisor.

```
infra/
├── bicep/              # Azure Bicep templates
│   ├── main.bicep
│   ├── main.bicepparam
│   └── modules/
│       ├── ai-foundry.bicep
│       └── role-assignment.bicep
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

Both versions provision the same resources in one resource group:

- Azure AI Services account (`Microsoft.CognitiveServices/accounts`) with local auth disabled
- Microsoft Foundry project (`Microsoft.MachineLearningServices/workspaces`, `kind: Project`) — flat architecture, no Hub
- Default `gpt-4o` model deployment on the AI Services account
- Connection from the project to the AI Services account (AAD-authenticated)
- `Cognitive Services OpenAI User` RBAC assignment for the deploying principal

> **Note:** This uses Microsoft Foundry's flat project architecture. The deprecated Hub + Project model is not used.

Authentication is Microsoft Entra ID only through `DefaultAzureCredential`. No API keys are required or enabled.

## Choose your tool

| | Bicep | Terraform |
|---|---|---|
| **Path** | `infra/bicep/` | `infra/terraform/` |
| **Docs** | Below | [`infra/terraform/README.md`](terraform/README.md) |
| **Prerequisites** | Azure CLI with Bicep | Terraform CLI + azurerm/azapi providers |
| **State** | ARM (server-side) | Local or remote backend |

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

After deployment (either tool), copy the output endpoint into `.env`:

```
AZURE_AI_FOUNDRY_ENDPOINT=<projectEndpoint output value>
AZURE_AI_FOUNDRY_MODEL=gpt-4o
```

The app authenticates with `DefaultAzureCredential` — no API keys needed.
