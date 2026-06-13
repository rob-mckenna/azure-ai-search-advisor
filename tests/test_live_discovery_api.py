from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from azure_ai_search_advisor.api.dependencies import get_live_ingestion_service
from azure_ai_search_advisor.ingestion.azure_resource_graph import DiscoveredSearchService
from azure_ai_search_advisor.ingestion.live_exceptions import AzureCredentialsUnavailableError
from azure_ai_search_advisor.main import create_app
from azure_ai_search_advisor.models import AzureSearchServiceSnapshot


class _FakeLiveIngestionService:
    def __init__(self, snapshot: AzureSearchServiceSnapshot) -> None:
        self._snapshot = snapshot

    def discover_services(
        self,
        subscription_id: str | None = None,
        resource_group: str | None = None,
    ) -> list[DiscoveredSearchService]:
        _ = (subscription_id, resource_group)
        return [
            DiscoveredSearchService(
                name=self._snapshot.configuration.service_name,
                resource_group=self._snapshot.configuration.resource_group,
                subscription_id=self._snapshot.configuration.subscription_id,
                location=self._snapshot.configuration.location,
                sku=self._snapshot.configuration.sku.value,
                replica_count=self._snapshot.configuration.replicas,
                partition_count=self._snapshot.configuration.partitions,
            )
        ]

    def ingest_live_service(
        self,
        subscription_id: str,
        resource_group: str,
        service_name: str,
    ) -> AzureSearchServiceSnapshot:
        _ = (subscription_id, resource_group, service_name)
        return self._snapshot


def test_discover_returns_live_services(sample_snapshot) -> None:
    app = create_app()
    app.dependency_overrides[get_live_ingestion_service] = lambda: _FakeLiveIngestionService(sample_snapshot)

    response = TestClient(app).get("/discover")

    assert response.status_code == 200
    body = response.json()
    assert len(body["services"]) == 1
    assert body["services"][0]["name"] == sample_snapshot.configuration.service_name


def test_discover_analyze_returns_completed_response(sample_snapshot) -> None:
    live_snapshot = AzureSearchServiceSnapshot(
        collected_at=datetime.now(timezone.utc),
        configuration=sample_snapshot.configuration,
        metrics=None,
        notes=["Live analysis executed without Azure Monitor metrics."],
    )
    app = create_app()
    app.dependency_overrides[get_live_ingestion_service] = lambda: _FakeLiveIngestionService(live_snapshot)

    response = TestClient(app).post(
        f"/discover/{sample_snapshot.configuration.service_name}/analyze",
        params={
            "subscription_id": sample_snapshot.configuration.subscription_id,
            "resource_group": sample_snapshot.configuration.resource_group,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert "Live analysis executed without Azure Monitor metrics." in body["notes"]


def test_discover_returns_503_when_credentials_are_unavailable() -> None:
    app = create_app()

    class _CredentialErrorService:
        def discover_services(self, subscription_id: str | None = None, resource_group: str | None = None):
            _ = (subscription_id, resource_group)
            raise AzureCredentialsUnavailableError("Azure credentials are unavailable.")

    app.dependency_overrides[get_live_ingestion_service] = lambda: _CredentialErrorService()

    response = TestClient(app).get("/discover")

    assert response.status_code == 503
    assert response.json()["message"] == "Azure credentials are unavailable."
