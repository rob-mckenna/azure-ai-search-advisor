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



def test_dedicated_only_cost_estimate_handles_missing_serverless_input() -> None:
    result = CostModelingService().simulate(
        CostModelRequest(
            dedicated_search=SearchUnitCostInput(tier=PricingTier.S1, replicas=2, partitions=2),
        )
    )

    assert result.breakdown.dedicated is not None
    assert result.breakdown.serverless is None
    assert result.breakdown.dedicated_total_monthly_cost_usd == 1000.0
    assert result.breakdown.serverless_total_monthly_cost_usd == 0.0
    assert result.comparison.lower_cost_option is None
    assert any("Comparison is partial" in note for note in result.comparison.notes)



def test_serverless_only_cost_estimate_handles_missing_dedicated_input() -> None:
    result = CostModelingService().simulate(
        CostModelRequest(
            serverless_search=ServerlessCostInput(
                monthly_queries=50_000,
                average_billable_compute_units_per_query=1.5,
            ),
        )
    )

    assert result.breakdown.dedicated is None
    assert result.breakdown.serverless is not None
    assert result.breakdown.serverless.monthly_billable_compute_units == 75_000
    assert result.breakdown.serverless_total_monthly_cost_usd == 9.0
    assert result.breakdown.dedicated_total_monthly_cost_usd == 0.0
    assert result.comparison.lower_cost_option is None
    assert any("Comparison is partial" in note for note in result.comparison.notes)



def test_zero_queries_produces_zero_serverless_cost() -> None:
    result = CostModelingService().simulate(
        CostModelRequest(
            serverless_search=ServerlessCostInput(
                monthly_queries=0,
                average_billable_compute_units_per_query=3.2,
            ),
        )
    )

    assert result.breakdown.serverless is not None
    assert result.breakdown.serverless.monthly_queries == 0
    assert result.breakdown.serverless.monthly_billable_compute_units == 0.0
    assert result.breakdown.serverless.estimated_monthly_cost_usd == 0.0
    assert result.breakdown.serverless_total_monthly_cost_usd == 0.0



def test_very_high_query_volume_favors_dedicated_when_serverless_spend_is_higher() -> None:
    result = CostModelingService().simulate(
        CostModelRequest(
            dedicated_search=SearchUnitCostInput(tier=PricingTier.S1, replicas=2, partitions=2),
            serverless_search=ServerlessCostInput(
                monthly_queries=100_000_000,
                average_billable_compute_units_per_query=2.0,
            ),
        )
    )

    assert result.breakdown.serverless is not None
    assert result.breakdown.serverless.monthly_billable_compute_units == 200_000_000.0
    assert result.breakdown.serverless.estimated_monthly_cost_usd == 24000.0
    assert result.comparison.lower_cost_option == PricingModelOption.DEDICATED
    assert result.comparison.monthly_difference_usd == -23000.0



def test_feature_costs_with_all_features_enabled() -> None:
    result = CostModelingService().simulate(
        CostModelRequest(
            feature_costs=FeatureCostInput(
                semantic_queries_per_month=1_000,
                enrichment_transactions_per_month=1_000,
                vector_index_storage_gb=10.0,
            )
        )
    )

    assert result.breakdown.features.estimated_monthly_cost_usd == 3.7
    assert [item.feature_name for item in result.breakdown.features.line_items] == [
        "semantic_ranker",
        "ai_enrichment",
        "vector_storage",
    ]
    assert [item.estimated_monthly_cost_usd for item in result.breakdown.features.line_items] == [1.0, 1.5, 1.2]



def test_feature_costs_with_no_features_enabled() -> None:
    result = CostModelingService().simulate(CostModelRequest(feature_costs=FeatureCostInput()))

    assert result.breakdown.features.estimated_monthly_cost_usd == 0.0
    assert all(item.estimated_monthly_cost_usd == 0.0 for item in result.breakdown.features.line_items)
    assert result.breakdown.dedicated_total_monthly_cost_usd == 0.0
    assert result.breakdown.serverless_total_monthly_cost_usd == 0.0



def test_compare_options_leaves_lower_cost_empty_when_costs_are_equal() -> None:
    comparison = CostModelingService().compare_options(
        125.0,
        125.0,
        has_dedicated_model=True,
        has_serverless_model=True,
    )

    assert comparison.monthly_difference_usd == 0.0
    assert comparison.lower_cost_option is None
    assert "Dedicated and serverless are estimated to have the same monthly cost." in comparison.notes
