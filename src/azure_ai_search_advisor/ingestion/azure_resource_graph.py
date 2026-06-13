"""Azure Resource Graph discovery for Azure AI Search services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
from azure.identity import CredentialUnavailableError, DefaultAzureCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest, QueryRequestOptions

from azure_ai_search_advisor.ingestion.live_exceptions import (
    AzureCredentialsUnavailableError,
    AzureResourceDiscoveryError,
)


@dataclass(frozen=True, slots=True)
class DiscoveredSearchService:
    """Summary of an Azure AI Search service discovered via Resource Graph."""

    name: str
    resource_group: str
    subscription_id: str
    location: str
    sku: str | None
    replica_count: int | None
    partition_count: int | None


class AzureResourceGraphSearchDiscoveryClient:
    """Discovers Azure AI Search services using Azure Resource Graph."""

    def __init__(self, credential: DefaultAzureCredential | None = None) -> None:
        self._credential = credential or DefaultAzureCredential()

    def discover_services(
        self,
        *,
        subscription_id: str | None = None,
        resource_group: str | None = None,
        service_name: str | None = None,
    ) -> list[DiscoveredSearchService]:
        """Return Azure AI Search services accessible to the current credential."""

        query = self._build_query(
            subscription_id=subscription_id,
            resource_group=resource_group,
            service_name=service_name,
        )
        request = QueryRequest(
            query=query,
            subscriptions=[subscription_id] if subscription_id else None,
            options=QueryRequestOptions(top=1000),
        )

        services: list[DiscoveredSearchService] = []
        try:
            with ResourceGraphClient(self._credential) as client:
                response = client.resources(request)
                services.extend(self._parse_response_rows(response.data))
                while response.skip_token:
                    request.options.skip_token = response.skip_token
                    response = client.resources(request)
                    services.extend(self._parse_response_rows(response.data))
        except (CredentialUnavailableError, ClientAuthenticationError) as exc:
            raise AzureCredentialsUnavailableError(
                "Azure credentials are unavailable. Configure DefaultAzureCredential "
                "via az login, managed identity, or service principal environment variables."
            ) from exc
        except HttpResponseError as exc:
            raise AzureResourceDiscoveryError(
                f"Azure Resource Graph query failed: {exc.message or exc!s}"
            ) from exc

        return services

    def _build_query(
        self,
        *,
        subscription_id: str | None,
        resource_group: str | None,
        service_name: str | None,
    ) -> str:
        filters = ["Resources", "| where type =~ 'microsoft.search/searchservices'"]
        if subscription_id:
            filters.append(f"| where subscriptionId =~ '{self._quote(subscription_id)}'")
        if resource_group:
            filters.append(f"| where resourceGroup =~ '{self._quote(resource_group)}'")
        if service_name:
            filters.append(f"| where name =~ '{self._quote(service_name)}'")
        filters.append(
            "| project "
            "name, resourceGroup, subscriptionId, location, "
            "sku=tostring(coalesce(properties.sku.name, properties.sku, sku.name, sku.tier)), "
            "replicaCount=toint(properties.replicaCount), "
            "partitionCount=toint(properties.partitionCount), "
            "hostingMode=tostring(properties.hostingMode), "
            "status=tostring(properties.status), "
            "publicNetworkAccess=tostring(properties.publicNetworkAccess)"
        )
        return "\n".join(filters)

    def _parse_response_rows(self, data: Any) -> list[DiscoveredSearchService]:
        rows: list[dict[str, Any]]
        if isinstance(data, list):
            rows = [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict) and isinstance(data.get("rows"), list):
            columns = [column["name"] for column in data.get("columns", []) if "name" in column]
            rows = [
                {
                    column_name: value
                    for column_name, value in zip(columns, row, strict=False)
                }
                for row in data["rows"]
                if isinstance(row, list)
            ]
        else:
            rows = []

        return [
            DiscoveredSearchService(
                name=str(row.get("name", "")),
                resource_group=str(row.get("resourceGroup", "")),
                subscription_id=str(row.get("subscriptionId", "")),
                location=str(row.get("location", "")),
                sku=self._optional_str(row.get("sku")),
                replica_count=self._optional_int(row.get("replicaCount")),
                partition_count=self._optional_int(row.get("partitionCount")),
            )
            for row in rows
            if row.get("name") and row.get("resourceGroup") and row.get("subscriptionId")
        ]

    @staticmethod
    def _quote(value: str) -> str:
        return value.replace("'", "''")

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
