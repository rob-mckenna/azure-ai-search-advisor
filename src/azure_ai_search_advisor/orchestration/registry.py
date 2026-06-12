"""Registry that wires the Microsoft Foundry multi-agent system together."""

from __future__ import annotations

from azure_ai_search_advisor.analysis import AnalysisService
from azure_ai_search_advisor.cost_modeling import CostModelingService
from azure_ai_search_advisor.ingestion import IngestionService
from azure_ai_search_advisor.orchestration.agents.analysis_agent import AnalysisAgent
from azure_ai_search_advisor.orchestration.agents.cost_agent import CostAgent
from azure_ai_search_advisor.orchestration.agents.ingestion_agent import IngestionAgent
from azure_ai_search_advisor.orchestration.agents.orchestrator import OrchestratorAgent
from azure_ai_search_advisor.orchestration.agents.recommendation_agent import (
    RecommendationAgent,
)
from azure_ai_search_advisor.orchestration.config import build_agent_configs
from azure_ai_search_advisor.recommendations import RecommendationService


class AgentRegistry:
    """Creates a configured orchestrator and its specialist agents."""

    def __init__(
        self,
        *,
        ingestion_service: IngestionService | None = None,
        analysis_service: AnalysisService | None = None,
        cost_modeling_service: CostModelingService | None = None,
        recommendation_service: RecommendationService | None = None,
    ) -> None:
        self.ingestion_service = ingestion_service or IngestionService()
        self.analysis_service = analysis_service or AnalysisService()
        self.cost_modeling_service = cost_modeling_service or CostModelingService()
        self.recommendation_service = recommendation_service or RecommendationService()
        self._configs = build_agent_configs()

    def build(self) -> OrchestratorAgent:
        """Return the fully wired top-level orchestrator agent."""
        ingestion_agent = IngestionAgent(
            config=self._configs['ingestion'],
            service=self.ingestion_service,
        )
        analysis_agent = AnalysisAgent(
            config=self._configs['analysis'],
            service=self.analysis_service,
        )
        cost_agent = CostAgent(
            config=self._configs['cost'],
            service=self.cost_modeling_service,
        )
        recommendation_agent = RecommendationAgent(
            config=self._configs['recommendation'],
            service=self.recommendation_service,
        )
        return OrchestratorAgent(
            config=self._configs['orchestrator'],
            ingestion_agent=ingestion_agent,
            analysis_agent=analysis_agent,
            cost_agent=cost_agent,
            recommendation_agent=recommendation_agent,
        )
