"""Approximate pricing references for Azure AI Search cost scaffolding."""

from __future__ import annotations

from azure_ai_search_advisor.models.cost_models import PricingReference, PricingTier

PRICING_DATA_VERSION = "2026-06 approximate scaffold"
APPROXIMATE_PRICING_NOTICE = (
    "Approximate Azure AI Search pricing for scaffolding only. Values vary by region, currency, "
    "reservation, and feature availability; verify against official Azure pricing before production use."
)

DEDICATED_TIER_PRICING: dict[PricingTier, PricingReference] = {
    PricingTier.FREE: PricingReference(
        tier=PricingTier.FREE,
        monthly_cost_per_search_unit_usd=0.0,
        included_search_units=1,
        notes=["Free tier has limited capacity and is not intended for production workloads."],
    ),
    PricingTier.BASIC: PricingReference(
        tier=PricingTier.BASIC,
        monthly_cost_per_search_unit_usd=75.0,
        included_search_units=1,
        notes=["Approximate monthly price per Search Unit for Basic tier."],
    ),
    PricingTier.S1: PricingReference(
        tier=PricingTier.S1,
        monthly_cost_per_search_unit_usd=250.0,
        included_search_units=1,
        notes=["Approximate monthly price per Search Unit for S1 tier."],
    ),
    PricingTier.S2: PricingReference(
        tier=PricingTier.S2,
        monthly_cost_per_search_unit_usd=1000.0,
        included_search_units=1,
        notes=["Approximate monthly price per Search Unit for S2 tier."],
    ),
    PricingTier.S3: PricingReference(
        tier=PricingTier.S3,
        monthly_cost_per_search_unit_usd=2000.0,
        included_search_units=1,
        notes=["Approximate monthly price per Search Unit for S3 tier."],
    ),
    PricingTier.L1: PricingReference(
        tier=PricingTier.L1,
        monthly_cost_per_search_unit_usd=2800.0,
        included_search_units=1,
        notes=["Approximate monthly price per Search Unit for storage-optimized L1 tier."],
    ),
    PricingTier.L2: PricingReference(
        tier=PricingTier.L2,
        monthly_cost_per_search_unit_usd=5600.0,
        included_search_units=1,
        notes=["Approximate monthly price per Search Unit for storage-optimized L2 tier."],
    ),
}

APPROX_SERVERLESS_PRICE_PER_1K_COMPUTE_UNITS_USD = 0.12
APPROX_SEMANTIC_RANKER_PRICE_PER_1K_QUERIES_USD = 1.0
APPROX_AI_ENRICHMENT_PRICE_PER_1K_TRANSACTIONS_USD = 1.5
APPROX_VECTOR_STORAGE_PRICE_PER_GB_MONTH_USD = 0.12


def get_pricing_reference(tier: PricingTier) -> PricingReference:
    """Return approximate dedicated pricing data for a tier."""
    return DEDICATED_TIER_PRICING[tier]
