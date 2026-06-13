from __future__ import annotations

from datetime import datetime, timezone

from azure_ai_search_advisor.api.schemas import (
    AnalysisSummary,
    AnalyzeResponse,
    PricingModel,
    SearchCapacity,
    SearchFeatureFlags,
    SearchIndexTopology,
    SearchSecurityConfiguration,
    SearchServiceConfiguration,
    SearchWorkloadMetrics,
    SeverityLevel,
    QueryMetrics,
    IndexingMetrics,
    UtilizationMetrics,
)
from azure_ai_search_advisor.api.service_adapters import build_recommendation_inputs
from azure_ai_search_advisor.cost_modeling.service import CostModelingService
from azure_ai_search_advisor.models.cost_models import (
    CostModelRequest,
    FeatureCostInput,
    PricingModelOption,
    PricingTier,
    SearchUnitCostInput,
    ServerlessCostInput,
)
from azure_ai_search_advisor.recommendations.service import RecommendationService


def test_cost_modeling_reports_lower_cost_option_and_assumptions() -> None:
    result = CostModelingService().simulate(
        CostModelRequest(
            dedicated_search=SearchUnitCostInput(tier=PricingTier.S1, replicas=2, partitions=1),
            serverless_search=ServerlessCostInput(
                monthly_queries=100_000,
                average_billable_compute_units_per_query=1.0,
            ),
            feature_costs=FeatureCostInput(
                semantic_queries_per_month=10_000,
                enrichment_transactions_per_month=5_000,
                vector_index_storage_gb=2.0,
            ),
        )
    )

    assert result.comparison.lower_cost_option == PricingModelOption.SERVERLESS
    assert any("Serverless is estimated to be cheaper by" in note for note in result.notes)
    assert all("TODO" not in item for item in result.breakdown.assumptions)
    assert all("TODO" not in item for item in result.comparison.notes)


def test_empty_recommendation_summary_is_operator_friendly() -> None:
    report = RecommendationService().recommend({}, {})

    assert report.summary == "No optimization opportunities identified for this workload."



def test_alerting_recommendations_are_generated_from_operational_signals() -> None:
    report = RecommendationService().recommend(
        {
            "service": {"service_name": "contoso-search", "replicas": 2, "indexer_count": 2},
            "alerting": {
                "query_latency_p95_ms": 720.0,
                "replica_utilization_percent": 22.0,
                "storage_utilization_percent": 88.0,
                "throttled_queries_per_day": 14.0,
                "avg_queries_per_second": 0.4,
                "avg_cpu_utilization_pct": 91.0,
                "indexer_count": 2,
                "indexer_monitoring_configured": False,
            },
        },
        {},
    )

    titles = {item.title for item in report.recommendations}
    assert "Add latency alert: p95 > 500ms for 5 min" in titles
    assert "Add utilization alert: < 30% for 1 hour" in titles
    assert "Add storage alert: > 80% utilization" in titles
    assert "Add throttling alert: > 0 throttled queries" in titles
    assert "Add indexer failure alert" in titles
    assert "Add idle-service cost alert: < 1 QPS for 24 hours" in titles
    assert "Add CPU alert: > 80% for 15 min (scale trigger)" in titles
    assert all(item.category == "alerting" for item in report.recommendations)
    assert all(item.effort == "low" for item in report.recommendations)



def test_build_recommendation_inputs_includes_alerting_signals() -> None:
    analysis = AnalyzeResponse(
        request_id="anl_test",
        status="completed",
        generated_at=datetime.now(timezone.utc),
        summary=AnalysisSummary(
            finding_count=0,
            highest_severity=SeverityLevel.LOW,
            optimization_themes=[],
            overall_assessment="No findings.",
        ),
        findings=[],
        notes=[],
    )
    configuration = SearchServiceConfiguration(
        service_name="contoso-search",
        region="eastus",
        capacity=SearchCapacity(
            pricing_model=PricingModel.DEDICATED,
            sku="standard",
            replica_count=2,
            partition_count=1,
            zone_redundancy_enabled=False,
        ),
        features=SearchFeatureFlags(
            semantic_ranker_enabled=False,
            vector_search_enabled=False,
            ai_enrichment_enabled=False,
            knowledge_store_enabled=False,
        ),
        index_topology=SearchIndexTopology(
            index_count=3,
            indexer_count=2,
            skillset_count=0,
            total_document_count=100_000,
            total_index_size_gb=12.0,
            vector_index_size_gb=0.0,
        ),
        security=SearchSecurityConfiguration(
            api_keys_enabled=True,
            managed_identity_enabled=False,
            private_endpoint_enabled=False,
            customer_managed_keys_enabled=False,
        ),
        notes=[],
    )
    metrics = SearchWorkloadMetrics(
        observation_window_days=30,
        query=QueryMetrics(
            average_queries_per_second=0.5,
            peak_queries_per_second=2.0,
            monthly_query_volume=50_000,
            p95_query_latency_ms=650.0,
            cache_hit_ratio=0.2,
        ),
        indexing=IndexingMetrics(
            daily_document_updates=500,
            full_rebuilds_per_month=1,
            average_indexing_latency_minutes=10.0,
        ),
        utilization=UtilizationMetrics(
            replica_utilization_percent=84.0,
            partition_utilization_percent=40.0,
            storage_utilization_percent=87.0,
            semantic_queries_per_day=0,
            vector_queries_per_day=0,
        ),
    )

    analysis_findings, _ = build_recommendation_inputs(analysis, configuration, metrics, None)

    assert analysis_findings["service"]["service_name"] == "contoso-search"
    assert analysis_findings["alerting"] == {
        "indexer_count": 2,
        "indexer_monitoring_configured": False,
        "query_latency_p95_ms": 650.0,
        "replica_utilization_percent": 84.0,
        "storage_utilization_percent": 87.0,
        "throttled_queries_per_day": 0.0,
        "avg_queries_per_second": 0.5,
        "avg_cpu_utilization_pct": 84.0,
    }
