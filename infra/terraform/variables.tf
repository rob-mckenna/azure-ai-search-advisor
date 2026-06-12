variable "resource_group_name" {
  description = "Name of the existing resource group that will contain the Azure AI Services account and Foundry project."
  type        = string
}

variable "location" {
  description = "Azure region for the Microsoft Foundry resources. Defaults to the resource group location when null."
  type        = string
  default     = null
}

variable "project_name" {
  description = "Logical project name used to derive the Microsoft Foundry project and supporting resource names."
  type        = string
  default     = "searchadvisor"

  validation {
    condition     = length(var.project_name) >= 3 && length(var.project_name) <= 16
    error_message = "project_name must be between 3 and 16 characters."
  }
}

variable "ai_services_account_name" {
  description = "Optional override for the Azure AI Services account name. Leave empty to derive from project_name."
  type        = string
  default     = ""
}

variable "ai_project_name" {
  description = "Optional override for the Microsoft Foundry project name. Leave empty to derive from project_name."
  type        = string
  default     = ""
}

variable "principal_id" {
  description = "Optional Microsoft Entra object ID for the principal that should receive the Cognitive Services OpenAI User role. Defaults to the current authenticated client."
  type        = string
  default     = ""
}

variable "principal_type" {
  description = "Principal type for the RBAC assignment. Use User for local development and ServicePrincipal for automation identities."
  type        = string
  default     = "User"

  validation {
    condition     = contains(["User", "ServicePrincipal", "Group"], var.principal_type)
    error_message = "principal_type must be one of User, ServicePrincipal, or Group."
  }
}

variable "model_deployment_name" {
  description = "Default model deployment name to create in Azure AI Services for the project."
  type        = string
  default     = "gpt-4o"
}

variable "model_name" {
  description = "Foundation model name to deploy into the Azure AI Services account."
  type        = string
  default     = "gpt-4o"
}

variable "model_version" {
  description = "Foundation model version to deploy. Update this if your target region requires a different supported version."
  type        = string
  default     = "2024-05-13"
}

variable "model_capacity" {
  description = "Capacity units to allocate for the default model deployment."
  type        = number
  default     = 10

  validation {
    condition     = var.model_capacity >= 1
    error_message = "model_capacity must be at least 1."
  }
}

variable "deploy_default_model" {
  description = "Whether to deploy the default model during infrastructure provisioning."
  type        = bool
  default     = true
}

variable "ai_services_sku_name" {
  description = "SKU name for the Azure AI Services account."
  type        = string
  default     = "S0"
}

variable "tags" {
  description = "Tags to apply to all provisioned infrastructure resources."
  type        = map(string)
  default = {
    workload    = "azure-ai-search-advisor"
    provisioner = "terraform"
  }
}
