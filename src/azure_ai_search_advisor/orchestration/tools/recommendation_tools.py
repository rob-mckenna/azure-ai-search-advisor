"""Tool functions that expose recommendation generation capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.analysis import AnalysisResult
from azure_ai_search_advisor.cost_modeling.service import CostModelResponse
from azure_ai_search_advisor.models import RecommendationReport
from azure_ai_search_advisor.recommendations import RecommendationService



def generate_recommendations(
    analysis: AnalysisResult | Mapping[str, Any],
    cost: CostModelResponse | Mapping[str, Any],
    *,
    service: RecommendationService | None = None,
) -> RecommendationReport:
    """Generate prioritized Azure AI Search guidance from analysis and cost outputs."""
    recommendation_service = service or RecommendationService()
    return recommendation_service.recommend(
        _as_serializable_mapping(analysis),
        _as_serializable_mapping(cost),
    )



def _as_serializable_mapping(value: AnalysisResult | CostModelResponse | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    model_dump = getattr(value, 'model_dump', None)
    if callable(model_dump):
        return model_dump()
    return value.dict()
