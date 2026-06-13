from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from jose import jwt
from jose.utils import base64url_encode

from azure_ai_search_advisor.api import auth
from azure_ai_search_advisor.api.dependencies import get_response_cache
from azure_ai_search_advisor.main import create_app


def _history_db_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / f"test-history-{uuid4().hex}.db"


def _cleanup_history_db(path: Path) -> None:
    for candidate in (
        path,
        path.with_suffix(f"{path.suffix}-journal"),
        path.with_suffix(f"{path.suffix}-shm"),
        path.with_suffix(f"{path.suffix}-wal"),
    ):
        if candidate.exists():
            candidate.unlink()


def _build_api_inputs(snapshot) -> tuple[dict, dict]:
    configuration = snapshot.configuration
    metrics = snapshot.metrics
    return (
        {
            "service_name": configuration.service_name,
            "region": configuration.location,
            "capacity": {
                "pricing_model": configuration.deployment_mode.value,
                "sku": configuration.sku.value,
                "replica_count": configuration.replicas or 0,
                "partition_count": configuration.partitions or 0,
                "zone_redundancy_enabled": configuration.availability_zones_enabled,
            },
            "features": {
                "semantic_ranker_enabled": configuration.semantic_ranker.enabled,
                "vector_search_enabled": configuration.vector_search.enabled,
                "ai_enrichment_enabled": configuration.ai_enrichment.enabled,
                "knowledge_store_enabled": configuration.ai_enrichment.knowledge_store_enabled,
            },
            "index_topology": {
                "index_count": configuration.index_count,
                "indexer_count": configuration.indexer_count,
                "skillset_count": configuration.skillset_count,
                "total_document_count": metrics.document_count,
                "total_index_size_gb": metrics.total_index_size_gb,
                "vector_index_size_gb": 0.0,
            },
            "security": {
                "api_keys_enabled": True,
                "managed_identity_enabled": configuration.managed_identity_enabled,
                "private_endpoint_enabled": configuration.private_endpoint_enabled,
                "customer_managed_keys_enabled": False,
            },
            "notes": list(snapshot.notes),
        },
        {
            "observation_window_days": metrics.observation_window_days,
            "query": {
                "average_queries_per_second": metrics.query_volume.avg_queries_per_second,
                "peak_queries_per_second": round(metrics.query_volume.peak_queries_per_day / 3600, 4),
                "monthly_query_volume": metrics.query_volume.monthly_queries,
                "p95_query_latency_ms": metrics.latency.p95_ms,
                "cache_hit_ratio": 0.0,
            },
            "indexing": {
                "daily_document_updates": metrics.indexing_operations_per_day,
                "full_rebuilds_per_month": 0,
                "average_indexing_latency_minutes": 0.0,
            },
            "utilization": {
                "replica_utilization_percent": metrics.avg_cpu_utilization_pct,
                "partition_utilization_percent": metrics.storage_quota_utilization_pct,
                "storage_utilization_percent": metrics.storage_quota_utilization_pct,
                "semantic_queries_per_day": 0,
                "vector_queries_per_day": 0,
            },
        },
    )



