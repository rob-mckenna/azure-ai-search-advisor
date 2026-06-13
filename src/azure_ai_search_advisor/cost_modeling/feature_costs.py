"""Feature-level pricing helpers for Azure AI Search add-ons."""

from __future__ import annotations

from azure_ai_search_advisor.models.cost_models import (
    FeatureCostEstimate,
    FeatureCostInput,
    FeatureCostLineItem,
)

from azure_ai_search_advisor.cost_modeling.pricing_data import (
    APPROXIMATE_PRICING_NOTICE,
    APPROX_AI_ENRICHMENT_PRICE_PER_1K_TRANSACTIONS_USD,
    APPROX_SEMANTIC_RANKER_PRICE_PER_1K_QUERIES_USD,
    APPROX_VECTOR_STORAGE_PRICE_PER_GB_MONTH_USD,
)


def estimate_feature_costs(request: FeatureCostInput) -> FeatureCostEstimate:
    """Estimate feature-level costs with scaffolded pricing constants."""
    semantic_monthly_cost = round(
        (request.semantic_queries_per_month / 1000.0) * APPROX_SEMANTIC_RANKER_PRICE_PER_1K_QUERIES_USD,
        2,
    )
    enrichment_monthly_cost = round(
        (request.enrichment_transactions_per_month / 1000.0)
        * APPROX_AI_ENRICHMENT_PRICE_PER_1K_TRANSACTIONS_USD,
        2,
    )
    vector_storage_monthly_cost = round(
        request.vector_index_storage_gb * APPROX_VECTOR_STORAGE_PRICE_PER_GB_MONTH_USD,
        2,
    )

    line_items = [
        FeatureCostLineItem(
            feature_name="semantic_ranker",
            unit_label="1,000 semantic queries",
            unit_price_usd=APPROX_SEMANTIC_RANKER_PRICE_PER_1K_QUERIES_USD,
            usage_quantity=request.semantic_queries_per_month / 1000.0,
            estimated_monthly_cost_usd=semantic_monthly_cost,
            notes=["Approximate paid semantic query volume; verify free quotas for your tier."],
        ),
        FeatureCostLineItem(
            feature_name="ai_enrichment",
            unit_label="1,000 enrichment transactions",
            unit_price_usd=APPROX_AI_ENRICHMENT_PRICE_PER_1K_TRANSACTIONS_USD,
            usage_quantity=request.enrichment_transactions_per_month / 1000.0,
            estimated_monthly_cost_usd=enrichment_monthly_cost,
            notes=[
                "Uses one blended enrichment rate and excludes downstream Azure AI services, storage, and network charges."
            ],
        ),
        FeatureCostLineItem(
            feature_name="vector_storage",
            unit_label="GB-month",
            unit_price_usd=APPROX_VECTOR_STORAGE_PRICE_PER_GB_MONTH_USD,
            usage_quantity=request.vector_index_storage_gb,
            estimated_monthly_cost_usd=vector_storage_monthly_cost,
            notes=[
                "Estimates only vector index storage GB-month and excludes any extra search units needed to host larger indexes."
            ],
        ),
    ]

    estimated_monthly_cost_usd = round(sum(item.estimated_monthly_cost_usd for item in line_items), 2)
    estimated_period_cost_usd = round(estimated_monthly_cost_usd * request.months, 2)

    return FeatureCostEstimate(
        line_items=line_items,
        estimated_monthly_cost_usd=estimated_monthly_cost_usd,
        estimated_period_cost_usd=estimated_period_cost_usd,
        assumptions=[
            APPROXIMATE_PRICING_NOTICE,
            "Semantic cost is estimated from paid semantic query volume without subtracting tier-specific free allowances.",
            "AI enrichment cost uses a single per-1,000 transaction rate and does not model skill-specific billing differences.",
            "Vector cost reflects configured GB-month storage only and excludes embedding generation or external model charges.",
        ],
    )
