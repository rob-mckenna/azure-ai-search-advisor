from __future__ import annotations

from unittest.mock import ANY, patch

from fastapi.testclient import TestClient

from azure_ai_search_advisor.api.dependencies import get_live_ingestion_service
from azure_ai_search_advisor.ingestion.azure_resource_graph import DiscoveredSearchService
from azure_ai_search_advisor.ingestion.live_exceptions import AzureCredentialsUnavailableError
from azure_ai_search_advisor.ingestion.live_ingestion_service import LiveIngestionService
from azure_ai_search_advisor.main import create_app



def _build_discovered_service(sample_snapshot) -> DiscoveredSearchService:
    configuration = sample_snapshot.configuration
    return DiscoveredSearchService(
        name=configuration.service_name,
        resource_group=configuration.resource_group,
        subscription_id=configuration.subscription_id,
        location=configuration.location,
        sku=configuration.sku.value,
        replica_count=configuration.replicas,
        partition_count=configuration.partitions,
    )



def _create_client() -> TestClient:
    get_live_ingestion_service.cache_clear()
    return TestClient(create_app())



def test_get_discover_returns_discovered_services(sample_snapshot) -> None:
    fake_service = _build_discovered_service(sample_snapshot)

    with patch.object(LiveIngestionService, "discover_services", autospec=True, return_value=[fake_service]) as mock_discover:
        response = _create_client().get("/discover")

    assert response.status_code == 200
    body = response.json()
    assert body["notes"] == []
    assert body["services"] == [
        {
            "name": fake_service.name,
            "resource_group": fake_service.resource_group,
            "subscription_id": fake_service.subscription_id,
            "location": fake_service.location,
            "sku": fake_service.sku,
            "replica_count": fake_service.replica_count,
            "partition_count": fake_service.partition_count,
        }
    ]
    mock_discover.assert_called_once_with(ANY, subscription_id=None, resource_group=None)



def test_get_discover_passes_subscription_filter(sample_snapshot) -> None:
    fake_service = _build_discovered_service(sample_snapshot)

    with patch.object(LiveIngestionService, "discover_services", autospec=True, return_value=[fake_service]) as mock_discover:
        response = _create_client().get("/discover", params={"subscription_id": "sub-filter"})

    assert response.status_code == 200
    mock_discover.assert_called_once_with(ANY, subscription_id="sub-filter", resource_group=None)



def test_post_discover_analyze_returns_analysis(sample_snapshot) -> None:
    fake_service = _build_discovered_service(sample_snapshot)

    with (
        patch.object(LiveIngestionService, "discover_services", autospec=True, return_value=[fake_service]) as mock_discover,
        patch.object(LiveIngestionService, "ingest_live_service", autospec=True, return_value=sample_snapshot) as mock_ingest,
    ):
        response = _create_client().post(f"/discover/{fake_service.name}/analyze")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["summary"]["finding_count"] >= 1
    assert body["findings"]
    mock_discover.assert_called_once_with(ANY, subscription_id=None, resource_group=None)
    mock_ingest.assert_called_once_with(
        ANY,
        subscription_id=fake_service.subscription_id,
        resource_group=fake_service.resource_group,
        service_name=fake_service.name,
    )



def test_post_discover_analyze_returns_404_for_unknown_service() -> None:
    with patch.object(LiveIngestionService, "discover_services", autospec=True, return_value=[]):
        response = _create_client().post("/discover/missing-service/analyze")

    assert response.status_code == 404
    assert response.json()["message"] == "No Azure AI Search service named 'missing-service' was found."



def test_discover_endpoints_return_503_when_azure_credentials_are_unavailable(sample_snapshot) -> None:
    fake_service = _build_discovered_service(sample_snapshot)
    client = _create_client()

    with patch.object(
        LiveIngestionService,
        "discover_services",
        autospec=True,
        side_effect=AzureCredentialsUnavailableError("Azure credentials are unavailable."),
    ):
        discover_response = client.get("/discover")

    with patch.object(
        LiveIngestionService,
        "ingest_live_service",
        autospec=True,
        side_effect=AzureCredentialsUnavailableError("Azure credentials are unavailable."),
    ):
        analyze_response = client.post(
            f"/discover/{fake_service.name}/analyze",
            params={
                "subscription_id": fake_service.subscription_id,
                "resource_group": fake_service.resource_group,
            },
        )

    assert discover_response.status_code == 503
    assert discover_response.json()["message"] == "Azure credentials are unavailable."
    assert analyze_response.status_code == 503
    assert analyze_response.json()["message"] == "Azure credentials are unavailable."
