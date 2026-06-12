"""Recommendations domain package."""

from azure_ai_search_advisor.recommendations.feature_guidance import (
    generate_feature_guidance_recommendations,
)
from azure_ai_search_advisor.recommendations.pricing_advisor import (
    generate_pricing_model_recommendations,
)
from azure_ai_search_advisor.recommendations.rightsizing import (
    generate_rightsizing_recommendations,
)
from azure_ai_search_advisor.recommendations.service import RecommendationService

__all__ = [
    "RecommendationService",
    "generate_feature_guidance_recommendations",
    "generate_pricing_model_recommendations",
    "generate_rightsizing_recommendations",
]
