"""Configuration objects for the orchestration multi-agent system."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from azure_ai_search_advisor.orchestration.tools.analysis_tools import (
    analyze_features,
    analyze_provisioning,
    analyze_sku,
    run_full_analysis,
)
from azure_ai_search_advisor.orchestration.tools.cost_tools import (
    compare_pricing_models,
    estimate_cost,
)
from azure_ai_search_advisor.orchestration.tools.ingestion_tools import (
    ingest_config,
    ingest_config_file,
    validate_snapshot,
)
from azure_ai_search_advisor.orchestration.tools.recommendation_tools import (
    generate_recommendations,
)

ToolHandler = Callable[..., Any]


@dataclass(frozen=True)
class ModelSettings:
    """LLM deployment settings for a Foundry-hosted agent."""

    model: str
    temperature: float = 0.1
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class ToolBinding:
    """Plain-function tool metadata used for agent registration."""

    name: str
    handler: ToolHandler
    description: str

    @classmethod
    def from_function(cls, handler: ToolHandler) -> "ToolBinding":
        """Build a tool binding from a typed Python function."""
        return cls(
            name=handler.__name__,
            handler=handler,
            description=inspect.getdoc(handler) or f"Tool function: {handler.__name__}",
        )


@dataclass(frozen=True)
class AgentConfig:
    """System prompt, model settings, and tool catalog for an agent."""

    name: str
    description: str
    system_prompt: str
    model: ModelSettings
    tools: tuple[ToolBinding, ...] = field(default_factory=tuple)


ORCHESTRATOR_SYSTEM_PROMPT = """You are the Azure AI Search Advisor orchestrator agent running in Microsoft Foundry.
Decompose each user request into clear sub-tasks, delegate work to the specialist agents,
and assemble a final answer that is accurate, traceable, and action-oriented.
Always use the ingestion agent before analysis when the workload input is not yet validated.
Call the analysis agent for inefficiency detection, the cost agent for pricing trade-offs,
and the recommendation agent for final guidance. Do not rewrite domain logic in the prompt layer.
"""

INGESTION_SYSTEM_PROMPT = """You are the ingestion specialist for Azure AI Search Advisor.
Validate, normalize, and prepare Azure AI Search configuration snapshots for downstream agents.
Reject malformed inputs and preserve the validated snapshot contract used by the API layer.
"""

ANALYSIS_SYSTEM_PROMPT = """You are the analysis specialist for Azure AI Search Advisor.
Inspect validated workload inputs to detect provisioning inefficiencies, SKU mismatches,
and feature-usage issues. Return structured findings without inventing missing telemetry.
"""

COST_SYSTEM_PROMPT = """You are the cost modeling specialist for Azure AI Search Advisor.
Estimate dedicated, serverless, and feature-related cost scenarios for Azure AI Search workloads.
Explain assumptions clearly and compare pricing models without overstating certainty.
"""

RECOMMENDATION_SYSTEM_PROMPT = """You are the recommendation specialist for Azure AI Search Advisor.
Generate prioritized, actionable guidance from analysis and cost inputs.
Keep recommendations specific to Azure AI Search architecture, trade-offs, and implementation effort.
"""


DEFAULT_ORCHESTRATOR_MODEL = ModelSettings(model='foundry-orchestrator-model', temperature=0.1)
DEFAULT_SPECIALIST_MODEL = ModelSettings(model='foundry-specialist-model', temperature=0.0)



def build_agent_configs() -> dict[str, AgentConfig]:
    """Create the agent configuration map for the Foundry multi-agent system."""
    return {
        'orchestrator': AgentConfig(
            name='azure-ai-search-advisor-orchestrator',
            description='Top-level entry point that delegates to Azure AI Search specialist agents.',
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            model=DEFAULT_ORCHESTRATOR_MODEL,
        ),
        'ingestion': AgentConfig(
            name='azure-ai-search-advisor-ingestion',
            description='Validates and normalizes Azure AI Search workload snapshots.',
            system_prompt=INGESTION_SYSTEM_PROMPT,
            model=DEFAULT_SPECIALIST_MODEL,
            tools=tuple(
                ToolBinding.from_function(tool)
                for tool in (ingest_config, ingest_config_file, validate_snapshot)
            ),
        ),
        'analysis': AgentConfig(
            name='azure-ai-search-advisor-analysis',
            description='Detects provisioning, SKU, and feature inefficiencies.',
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            model=DEFAULT_SPECIALIST_MODEL,
            tools=tuple(
                ToolBinding.from_function(tool)
                for tool in (
                    analyze_provisioning,
                    analyze_sku,
                    analyze_features,
                    run_full_analysis,
                )
            ),
        ),
        'cost': AgentConfig(
            name='azure-ai-search-advisor-cost',
            description='Models dedicated, serverless, and comparative pricing scenarios.',
            system_prompt=COST_SYSTEM_PROMPT,
            model=DEFAULT_SPECIALIST_MODEL,
            tools=tuple(
                ToolBinding.from_function(tool)
                for tool in (estimate_cost, compare_pricing_models)
            ),
        ),
        'recommendation': AgentConfig(
            name='azure-ai-search-advisor-recommendation',
            description='Synthesizes recommendations from findings and cost trade-offs.',
            system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
            model=DEFAULT_SPECIALIST_MODEL,
            tools=tuple(ToolBinding.from_function(tool) for tool in (generate_recommendations,)),
        ),
    }
