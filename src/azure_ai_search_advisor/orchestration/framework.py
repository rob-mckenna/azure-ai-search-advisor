"""Optional Microsoft Agent Framework orchestration integration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from azure_ai_search_advisor.analysis import AnalysisResult
from azure_ai_search_advisor.models import AzureSearchServiceSnapshot, CostModelResponse
from azure_ai_search_advisor.models import RecommendationReport
from azure_ai_search_advisor.orchestration.agents.orchestrator import (
    OrchestratorAgent,
    OrchestratorResponse,
)
from azure_ai_search_advisor.orchestration.config import (
    AgentCommunicationSettings,
    ToolBinding,
)

try:
    from microsoft.agents.core import Agent, Message, Tool

    FRAMEWORK_AVAILABLE = True
except ImportError:  # pragma: no cover - optional runtime dependency
    FRAMEWORK_AVAILABLE = False

    @dataclass(frozen=True)
    class Message:
        """Fallback message envelope used when the SDK is unavailable."""

        role: str
        content: str
        metadata: dict[str, Any] = field(default_factory=dict)

    @dataclass(frozen=True)
    class Tool:
        """Fallback tool wrapper used when the SDK is unavailable."""

        name: str
        description: str
        handler: Callable[..., Any]

    @dataclass(frozen=True)
    class Agent:
        """Fallback agent descriptor used when the SDK is unavailable."""

        name: str
        description: str
        instructions: str
        tools: tuple[Tool, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RegisteredFrameworkAgent:
    """Local representation of a framework-registered specialist."""

    name: str
    description: str
    instructions: str
    tools: dict[str, Tool]
    handlers: dict[str, Callable[..., Any]]
    runtime_agent: Any


class AgentFrameworkOrchestrator:
    """Wrap the local orchestrator with Agent Framework registration semantics."""

    def __init__(
        self,
        *,
        local_orchestrator: OrchestratorAgent,
        communication_settings: AgentCommunicationSettings,
    ) -> None:
        self.local_orchestrator = local_orchestrator
        self.config = local_orchestrator.config
        self.communication_settings = communication_settings
        self.framework_available = FRAMEWORK_AVAILABLE
        self._registered_agents = self._register_specialists()
        self.framework_agent = self._build_framework_agent()

    def handle_request(
        self,
        user_query: str,
        *,
        payload: Mapping[str, Any] | None = None,
        snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
        snapshot_path: str | None = None,
        include_cost_analysis: bool = True,
        include_recommendations: bool = True,
    ) -> OrchestratorResponse:
        """Route a request through specialist-agent tool calls when available."""
        if not self.framework_available:
            return self.local_orchestrator.handle_request(
                user_query,
                payload=payload,
                snapshot=snapshot,
                snapshot_path=snapshot_path,
                include_cost_analysis=include_cost_analysis,
                include_recommendations=include_recommendations,
            )

        plan = self.local_orchestrator.decompose_query(
            user_query,
            include_cost_analysis=include_cost_analysis,
            include_recommendations=include_recommendations,
        )
        transcript: list[Message] = [
            self._build_message(
                role='user',
                content=user_query,
                metadata={
                    'requested_cost_analysis': plan.include_cost_modeling,
                    'requested_recommendations': plan.include_recommendations,
                },
            )
        ]

        resolved_snapshot = self._invoke_ingestion_agent(
            transcript=transcript,
            payload=payload,
            snapshot=snapshot,
            snapshot_path=snapshot_path,
        )
        if resolved_snapshot is None:
            return OrchestratorResponse(
                user_query=user_query,
                plan=plan,
                summary='No workload input was supplied. Returning the orchestrator plan only.',
                notes=[
                    'Provide a snapshot payload or snapshot_path for end-to-end execution.',
                    'Framework mode will request missing workload context through specialist-agent messages when hosted.',
                ],
            )

        analysis_result = self._invoke_specialist(
            specialist_key='analysis',
            tool_name='run_full_analysis',
            transcript=transcript,
            message_content='Run the full workload analysis pipeline for the validated Azure AI Search snapshot.',
            snapshot=resolved_snapshot,
        )
        cost_result = (
            self._invoke_specialist(
                specialist_key='cost',
                tool_name='estimate_cost',
                transcript=transcript,
                message_content='Estimate dedicated and serverless pricing scenarios for the validated workload.',
                snapshot=resolved_snapshot,
            )
            if plan.include_cost_modeling
            else None
        )
        recommendation_result = (
            self._invoke_specialist(
                specialist_key='recommendation',
                tool_name='generate_recommendations',
                transcript=transcript,
                message_content='Generate prioritized recommendations from the analysis and cost outputs.',
                analysis=analysis_result,
                cost=cost_result or {'scenario_comparison': {}, 'potential_monthly_savings': 0.0},
            )
            if plan.include_recommendations
            else None
        )

        return OrchestratorResponse(
            user_query=user_query,
            plan=plan,
            summary=self.local_orchestrator.build_summary(
                analysis=analysis_result,
                cost=cost_result,
                recommendations=recommendation_result,
            ),
            snapshot=resolved_snapshot,
            analysis=analysis_result,
            cost=cost_result,
            recommendations=recommendation_result,
            notes=self._build_notes(transcript),
        )

    def specialist_tool_manifest(self) -> dict[str, tuple[ToolBinding, ...]]:
        """Expose the specialist tool catalog for deployment and inspection."""
        return self.local_orchestrator.specialist_tool_manifest()

    def get_registered_agents(self) -> dict[str, RegisteredFrameworkAgent]:
        """Return the registered specialist agents keyed by role."""
        return dict(self._registered_agents)

    def _register_specialists(self) -> dict[str, RegisteredFrameworkAgent]:
        registry: dict[str, RegisteredFrameworkAgent] = {}
        specialist_agents = {
            'ingestion': self.local_orchestrator.ingestion_agent,
            'analysis': self.local_orchestrator.analysis_agent,
            'cost': self.local_orchestrator.cost_agent,
            'recommendation': self.local_orchestrator.recommendation_agent,
        }
        for key, specialist in specialist_agents.items():
            tools = {
                binding.name: self._build_tool(binding, getattr(specialist, binding.name))
                for binding in specialist.config.tools
            }
            registry[key] = RegisteredFrameworkAgent(
                name=specialist.config.name,
                description=specialist.config.description,
                instructions=specialist.config.system_prompt,
                tools=tools,
                handlers={
                    binding.name: getattr(specialist, binding.name)
                    for binding in specialist.config.tools
                },
                runtime_agent=self._build_agent(
                    name=specialist.config.name,
                    description=specialist.config.description,
                    instructions=specialist.config.system_prompt,
                    tools=tuple(tools.values()),
                ),
            )
        return registry

    def _build_framework_agent(self) -> Any:
        return self._build_agent(
            name=self.config.name,
            description=self.config.description,
            instructions=self.config.system_prompt,
            tools=tuple(),
        )

    def _invoke_ingestion_agent(
        self,
        *,
        transcript: list[Message],
        payload: Mapping[str, Any] | None,
        snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None,
        snapshot_path: str | None,
    ) -> AzureSearchServiceSnapshot | None:
        if snapshot is not None:
            return self._invoke_specialist(
                specialist_key='ingestion',
                tool_name='validate_snapshot',
                transcript=transcript,
                message_content='Validate the supplied workload snapshot for downstream specialist use.',
                snapshot=snapshot,
            )
        if payload is not None:
            return self._invoke_specialist(
                specialist_key='ingestion',
                tool_name='ingest_config',
                transcript=transcript,
                message_content='Validate and normalize the supplied workload payload.',
                payload=payload,
            )
        if snapshot_path is not None:
            return self._invoke_specialist(
                specialist_key='ingestion',
                tool_name='ingest_config_file',
                transcript=transcript,
                message_content='Load and validate the workload snapshot stored on disk.',
                path=snapshot_path,
            )
        return None

    def _invoke_specialist(
        self,
        *,
        specialist_key: str,
        tool_name: str,
        transcript: list[Message],
        message_content: str,
        **tool_kwargs: Any,
    ) -> Any:
        specialist = self._registered_agents[specialist_key]
        transcript.append(
            self._build_message(
                role='assistant',
                content=message_content,
                metadata={
                    'recipient': specialist.name,
                    'tool_name': tool_name,
                },
            )
        )

        last_error: Exception | None = None
        for attempt in range(1, self.communication_settings.retry_attempts + 2):
            try:
                handler = specialist.handlers[tool_name]
                result = handler(**tool_kwargs)
                transcript.append(
                    self._build_message(
                        role='tool',
                        content=f'{specialist.name}.{tool_name} completed successfully.',
                        metadata={
                            'recipient': specialist.name,
                            'tool_name': tool_name,
                            'attempt': attempt,
                            'timeout_seconds': self.communication_settings.timeout_seconds,
                            'result': self._serialize_result(result),
                        },
                    )
                )
                return result
            except Exception as exc:  # pragma: no cover - exercised by optional runtime integrations
                last_error = exc
                if attempt > self.communication_settings.retry_attempts:
                    raise
        if last_error is not None:  # pragma: no cover - defensive branch
            raise last_error
        raise RuntimeError(f'Failed to invoke {specialist.name}.{tool_name}.')

    def _build_notes(self, transcript: list[Message]) -> list[str]:
        notes = [
            'Framework mode executed specialist-to-specialist tool calls through the orchestration wrapper.',
            f'Configured agent timeout: {self.communication_settings.timeout_seconds} second(s).',
            f'Configured agent retries: {self.communication_settings.retry_attempts}.',
        ]
        notes.extend(
            f"{message.metadata['recipient']} handled {message.metadata['tool_name']} on attempt {message.metadata['attempt']}."
            for message in transcript
            if getattr(message, 'role', None) == 'tool'
            and isinstance(getattr(message, 'metadata', None), Mapping)
            and all(
                key in message.metadata
                for key in ('recipient', 'tool_name', 'attempt')
            )
        )
        return notes

    def _build_tool(self, binding: ToolBinding, handler: Callable[..., Any]) -> Tool:
        if not FRAMEWORK_AVAILABLE:
            return Tool(name=binding.name, description=binding.description, handler=handler)
        for kwargs in (
            {'name': binding.name, 'description': binding.description, 'handler': handler},
            {'name': binding.name, 'description': binding.description, 'function': handler},
            {'name': binding.name, 'description': binding.description, 'func': handler},
        ):
            try:
                return Tool(**kwargs)
            except TypeError:
                continue
        return Tool(binding.name, binding.description, handler)

    def _build_agent(
        self,
        *,
        name: str,
        description: str,
        instructions: str,
        tools: tuple[Tool, ...],
    ) -> Any:
        if not FRAMEWORK_AVAILABLE:
            return Agent(
                name=name,
                description=description,
                instructions=instructions,
                tools=tools,
            )
        for kwargs in (
            {
                'name': name,
                'description': description,
                'instructions': instructions,
                'tools': list(tools),
            },
            {
                'name': name,
                'description': description,
                'system_prompt': instructions,
                'tools': list(tools),
            },
        ):
            try:
                return Agent(**kwargs)
            except TypeError:
                continue
        return Agent(name, description, instructions, list(tools))

    def _build_message(self, *, role: str, content: str, metadata: dict[str, Any]) -> Message:
        if not FRAMEWORK_AVAILABLE:
            return Message(role=role, content=content, metadata=metadata)
        for kwargs in (
            {'role': role, 'content': content, 'metadata': metadata},
            {'role': role, 'text': content, 'metadata': metadata},
        ):
            try:
                return Message(**kwargs)
            except TypeError:
                continue
        return Message(role, content, metadata)

    def _serialize_result(
        self,
        value: AzureSearchServiceSnapshot
        | AnalysisResult
        | CostModelResponse
        | RecommendationReport
        | Mapping[str, Any]
        | Any,
    ) -> Mapping[str, Any] | Any:
        if isinstance(value, Mapping):
            return dict(value)
        model_dump = getattr(value, 'model_dump', None)
        if callable(model_dump):
            return model_dump()
        model_dict = getattr(value, 'dict', None)
        if callable(model_dict):
            return model_dict()
        return value
