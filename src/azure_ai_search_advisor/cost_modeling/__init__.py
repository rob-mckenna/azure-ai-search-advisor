"""Cost modeling domain package."""

from azure_ai_search_advisor.cost_modeling.feature_costs import estimate_feature_costs
from azure_ai_search_advisor.cost_modeling.pricing_data import (
    APPROXIMATE_PRICING_NOTICE,
    DEDICATED_TIER_PRICING,
)
from azure_ai_search_advisor.cost_modeling.search_units import (
    calculate_search_units,
    estimate_search_unit_cost,
)
from azure_ai_search_advisor.cost_modeling.serverless_pricing import estimate_serverless_cost
from azure_ai_search_advisor.cost_modeling.service import CostModelingService

__all__ = [
    "APPROXIMATE_PRICING_NOTICE",
    "CostModelingService",
    "DEDICATED_TIER_PRICING",
    "calculate_search_units",
    "estimate_feature_costs",
    "estimate_search_unit_cost",
    "estimate_serverless_cost",
]
