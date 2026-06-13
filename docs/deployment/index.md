# Deployment Overview

Azure AI Search Advisor supports four deployment paths today.

## Choose the right path

| Path | Best for | What it provisions |
| --- | --- | --- |
| `azd` | Full-stack application deployment | Microsoft Foundry backend, Container Apps API, Static Web App UI |
| Bicep | Direct Azure template deployment | Microsoft Foundry backend resources |
| Terraform | Teams standardizing on Terraform | Microsoft Foundry backend resources |
| Docker | Local development | API container only |

## Shared Azure architecture

The infrastructure under `infra/` provisions a flat Microsoft Foundry project model:

- Azure AI Services account with local auth disabled
- Microsoft Foundry project (`kind: Project`)
- default `gpt-4o` deployment
- RBAC for the deploying principal and, in the `azd` path, the API managed identity

## Application hosting split

The checked-in `azure.yaml` defines two services:

- `api` -> Python app hosted in Azure Container Apps
- `web` -> Vite/React app hosted in Azure Static Web Apps

## After deployment

For any deployment path, populate the application runtime with:

```bash
AZURE_AI_FOUNDRY_ENDPOINT=<project endpoint>
AZURE_AI_FOUNDRY_MODEL=gpt-4o
```

The application uses `DefaultAzureCredential`, so no API key setup is required.

## Guides

- [Azure Developer CLI](azd.md)
- [Bicep](bicep.md)
- [Terraform](terraform.md)
- [Docker](docker.md)
