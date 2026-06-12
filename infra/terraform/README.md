# Terraform infrastructure

This directory contains a Terraform equivalent of the Bicep deployment under `infra/`. It provisions the same flat Microsoft Foundry architecture for Azure AI Search Advisor.

## What gets created

- Azure AI Services account (`Microsoft.CognitiveServices/accounts`) with `disableLocalAuth` equivalent enabled (`local_auth_enabled = false`)
- Optional default OpenAI model deployment on the AI Services account
- Microsoft Foundry project (`Microsoft.MachineLearningServices/workspaces`, `kind = "Project"`) created with `azapi_resource`
- AAD-authenticated connection from the Foundry project directly to the AI Services account
- `Cognitive Services OpenAI User` RBAC assignment for the deploying principal

> **Important:** This uses the flat Foundry project model only. It does **not** create a Hub (`kind: Hub`) resource.

## Prerequisites

- Terraform 1.6+
- Azure CLI (`az`) logged into the target subscription
- Permission to create Azure AI Services, Machine Learning, and RBAC resources in an existing resource group
- Azure resource providers registered if your subscription has not used them yet:
  - `Microsoft.CognitiveServices`
  - `Microsoft.MachineLearningServices`

To log in and confirm your current Entra object ID:

```bash
az login
az account show --query id -o tsv
az ad signed-in-user show --query id -o tsv
```

## State

Terraform uses local state by default. `main.tf` includes a commented `backend "azurerm"` example if you want to switch to remote state later.

## Configure variables

Start from the example file:

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Set `resource_group_name` to an existing resource group. `principal_id` is optional — if you leave it unset, Terraform assigns the RBAC role to the currently authenticated Azure client returned by `azurerm_client_config`.

## Deploy

Initialize providers:

```bash
cd infra/terraform
terraform init
```

Review the plan:

```bash
terraform plan
```

Apply the deployment:

```bash
terraform apply
```

Or supply a specific variables file explicitly:

```bash
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

## Outputs

After apply, Terraform returns:

- `project_endpoint`
- `ai_services_account_name`
- `foundry_project_name`
- `default_model_deployment_name`

Copy `project_endpoint` into your app configuration:

```bash
AZURE_AI_FOUNDRY_ENDPOINT=<project_endpoint>
AZURE_AI_FOUNDRY_MODEL=gpt-4o
```

The application authenticates with `DefaultAzureCredential`, so no API keys are required.
