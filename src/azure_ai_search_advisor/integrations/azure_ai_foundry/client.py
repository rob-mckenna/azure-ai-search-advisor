"""Microsoft Foundry client scaffold."""

from azure.identity import DefaultAzureCredential


class FoundryClientFactory:
    """Creates Microsoft Foundry clients for reasoning workloads.

    Microsoft Foundry provides a unified project-based interface for model
    deployments, prompt management, and agent orchestration — replacing
    direct Azure OpenAI endpoint usage.

    Authentication uses DefaultAzureCredential (managed identity, az login,
    environment variables, etc.) — API keys are not permitted.
    """

    def create(self) -> None:
        """Create a configured Microsoft Foundry client.

        Uses the azure-ai-projects SDK with DefaultAzureCredential to
        connect to a Foundry project.
        """
        # TODO: Build an authenticated Microsoft Foundry client:
        #   credential = DefaultAzureCredential()
        #   client = AIProjectClient(endpoint=..., credential=credential)
        raise NotImplementedError
