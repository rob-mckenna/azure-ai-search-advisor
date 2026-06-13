# Deploy with Terraform

Use `infra/terraform/` when you want Terraform-managed Microsoft Foundry infrastructure.

## What Terraform provisions

The Terraform stack creates the same flat Foundry backend model as the Bicep path:

- Azure AI Services account with local auth disabled
- optional default model deployment
- Microsoft Foundry project created with `azapi_resource`
- AAD-authenticated connection from the project to the AI Services account
- `Cognitive Services OpenAI User` role assignment for the deploying principal

## Prerequisites

- Terraform 1.6+
- Azure CLI (`az`) signed into the target subscription
- Permission to create Azure AI Services, Machine Learning, and RBAC resources in an existing resource group
- Registered providers:
  - `Microsoft.CognitiveServices`
  - `Microsoft.MachineLearningServices`

## Configure variables

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your target resource group and naming choices. `principal_id` is optional; if omitted, Terraform uses the authenticated Azure client.

## Deploy

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

Or explicitly pin the variables file:

```bash
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

## Outputs

After `terraform apply`, note these outputs:

- `project_endpoint`
- `ai_services_account_name`
- `foundry_project_name`
- `default_model_deployment_name`

Then configure the app:

```bash
export AZURE_AI_FOUNDRY_ENDPOINT=<project_endpoint>
export AZURE_AI_FOUNDRY_MODEL=gpt-4o
```

## Notes

- State is local by default.
- `main.tf` includes a commented remote-backend example if you later move state into Azure Storage.
- This stack only provisions backend resources; it does not deploy the API or UI application hosts.
