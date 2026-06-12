resource "azurerm_cognitive_account" "ai_services" {
  name                          = local.resolved_ai_services_account_name
  location                      = local.location
  resource_group_name           = data.azurerm_resource_group.current.name
  kind                          = "AIServices"
  sku_name                      = var.ai_services_sku_name
  custom_subdomain_name         = local.resolved_ai_services_account_name
  local_auth_enabled            = false
  public_network_access_enabled = true
  tags                          = var.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_cognitive_deployment" "default_model" {
  count                  = var.deploy_default_model ? 1 : 0
  name                   = var.model_deployment_name
  cognitive_account_id   = azurerm_cognitive_account.ai_services.id
  version_upgrade_option = "OnceNewDefaultVersionAvailable"

  model {
    format  = "OpenAI"
    name    = var.model_name
    version = var.model_version
  }

  sku {
    name     = "Standard"
    capacity = var.model_capacity
  }
}
