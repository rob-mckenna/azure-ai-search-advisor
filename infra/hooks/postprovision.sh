#!/usr/bin/env sh
set -eu

ROLE_DEFINITION_ID="5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"
RESOURCE_GROUP_NAME="${AZURE_RESOURCE_GROUP_NAME:-rg-${AZURE_ENV_NAME:-}}"

if command -v az >/dev/null 2>&1 && [ -n "${AZURE_AI_FOUNDRY_ACCOUNT_NAME:-}" ]; then
  scope="$(az cognitiveservices account show --name "${AZURE_AI_FOUNDRY_ACCOUNT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query id -o tsv 2>/dev/null || true)"
  if [ -n "$scope" ] && [ -n "${SERVICE_API_IDENTITY_PRINCIPAL_ID:-}" ]; then
    az role assignment create \
      --assignee-object-id "${SERVICE_API_IDENTITY_PRINCIPAL_ID}" \
      --assignee-principal-type ServicePrincipal \
      --role "$ROLE_DEFINITION_ID" \
      --scope "$scope" \
      --only-show-errors >/dev/null 2>&1 || true
  fi

  if [ -n "$scope" ] && [ -n "${AZURE_PRINCIPAL_ID:-}" ]; then
    az role assignment create \
      --assignee-object-id "${AZURE_PRINCIPAL_ID}" \
      --role "$ROLE_DEFINITION_ID" \
      --scope "$scope" \
      --only-show-errors >/dev/null 2>&1 || true
  fi
fi

printf 'Microsoft Foundry endpoint: %s\n' "${AZURE_AI_FOUNDRY_ENDPOINT:-unavailable}"
printf 'API endpoint: %s\n' "${SERVICE_API_URI:-unavailable}"
printf 'Web endpoint: %s\n' "${SERVICE_WEB_URI:-unavailable}"
