"""High-level orchestration for live Azure AI Search ingestion."""

from __future__ import annotations

import os

from azure.identity import DefaultAzureCredential

from azure_ai_search_advisor.ingestion.azure_resource_graph import (
    AzureResourceGraphSearchDiscoveryClient,
    DiscoveredSearchService,
)
from azure_ai_search_advisor.ingestion.azure_search_management import AzureSearchManagementClientAdapter
from azure_ai_search_advisor.models import AzureSearchServiceSnapshot


class LiveIngestionService:
    """Combines Azure Resource Graph discovery and management-plane ingestion."""

    def __init__(
        self,
        resource_graph_client: AzureResourceGraphSearchDiscoveryClient | None = None,
        search_management_client: AzureSearchManagementClientAdapter | None = None,
    ) -> None:
        credential = DefaultAzureCredential()
        self._resource_graph_client = resource_graph_client or AzureResourceGraphSearchDiscoveryClient(
            credential=credential
        )
        self._search_management_client = search_management_client or AzureSearchManagementClientAdapter(
            credential=credential
        )

    def discover_services(
        self,
        subscription_id: str | None = None,
        resource_group: str | None = None,
    ) -> list[DiscoveredSearchService]:
        """List Azure AI Search services accessible to the current caller."""

        effective_subscription_id = subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
        return self._resource_graph_client.discover_services(
            subscription_id=effective_subscription_id,
            resource_group=resource_group,
        )

    def ingest_live_service(
        self,
        subscription_id: str,
        resource_group: str,
        service_name: str,
    ) -> AzureSearchServiceSnapshot:
        """Fetch a live Azure AI Search snapshot via the management API."""

        return self._search_management_client.ingest_service(
            subscription_id=subscription_id,
            resource_group=resource_group,
            service_name=service_name,
        )
