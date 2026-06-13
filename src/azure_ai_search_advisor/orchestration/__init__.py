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
    AgentCommunicationSettings,
    ModelSettings,
    OrchestrationSettings,
    ToolBinding,
    build_agent_configs,
    build_orchestration_settings,
)
from azure_ai_search_advisor.orchestration.framework import (
    AgentFrameworkOrchestrator,
    FRAMEWORK_AVAILABLE,
)
from azure_ai_search_advisor.orchestration.registry import AgentRegistry



def build_orchestrator() -> OrchestratorAgent:
    """Build the default orchestrator registry graph."""
    return AgentRegistry().build()


__all__ = [
    'AgentConfig',
    'AgentCommunicationSettings',
    'AgentFrameworkOrchestrator',
    'AgentRegistry',
    'AnalysisAgent',
    'CostAgent',
    'FRAMEWORK_AVAILABLE',
    'IngestionAgent',
    'ModelSettings',
    'OrchestrationSettings',
    'OrchestratorAgent',
    'OrchestratorPlan',
    'OrchestratorResponse',
    'RecommendationAgent',
    'ToolBinding',
    'build_agent_configs',
    'build_orchestration_settings',
    'build_orchestrator',
]
