"""Dependency providers for API routes."""

from __future__ import annotations

from functools import lru_cache

from azure_ai_search_advisor.analysis.service import AnalysisService
from azure_ai_search_advisor.cost_modeling.service import CostModelingService
from azure_ai_search_advisor.ingestion.service import IngestionService
from azure_ai_search_advisor.recommendations.service import RecommendationService


@lru_cache(maxsize=1)
def get_ingestion_service() -> IngestionService:
    """Provide the ingestion service dependency."""

    return IngestionService()


@lru_cache(maxsize=1)
def get_analysis_service() -> AnalysisService:
    """Provide the analysis service dependency."""

    return AnalysisService()


@lru_cache(maxsize=1)
def get_recommendation_service() -> RecommendationService:
    """Provide the recommendation service dependency."""

    return RecommendationService()


@lru_cache(maxsize=1)
def get_cost_modeling_service() -> CostModelingService:
    """Provide the cost modeling service dependency."""

    return CostModelingService()
