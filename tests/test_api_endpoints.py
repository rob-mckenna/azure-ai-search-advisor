from __future__ import annotations


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
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "azure-ai-search-advisor"



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
    body = response.json()
    assert body["status"] == "completed"
    assert body["comparison"]["current_estimate"]["monthly_total"] > 0
    assert body["comparison"]["proposed_estimate"]["monthly_total"] > 0
    assert body["comparison"]["monthly_delta"] < 0
