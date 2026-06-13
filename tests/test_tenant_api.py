from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from azure_ai_search_advisor.api.auth import CurrentUser, get_current_user
from azure_ai_search_advisor.api.dependencies import get_live_ingestion_service
from azure_ai_search_advisor.ingestion.azure_resource_graph import DiscoveredSearchService
from azure_ai_search_advisor.main import create_app


def _tenant_db_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / f"test-tenants-{uuid4().hex}.db"


def _cleanup_db(path: Path) -> None:
    for candidate in (
        path,
        path.with_suffix(f"{path.suffix}-journal"),
        path.with_suffix(f"{path.suffix}-shm"),
        path.with_suffix(f"{path.suffix}-wal"),
    ):
        if candidate.exists():
            candidate.unlink()


class _FakeLiveIngestionService:
    def discover_services(
        self,
        subscription_id: str | None = None,
        resource_group: str | None = None,
    ) -> list[DiscoveredSearchService]:
        services = [
            DiscoveredSearchService(
                name="team-search-a",
                resource_group="rg-a",
                subscription_id="sub-a",
                location="eastus2",
                sku="standard",
                replica_count=2,
                partition_count=1,
            ),
            DiscoveredSearchService(
                name="other-search",
                resource_group="rg-b",
                subscription_id="sub-b",
                location="westus2",
                sku="standard",
                replica_count=1,
                partition_count=1,
            ),
        ]
        return [
            service
            for service in services
            if (subscription_id is None or service.subscription_id == subscription_id)
            and (resource_group is None or service.resource_group == resource_group)
        ]


def test_get_tenant_returns_local_fallback(monkeypatch) -> None:
    tenant_db_path = _tenant_db_path()
    monkeypatch.setenv("TENANT_DB_PATH", str(tenant_db_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")

    try:
        response = TestClient(create_app()).get("/tenant")

        assert response.status_code == 200
        body = response.json()
        assert body["tenant"]["name"] == "local"
        assert body["role"] == "admin"
    finally:
        _cleanup_db(tenant_db_path)


def test_create_tenant_and_manage_members_and_services(monkeypatch) -> None:
    tenant_db_path = _tenant_db_path()
    monkeypatch.setenv("TENANT_DB_PATH", str(tenant_db_path))
    monkeypatch.setenv("AUTH_ENABLED", "true")

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        sub="user-sub",
        name="Tenant Admin",
        oid="user-oid",
        roles=("advisor.user",),
        email="admin@example.test",
    )
    client = TestClient(app)

    try:
        create_response = client.post("/tenant", json={"name": "Contoso Platform"})
        assert create_response.status_code == 201
        assert create_response.json()["tenant"]["name"] == "Contoso Platform"

        member_response = client.post(
            "/tenant/members",
            json={
                "user_oid": "member-oid",
                "role": "viewer",
                "display_name": "View Only",
                "email": "viewer@example.test",
            },
        )
        assert member_response.status_code == 201
        assert member_response.json()["role"] == "viewer"

        members_response = client.get("/tenant/members")
        assert members_response.status_code == 200
        assert len(members_response.json()["members"]) == 2

        service_response = client.post(
            "/tenant/services",
            json={
                "subscription_id": "sub-a",
                "resource_group": "rg-a",
                "service_name": "team-search-a",
            },
        )
        assert service_response.status_code == 201

        services_response = client.get("/tenant/services")
        assert services_response.status_code == 200
        assert services_response.json()["services"][0]["service_name"] == "team-search-a"

        delete_response = client.delete(f"/tenant/services/{service_response.json()['id']}")
        assert delete_response.status_code == 204
    finally:
        _cleanup_db(tenant_db_path)


def test_discover_is_scoped_to_registered_services(monkeypatch) -> None:
    tenant_db_path = _tenant_db_path()
    monkeypatch.setenv("TENANT_DB_PATH", str(tenant_db_path))
    monkeypatch.setenv("AUTH_ENABLED", "true")

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        sub="tenant-user",
        name="Tenant User",
        oid="tenant-user-oid",
        roles=("advisor.user",),
    )
    app.dependency_overrides[get_live_ingestion_service] = lambda: _FakeLiveIngestionService()
    client = TestClient(app)

    try:
        assert client.post("/tenant", json={"name": "Scoped Tenant"}).status_code == 201
        assert (
            client.post(
                "/tenant/services",
                json={
                    "subscription_id": "sub-a",
                    "resource_group": "rg-a",
                    "service_name": "team-search-a",
                },
            ).status_code
            == 201
        )

        response = client.get("/discover")

        assert response.status_code == 200
        body = response.json()
        assert [service["name"] for service in body["services"]] == ["team-search-a"]
    finally:
        _cleanup_db(tenant_db_path)
