"""End-to-end integration tests for the full advisory pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from azure_ai_search_advisor.analysis.service import AnalysisRequest, AnalysisService
from azure_ai_search_advisor.cost_modeling.service import CostModelingService
from azure_ai_search_advisor.ingestion.service import IngestionService
from azure_ai_search_advisor.models.cost_models import (
    CostModelRequest,
    FeatureCostInput,
    PricingTier,
    SearchUnitCostInput,
    ServerlessCostInput,
)
from azure_ai_search_advisor.recommendations.service import RecommendationService

DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "inputs"


@pytest.fixture
def ingestion_service() -> IngestionService:
    return IngestionService(data_root=DATA_ROOT)


@pytest.fixture
def analysis_service() -> AnalysisService:
    return AnalysisService()


@pytest.fixture
def cost_service() -> CostModelingService:
    return CostModelingService()


@pytest.fixture
def recommendation_service() -> RecommendationService:
    return RecommendationService()


class TestEndToEndPipeline:
    """Full ingest → analyze → cost → recommend pipeline."""

    def test_over_provisioned_produces_findings_and_recommendations(
        self,
        ingestion_service: IngestionService,
        analysis_service: AnalysisService,
        cost_service: CostModelingService,
        recommendation_service: RecommendationService,
    ) -> None:
        """Over-provisioned service should produce findings and actionable recommendations."""
        # Ingest
        snapshot = ingestion_service.ingest_file(DATA_ROOT / "over_provisioned.json")
        assert snapshot.configuration.service_name is not None

        # Analyze
        analysis_result = analysis_service.analyze(
            AnalysisRequest(
                configuration=snapshot.configuration,
                metrics=snapshot.metrics,
            )
        )
        assert len(analysis_result.findings) > 0
        severities = {f.severity for f in analysis_result.findings}
        assert "medium" in severities or "high" in severities

        # Cost model
        cost_result = cost_service.simulate(
            CostModelRequest(
                dedicated_search=SearchUnitCostInput(
                    tier=PricingTier.S2,
                    replicas=snapshot.configuration.replicas or 1,
                    partitions=snapshot.configuration.partitions or 1,
                ),
                serverless_search=ServerlessCostInput(
                    monthly_queries=snapshot.metrics.query_volume.monthly_queries,
                ),
                feature_costs=FeatureCostInput(
                    semantic_queries_per_month=int(
                        snapshot.metrics.query_volume.monthly_queries
                        * snapshot.metrics.feature_usage.semantic_query_percentage
                        / 100
                    ),
                    vector_index_storage_gb=snapshot.metrics.total_index_size_gb * 0.3,
                ),
            )
        )
        assert cost_result.breakdown.dedicated_total_monthly_cost_usd > 0
        assert cost_result.comparison is not None

        # Recommend
        findings_dict = {
            "topology": {
                "replica_overprovisioned": any(
                    "replica" in (f.title or "").lower() for f in analysis_result.findings
                ),
                "partition_overprovisioned": any(
                    "partition" in (f.title or "").lower() for f in analysis_result.findings
                ),
                "suggested_replicas": max((snapshot.configuration.replicas or 1) - 2, 1),
                "estimated_monthly_savings": 500.0,
            },
            "service": {
                "replicas": snapshot.configuration.replicas,
                "partitions": snapshot.configuration.partitions,
                "sku": snapshot.configuration.sku.value,
                "hosting_mode": snapshot.configuration.deployment_mode.value,
            },
            "features": {
                "semantic_ranker_enabled": snapshot.configuration.semantic_ranker.enabled,
                "semantic_query_ratio": snapshot.metrics.feature_usage.semantic_query_percentage / 100,
                "vector_search_enabled": snapshot.configuration.vector_search.enabled,
            },
            "pricing": {},
        }
        cost_dict = {
            "scenario_comparison": {
                "recommended_monthly_savings": abs(cost_result.comparison.monthly_difference_usd),
            },
        }
        rec_result = recommendation_service.recommend(findings_dict, cost_dict)
        assert len(rec_result.recommendations) > 0
        assert rec_result.summary != ""
        assert rec_result.estimated_savings["monthly_usd"] > 0

    def test_well_optimized_produces_fewer_findings(
        self,
        ingestion_service: IngestionService,
        analysis_service: AnalysisService,
    ) -> None:
        """Well-optimized service should produce fewer or no high-severity findings."""
        snapshot = ingestion_service.ingest_file(DATA_ROOT / "well_optimized.json")
        analysis_result = analysis_service.analyze(
            AnalysisRequest(
                configuration=snapshot.configuration,
                metrics=snapshot.metrics,
            )
        )
        high_severity = [f for f in analysis_result.findings if f.severity == "high"]
        # Well-optimized should have fewer high-severity findings than over-provisioned
        assert len(high_severity) <= 2

    def test_all_mock_scenarios_ingest_and_analyze_without_error(
        self,
        ingestion_service: IngestionService,
        analysis_service: AnalysisService,
    ) -> None:
        """Every mock data file should be processable without exceptions."""
        snapshots = ingestion_service.ingest_directory()
        assert len(snapshots) == 4

        for snapshot in snapshots:
            result = analysis_service.analyze(
                AnalysisRequest(
                    configuration=snapshot.configuration,
                    metrics=snapshot.metrics,
                )
            )
            # Should not raise; findings may be empty for well-optimized
            assert isinstance(result.findings, list)
