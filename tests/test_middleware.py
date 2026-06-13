from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from azure_ai_search_advisor.api.rate_limit import _rate_limiter
from azure_ai_search_advisor.main import create_app


@pytest.fixture(autouse=True)
def reset_rate_limiter_state(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_ENABLED", raising=False)
    monkeypatch.delenv("RATE_LIMIT_REQUESTS", raising=False)
    monkeypatch.delenv("RATE_LIMIT_WINDOW_SECONDS", raising=False)
    _rate_limiter._requests.clear()
    yield
    _rate_limiter._requests.clear()



def _simulate_payload() -> dict:
    return {
        "cost_model_request": {
            "dedicated_search": {
                "tier": "s1",
                "replicas": 2,
                "partitions": 1,
                "months": 1.0,
            },
            "serverless_search": {
                "monthly_queries": 1000,
                "average_billable_compute_units_per_query": 1.0,
                "months": 1.0,
            },
        },
        "assumptions": {
            "pricing_horizon_days": 30,
            "currency": "USD",
            "notes": [],
        },
    }



def test_correlation_id_is_generated_when_not_provided() -> None:
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    correlation_id = response.headers["X-Correlation-ID"]
    assert correlation_id
    UUID(correlation_id)



def test_correlation_id_is_preserved_from_request_header() -> None:
    response = TestClient(create_app()).get(
        "/health",
        headers={"X-Correlation-ID": "req-correlation-id"},
    )

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "req-correlation-id"



def test_rate_limiting_returns_429_when_exceeded(monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    client = TestClient(create_app())
    headers = {"X-Forwarded-For": "198.51.100.10"}

    first_response = client.post("/simulate", headers=headers, json=_simulate_payload())
    second_response = client.post("/simulate", headers=headers, json=_simulate_payload())

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.headers["Retry-After"] == "60"
    assert second_response.json()["message"] == "Rate limit exceeded. Try again later."



def test_rate_limiting_passes_when_under_limit(monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    client = TestClient(create_app())
    headers = {"X-Forwarded-For": "198.51.100.11"}

    first_response = client.post("/simulate", headers=headers, json=_simulate_payload())
    second_response = client.post("/simulate", headers=headers, json=_simulate_payload())

    assert first_response.status_code == 200
    assert second_response.status_code == 200
