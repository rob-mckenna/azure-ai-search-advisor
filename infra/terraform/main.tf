terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.110.0, < 5.0.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = ">= 1.13.0, < 3.0.0"
    }
  }

  # Local state is used by default.
  # To use remote state instead, uncomment and configure a backend such as:
  # backend "azurerm" {
  #   resource_group_name  = "rg-terraform-state"
  #   storage_account_name = "tfstateaccount"
  #   container_name       = "tfstate"
  #   key                  = "azure-ai-search-advisor.tfstate"
  # }
}

provider "azurerm" {
  features {}
}

provider "azapi" {}

data "azurerm_client_config" "current" {}

data "azurerm_resource_group" "current" {
  name = var.resource_group_name
}

locals {
  location                          = coalesce(var.location, data.azurerm_resource_group.current.location)
  resource_suffix                   = substr(md5("${data.azurerm_client_config.current.subscription_id}/${data.azurerm_resource_group.current.id}/${var.project_name}"), 0, 6)
  resolved_ai_services_account_name = var.ai_services_account_name != "" ? var.ai_services_account_name : substr("${var.project_name}-foundry-${local.resource_suffix}", 0, 64)
  resolved_ai_project_name          = var.ai_project_name != "" ? var.ai_project_name : substr("${var.project_name}-project", 0, 33)
  effective_principal_id            = var.principal_id != "" ? var.principal_id : data.azurerm_client_config.current.object_id
  openai_user_role_definition_id    = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"
  project_endpoint                  = "https://${local.resolved_ai_services_account_name}.services.ai.azure.com/"
}
