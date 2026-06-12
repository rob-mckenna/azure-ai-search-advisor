output "project_endpoint" {
  description = "Microsoft Foundry project endpoint that can be copied into AZURE_AI_FOUNDRY_ENDPOINT."
  value       = local.project_endpoint
}

output "ai_services_account_name" {
  description = "Azure AI Services account name backing the Foundry project."
  value       = azurerm_cognitive_account.ai_services.name
}

output "foundry_project_name" {
  description = "Microsoft Foundry project resource name."
  value       = local.resolved_ai_project_name
}

output "default_model_deployment_name" {
  description = "Default model deployment name available to the application after provisioning."
  value       = var.model_deployment_name
}
