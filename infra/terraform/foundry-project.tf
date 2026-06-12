resource "azapi_resource" "foundry_project" {
  type      = "Microsoft.MachineLearningServices/workspaces@2025-06-01"
  name      = local.resolved_ai_project_name
  parent_id = data.azurerm_resource_group.current.id
  location  = local.location
  tags      = var.tags

  schema_validation_enabled = false

  body = {
    kind = "Project"
    sku = {
      name = "Basic"
      tier = "Basic"
    }
    identity = {
      type = "SystemAssigned"
    }
    properties = {
      friendlyName        = local.resolved_ai_project_name
      publicNetworkAccess = "Enabled"
    }
  }

  response_export_values = ["id", "name"]
}

resource "azapi_resource" "ai_services_connection" {
  type      = "Microsoft.MachineLearningServices/workspaces/connections@2025-06-01"
  name      = "${local.resolved_ai_services_account_name}-connection"
  parent_id = azapi_resource.foundry_project.id

  schema_validation_enabled = false

  body = {
    properties = {
      category                    = "AIServices"
      target                      = azurerm_cognitive_account.ai_services.endpoint
      authType                    = "AAD"
      isSharedToAll               = true
      useWorkspaceManagedIdentity = true
      metadata = {
        ApiType    = "Azure"
        ResourceId = azurerm_cognitive_account.ai_services.id
      }
    }
  }

  response_export_values = ["id", "name"]
}
