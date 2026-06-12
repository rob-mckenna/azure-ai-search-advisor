"""Microsoft Foundry multi-agent orchestration layer for Azure AI Search Advisor."""

from azure_ai_search_advisor.orchestration.agents import (
    AnalysisAgent,
    CostAgent,
    IngestionAgent,
    OrchestratorAgent,
    OrchestratorPlan,
    OrchestratorResponse,
    RecommendationAgent,
)
from azure_ai_search_advisor.orchestration.config import (
    AgentConfig,
    ModelSettings,
    ToolBinding,
    build_agent_configs,
)
from azure_ai_search_advisor.orchestration.registry import AgentRegistry



def build_orchestrator() -> OrchestratorAgent:
    """Build the default orchestrator registry graph."""
    return AgentRegistry().build()


__all__ = [
    'AgentConfig',
    'AgentRegistry',
    'AnalysisAgent',
    'CostAgent',
    'IngestionAgent',
    'ModelSettings',
    'OrchestratorAgent',
    'OrchestratorPlan',
    'OrchestratorResponse',
    'RecommendationAgent',
    'ToolBinding',
    'build_agent_configs',
    'build_orchestrator',
]
