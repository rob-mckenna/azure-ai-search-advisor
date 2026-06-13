"""Configuration objects for the orchestration multi-agent system."""

from __future__ import annotations

import inspect
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

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
OrchestrationMode = Literal['local', 'framework']


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


@dataclass(frozen=True)
class AgentCommunicationSettings:
    """Execution settings for specialist agent communication."""

    timeout_seconds: int = 30
    retry_attempts: int = 2


@dataclass(frozen=True)
class OrchestrationSettings:
    """Top-level orchestration runtime settings."""

    mode: OrchestrationMode = 'local'
    communication: AgentCommunicationSettings = field(
        default_factory=AgentCommunicationSettings
    )
    agent_models: dict[str, ModelSettings] = field(default_factory=dict)


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
DEFAULT_ORCHESTRATION_MODE: OrchestrationMode = 'local'


def get_orchestration_mode(default: OrchestrationMode = DEFAULT_ORCHESTRATION_MODE) -> OrchestrationMode:
    """Resolve the configured orchestration mode from the environment."""
    raw_mode = os.environ.get('ORCHESTRATION_MODE', default).strip().lower()
    return 'framework' if raw_mode == 'framework' else 'local'


def build_orchestration_settings() -> OrchestrationSettings:
    """Build orchestration runtime settings from environment variables."""
    return OrchestrationSettings(
        mode=get_orchestration_mode(),
        communication=AgentCommunicationSettings(
            timeout_seconds=_read_int_env('ORCHESTRATION_TIMEOUT_SECONDS', 30),
            retry_attempts=_read_int_env('ORCHESTRATION_RETRY_ATTEMPTS', 2),
        ),
        agent_models={
            'orchestrator': _build_model_settings(
                env_prefix='ORCHESTRATOR',
                default=DEFAULT_ORCHESTRATOR_MODEL,
            ),
            'ingestion': _build_model_settings(
                env_prefix='INGESTION_AGENT',
                default=DEFAULT_SPECIALIST_MODEL,
            ),
            'analysis': _build_model_settings(
                env_prefix='ANALYSIS_AGENT',
                default=DEFAULT_SPECIALIST_MODEL,
            ),
            'cost': _build_model_settings(
                env_prefix='COST_AGENT',
                default=DEFAULT_SPECIALIST_MODEL,
            ),
            'recommendation': _build_model_settings(
                env_prefix='RECOMMENDATION_AGENT',
                default=DEFAULT_SPECIALIST_MODEL,
            ),
        },
    )



def build_agent_configs(
    settings: OrchestrationSettings | None = None,
) -> dict[str, AgentConfig]:
    """Create the agent configuration map for the Foundry multi-agent system."""
    runtime_settings = settings or build_orchestration_settings()
    agent_models = runtime_settings.agent_models
    return {
        'orchestrator': AgentConfig(
            name='azure-ai-search-advisor-orchestrator',
            description='Top-level entry point that delegates to Azure AI Search specialist agents.',
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            model=agent_models['orchestrator'],
        ),
        'ingestion': AgentConfig(
            name='azure-ai-search-advisor-ingestion',
            description='Validates and normalizes Azure AI Search workload snapshots.',
            system_prompt=INGESTION_SYSTEM_PROMPT,
            model=agent_models['ingestion'],
            tools=tuple(
                ToolBinding.from_function(tool)
                for tool in (ingest_config, ingest_config_file, validate_snapshot)
            ),
        ),
        'analysis': AgentConfig(
            name='azure-ai-search-advisor-analysis',
            description='Detects provisioning, SKU, and feature inefficiencies.',
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            model=agent_models['analysis'],
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
            model=agent_models['cost'],
            tools=tuple(
                ToolBinding.from_function(tool)
                for tool in (estimate_cost, compare_pricing_models)
            ),
        ),
        'recommendation': AgentConfig(
            name='azure-ai-search-advisor-recommendation',
            description='Synthesizes recommendations from findings and cost trade-offs.',
            system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
            model=agent_models['recommendation'],
            tools=tuple(ToolBinding.from_function(tool) for tool in (generate_recommendations,)),
        ),
    }


def _build_model_settings(*, env_prefix: str, default: ModelSettings) -> ModelSettings:
    """Resolve per-agent model settings from environment variables."""
    normalized_prefix = env_prefix.upper()
    model = os.environ.get(f'{normalized_prefix}_MODEL', default.model)
    temperature = _read_float_env(
        f'{normalized_prefix}_TEMPERATURE',
        default.temperature,
    )
    max_output_tokens = _read_optional_int_env(
        f'{normalized_prefix}_MAX_OUTPUT_TOKENS',
        default.max_output_tokens,
    )
    return ModelSettings(
        model=model,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )


def _read_int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _read_optional_int_env(name: str, default: int | None) -> int | None:
    value = os.environ.get(name)
    if value is None or value.strip() == '':
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _read_float_env(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default