def test_health_returns_200(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"]
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "azure-ai-search-advisor"


def test_health_echoes_supplied_correlation_id(client) -> None:
    response = client.get("/health", headers={"X-Correlation-ID": "test-correlation-id"})

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "test-correlation-id"



def test_analyze_with_valid_payload_returns_findings(client, sample_snapshot) -> None:
    configuration, metrics = _build_api_inputs(sample_snapshot)

    response = client.post(
        "/analyze",
        json={
            "configuration": configuration,
            "metrics": metrics,
            "include_cost_signals": True,
            "include_feature_assessment": True,
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"
    assert response.headers["X-Cache-Key"]
    body = response.json()
    assert body["status"] == "completed"
    assert body["summary"]["finding_count"] >= 1
    assert len(body["findings"]) >= 1



def test_analyze_with_invalid_payload_returns_422(client) -> None:
    response = client.post(
        "/analyze",
        json={
            "configuration": {"service_name": ""},
            "metrics": {},
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["status_code"] == 422
    assert body["details"]



def test_recommend_returns_recommendations(client, sample_snapshot) -> None:
    configuration, metrics = _build_api_inputs(sample_snapshot)

    response = client.post(
        "/recommend",
        json={
            "configuration": configuration,
            "metrics": metrics,
            "preferences": {
                "max_recommendations": 5,
                "prioritize_for": ["cost", "availability"],
                "include_remediation_steps": True,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["source"] == "end_to_end"
    assert len(body["recommendations"]) >= 1


def test_analyze_records_history_and_exposes_trends(monkeypatch, sample_snapshot) -> None:
    history_db_path = _history_db_path()
    monkeypatch.setenv("HISTORY_DB_PATH", str(history_db_path))
    configuration, metrics = _build_api_inputs(sample_snapshot)
    client = TestClient(create_app())

    try:
        analyze_response = client.post(
            "/analyze",
            json={
                "configuration": configuration,
                "metrics": metrics,
                "include_cost_signals": True,
                "include_feature_assessment": True,
            },
        )
        assert analyze_response.status_code == 200

        history_response = client.get(f"/history/{configuration['service_name']}")
        assert history_response.status_code == 200
        history_body = history_response.json()
        assert history_body["runs"]
        assert history_body["runs"][0]["service_name"] == configuration["service_name"]
        assert history_body["runs"][0]["finding_count"] >= 1
        assert history_body["runs"][0]["recommendation_count"] == 0

        trends_response = client.get(f"/history/{configuration['service_name']}/trends")
        assert trends_response.status_code == 200
        trends_body = trends_response.json()
        assert len(trends_body["finding_count_over_time"]) == 1
        assert trends_body["finding_count_over_time"][0]["finding_count"] >= 1
    finally:
        _cleanup_history_db(history_db_path)


def test_recommend_end_to_end_records_cost_history(monkeypatch, sample_snapshot) -> None:
    history_db_path = _history_db_path()
    monkeypatch.setenv("HISTORY_DB_PATH", str(history_db_path))
    configuration, metrics = _build_api_inputs(sample_snapshot)
    client = TestClient(create_app())

    try:
        recommend_response = client.post(
            "/recommend",
            json={
                "configuration": configuration,
                "metrics": metrics,
                "preferences": {
                    "max_recommendations": 5,
                    "prioritize_for": ["cost", "availability"],
                    "include_remediation_steps": True,
                },
            },
        )
        assert recommend_response.status_code == 200

        history_response = client.get(f"/history/{configuration['service_name']}")
        assert history_response.status_code == 200
        history_body = history_response.json()
        assert history_body["runs"]
        assert history_body["runs"][0]["dedicated_monthly_usd"] is not None
        assert history_body["runs"][0]["serverless_monthly_usd"] is not None
        assert history_body["runs"][0]["recommendation_count"] >= 1
    finally:
        _cleanup_history_db(history_db_path)


def test_simulate_returns_cost_comparison(client, sample_snapshot) -> None:
    configuration, metrics = _build_api_inputs(sample_snapshot)

    response = client.post(
        "/simulate",
        json={
            "current_configuration": configuration,
            "current_metrics": metrics,
            "proposed_changes": [
                {
                    "change_id": "reduce-replicas",
                    "target": "capacity",
                    "attribute": "replica_count",
                    "current_value": configuration["capacity"]["replica_count"],
                    "proposed_value": configuration["capacity"]["replica_count"] - 1,
                    "rationale": "Observed load is low relative to current replica capacity.",
                }
            ],
            "assumptions": {
                "pricing_horizon_days": 30,
                "currency": "USD",
                "notes": ["Test scenario for reducing dedicated capacity."],
            },
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"
    assert response.headers["X-Cache-Key"]
    body = response.json()
    assert body["status"] == "completed"
    assert body["comparison"]["current_estimate"]["monthly_total"] > 0
    assert body["comparison"]["proposed_estimate"]["monthly_total"] > 0
    assert body["comparison"]["monthly_delta"] < 0


def test_analyze_returns_cache_hit_when_enabled(monkeypatch, sample_snapshot) -> None:
    configuration, metrics = _build_api_inputs(sample_snapshot)
    monkeypatch.setenv("CACHE_ENABLED", "true")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "300")
    monkeypatch.setenv("CACHE_MAX_ENTRIES", "100")
    get_response_cache.cache_clear()
    client = TestClient(create_app())
    payload = {
        "configuration": configuration,
        "metrics": metrics,
        "include_cost_signals": True,
        "include_feature_assessment": True,
    }

    first_response = client.post("/analyze", json=payload)
    second_response = client.post("/analyze", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.headers["X-Cache"] == "MISS"
    assert second_response.headers["X-Cache"] == "HIT"
    assert first_response.headers["X-Cache-Key"] == second_response.headers["X-Cache-Key"]
    assert first_response.json() == second_response.json()
    get_response_cache.cache_clear()


def test_simulate_returns_cache_hit_when_enabled(monkeypatch, sample_snapshot) -> None:
    configuration, metrics = _build_api_inputs(sample_snapshot)
    monkeypatch.setenv("CACHE_ENABLED", "true")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "300")
    monkeypatch.setenv("CACHE_MAX_ENTRIES", "100")
    get_response_cache.cache_clear()
    client = TestClient(create_app())
    payload = {
        "current_configuration": configuration,
        "current_metrics": metrics,
        "proposed_changes": [
            {
                "change_id": "reduce-replicas",
                "target": "capacity",
                "attribute": "replica_count",
                "current_value": configuration["capacity"]["replica_count"],
                "proposed_value": configuration["capacity"]["replica_count"] - 1,
                "rationale": "Observed load is low relative to current replica capacity.",
            }
        ],
        "assumptions": {
            "pricing_horizon_days": 30,
            "currency": "USD",
            "notes": ["Test scenario for reducing dedicated capacity."],
        },
    }

    first_response = client.post("/simulate", json=payload)
    second_response = client.post("/simulate", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.headers["X-Cache"] == "MISS"
    assert second_response.headers["X-Cache"] == "HIT"
    assert first_response.headers["X-Cache-Key"] == second_response.headers["X-Cache-Key"]
    assert first_response.json() == second_response.json()
    get_response_cache.cache_clear()


def _build_valid_bearer_token() -> tuple[str, dict]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_numbers = private_key.public_key().public_numbers()

    def _encode_number(value: int) -> str:
        size = (value.bit_length() + 7) // 8
        return base64url_encode(value.to_bytes(size, "big")).decode("utf-8")

    jwk = {
        "kty": "RSA",
        "kid": "test-key",
        "use": "sig",
        "alg": "RS256",
        "n": _encode_number(public_numbers.n),
        "e": _encode_number(public_numbers.e),
    }
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    token = jwt.encode(
        {
            "sub": "test-subject",
            "name": "Test User",
            "oid": "test-object-id",
            "roles": ["advisor.user"],
            "aud": "test-client-id",
            "iss": "https://login.microsoftonline.com/test-tenant-id/v2.0",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(expires_at.timestamp()),
        },
        private_pem,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    return token, jwk


def test_protected_routes_require_bearer_token_when_auth_enabled(monkeypatch, sample_snapshot) -> None:
    configuration, metrics = _build_api_inputs(sample_snapshot)
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AZURE_TENANT_ID", "test-tenant-id")
    monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id")
    auth._jwks_cache._keys = None
    auth._jwks_cache._metadata = None

    response = TestClient(create_app()).post(
        "/analyze",
        json={
            "configuration": configuration,
            "metrics": metrics,
            "include_cost_signals": True,
            "include_feature_assessment": True,
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["message"] == "Bearer token is required."


def test_health_stays_unauthenticated_when_auth_enabled(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AZURE_TENANT_ID", "test-tenant-id")
    monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id")
    auth._jwks_cache._keys = None
    auth._jwks_cache._metadata = None

    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200


def test_protected_routes_are_rate_limited_when_enabled(monkeypatch, sample_snapshot) -> None:
    configuration, metrics = _build_api_inputs(sample_snapshot)
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    client = TestClient(create_app())
    headers = {"X-Forwarded-For": "203.0.113.10"}

    first_response = client.post(
        "/analyze",
        headers=headers,
        json={
            "configuration": configuration,
            "metrics": metrics,
            "include_cost_signals": True,
            "include_feature_assessment": True,
        },
    )
    second_response = client.post(
        "/analyze",
        headers=headers,
        json={
            "configuration": configuration,
            "metrics": metrics,
            "include_cost_signals": True,
            "include_feature_assessment": True,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.headers["Retry-After"] == "60"
    assert second_response.json()["message"] == "Rate limit exceeded. Try again later."


def test_health_is_not_rate_limited(monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    client = TestClient(create_app())
    headers = {"X-Forwarded-For": "203.0.113.11"}

    first_response = client.get("/health", headers=headers)
    second_response = client.get("/health", headers=headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200


def test_protected_routes_accept_valid_entra_token(monkeypatch, sample_snapshot) -> None:
    configuration, metrics = _build_api_inputs(sample_snapshot)
    token, jwk = _build_valid_bearer_token()
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AZURE_TENANT_ID", "test-tenant-id")
    monkeypatch.setenv("AZURE_CLIENT_ID", "test-client-id")
    auth._jwks_cache._keys = None
    auth._jwks_cache._metadata = None
    monkeypatch.setattr(
        auth,
        "_fetch_openid_metadata",
        lambda tenant_id: {
            "issuer": f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            "jwks_uri": "https://entra.example.test/discovery/keys",
        },
    )
    monkeypatch.setattr(
        auth,
        "_fetch_json",
        lambda url: {"keys": [jwk]},
    )

    response = TestClient(create_app()).post(
        "/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "configuration": configuration,
            "metrics": metrics,
            "include_cost_signals": True,
            "include_feature_assessment": True,
        },
    )

    assert response.status_code == 200
