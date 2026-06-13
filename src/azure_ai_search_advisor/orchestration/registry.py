"""Registry that wires the Microsoft Foundry multi-agent system together."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

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
from azure_ai_search_advisor.orchestration.config import (
    OrchestrationMode,
    OrchestrationSettings,
    build_agent_configs,
    build_orchestration_settings,
    get_orchestration_mode,
)
from azure_ai_search_advisor.orchestration.framework import (
    AgentFrameworkOrchestrator,
    FRAMEWORK_AVAILABLE,
)
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
        settings: OrchestrationSettings | None = None,
    ) -> None:
        self.ingestion_service = ingestion_service or IngestionService()
        self.analysis_service = analysis_service or AnalysisService()
        self.cost_modeling_service = cost_modeling_service or CostModelingService()
        self.recommendation_service = recommendation_service or RecommendationService()
        self.settings = settings or build_orchestration_settings()
        self._configs = build_agent_configs(self.settings)

    def build(self) -> OrchestratorAgent:
        """Return the fully wired local orchestrator agent."""
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

    def get_orchestrator(
        self,
        mode: OrchestrationMode | None = None,
    ) -> OrchestratorAgent | AgentFrameworkOrchestrator:
        """Return an orchestrator using the requested execution mode."""
        resolved_mode = mode or get_orchestration_mode(self.settings.mode)
        local_orchestrator = self.build()
        if resolved_mode == 'framework':
            return AgentFrameworkOrchestrator(
                local_orchestrator=local_orchestrator,
                communication_settings=self.settings.communication,
            )
        return local_orchestrator

    def register_framework_agents(self) -> dict[str, Any]:
        """Build framework-compatible specialist registrations when available."""
        orchestrator = self.get_orchestrator(mode='framework')
        if not isinstance(orchestrator, AgentFrameworkOrchestrator):
            return {}
        registrations = orchestrator.get_registered_agents()
        if not FRAMEWORK_AVAILABLE:
            return registrations
        return {
            key: registration.runtime_agent
            for key, registration in registrations.items()
        }

    def iter_specialist_functions(self) -> tuple[Callable[..., Any], ...]:
        """Return callable specialist tools for deployment registration."""
        specialist_agents = self.build()
        functions: list[Callable[..., Any]] = []
        for agent in (
            specialist_agents.ingestion_agent,
            specialist_agents.analysis_agent,
            specialist_agents.cost_agent,
            specialist_agents.recommendation_agent,
        ):
            for binding in agent.config.tools:
                functions.append(getattr(agent, binding.name))
        return tuple(functions)
