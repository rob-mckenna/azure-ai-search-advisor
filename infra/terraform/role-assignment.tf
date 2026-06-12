resource "azurerm_role_assignment" "openai_user" {
  scope              = azurerm_cognitive_account.ai_services.id
  role_definition_id = local.openai_user_role_definition_id
  principal_id       = local.effective_principal_id
  principal_type     = var.principal_type
}
