"""Microsoft Foundry client factory."""

from azure.identity import DefaultAzureCredential


class FoundryClientFactory:
    """Creates Microsoft Foundry clients for reasoning workloads.

    Microsoft Foundry provides a unified project-based interface for model
    deployments, prompt management, and agent orchestration — replacing
    direct Azure OpenAI endpoint usage.

    Authentication uses DefaultAzureCredential (managed identity, az login,
    environment variables, etc.) — API keys are not permitted.
    """

    def __init__(self, endpoint: str | None = None) -> None:
        self._endpoint = endpoint
        self._credential = DefaultAzureCredential()

    def create(self):
        """Create a configured Microsoft Foundry client.

        Uses the azure-ai-projects SDK with DefaultAzureCredential to
        connect to a Foundry project.

        Raises NotImplementedError until azure-ai-projects exposes the
        stable agent hosting API surface.
        """
        from azure_ai_search_advisor.core.config import Settings

        endpoint = self._endpoint or Settings().azure_ai_foundry_endpoint
        # azure-ai-projects client creation will be:
        #   from azure.ai.projects import AIProjectClient
        #   return AIProjectClient(endpoint=endpoint, credential=self._credential)
        raise NotImplementedError(
            f"Awaiting stable azure-ai-projects agent hosting API. Endpoint: {endpoint}"
        )
