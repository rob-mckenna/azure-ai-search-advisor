"""Agent wrapper around the recommendation domain service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.analysis import AnalysisResult
from azure_ai_search_advisor.cost_modeling.service import CostModelResponse
from azure_ai_search_advisor.models import RecommendationReport
from azure_ai_search_advisor.orchestration.config import AgentConfig
from azure_ai_search_advisor.orchestration.tools.recommendation_tools import (
    generate_recommendations,
)
from azure_ai_search_advisor.recommendations import RecommendationService


class RecommendationAgent:
    """Specialist agent for Azure AI Search guidance generation."""

    def __init__(
        self,
        *,
        config: AgentConfig,
        service: RecommendationService | None = None,
    ) -> None:
        self.config = config
        self.service = service or RecommendationService()

    def generate_recommendations(
        self,
        analysis: AnalysisResult | Mapping[str, Any],
        cost: CostModelResponse | Mapping[str, Any],
    ) -> RecommendationReport:
        """Generate prioritized recommendations from analysis and cost outputs."""
        return generate_recommendations(analysis, cost, service=self.service)
