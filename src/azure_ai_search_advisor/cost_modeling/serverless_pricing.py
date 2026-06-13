"""Serverless query-based pricing helpers."""

from __future__ import annotations

from azure_ai_search_advisor.models.cost_models import ServerlessCostEstimate, ServerlessCostInput

from azure_ai_search_advisor.cost_modeling.pricing_data import (
    APPROXIMATE_PRICING_NOTICE,
    APPROX_SERVERLESS_PRICE_PER_1K_COMPUTE_UNITS_USD,
)


def estimate_serverless_cost(request: ServerlessCostInput) -> ServerlessCostEstimate:
    """Estimate serverless costs from billable compute units per query."""
    monthly_billable_compute_units = round(
        request.monthly_queries * request.average_billable_compute_units_per_query,
        2,
    )

    estimated_monthly_cost_usd = round(
        (monthly_billable_compute_units / 1000.0) * APPROX_SERVERLESS_PRICE_PER_1K_COMPUTE_UNITS_USD,
        2,
    )
    estimated_period_cost_usd = round(estimated_monthly_cost_usd * request.months, 2)

    return ServerlessCostEstimate(
        monthly_queries=request.monthly_queries,
        monthly_billable_compute_units=monthly_billable_compute_units,
        price_per_1k_compute_units_usd=APPROX_SERVERLESS_PRICE_PER_1K_COMPUTE_UNITS_USD,
        estimated_monthly_cost_usd=estimated_monthly_cost_usd,
        estimated_period_cost_usd=estimated_period_cost_usd,
        assumptions=[
            APPROXIMATE_PRICING_NOTICE,
            "Monthly billable compute units are estimated as monthly queries multiplied by the average billable compute units per query.",
            "Estimate excludes free grants, billing rounding behavior, and workload-specific query complexity variation.",
        ],
    )
