"""Dedicated Search Unit pricing helpers."""

from __future__ import annotations

from azure_ai_search_advisor.models.cost_models import SearchUnitCostEstimate, SearchUnitCostInput

from azure_ai_search_advisor.cost_modeling.pricing_data import (
    APPROXIMATE_PRICING_NOTICE,
    get_pricing_reference,
)


def calculate_search_units(replicas: int, partitions: int) -> int:
    """Calculate total Search Units from replicas and partitions."""
    return replicas * partitions


def estimate_search_unit_cost(request: SearchUnitCostInput) -> SearchUnitCostEstimate:
    """Estimate dedicated tier costs using approximate Search Unit pricing."""
    pricing_reference = get_pricing_reference(request.tier)
    search_units = calculate_search_units(request.replicas, request.partitions)

    estimated_monthly_cost_usd = round(
        search_units * pricing_reference.monthly_cost_per_search_unit_usd,
        2,
    )
    estimated_period_cost_usd = round(estimated_monthly_cost_usd * request.months, 2)

    return SearchUnitCostEstimate(
        tier=request.tier,
        replicas=request.replicas,
        partitions=request.partitions,
        search_units=search_units,
        monthly_cost_per_search_unit_usd=pricing_reference.monthly_cost_per_search_unit_usd,
        estimated_monthly_cost_usd=estimated_monthly_cost_usd,
        estimated_period_cost_usd=estimated_period_cost_usd,
        assumptions=[
            APPROXIMATE_PRICING_NOTICE,
            "Estimate assumes the configured replicas and partitions stay provisioned for the full modeled period.",
        ],
        scaling_notes=[
            f"Computed as {request.replicas} replicas × {request.partitions} partitions.",
            "Cost is based on list price per search unit for the selected tier and excludes reservations, autoscale changes, and regional price adjustments.",
        ],
    )
