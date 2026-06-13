from __future__ import annotations

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
