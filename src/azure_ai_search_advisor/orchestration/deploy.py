"""Deployment entry point for the Microsoft Foundry hosted orchestrator agent."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from typing import Any

from azure_ai_search_advisor.core.config import Settings
from azure_ai_search_advisor.orchestration.registry import AgentRegistry


def build_hosted_agent_manifest(
    *,
    agent_name: str = 'azure-ai-search-advisor-orchestrator',
    registry: AgentRegistry | None = None,
) -> dict[str, Any]:
    """Build the registration payload for the Foundry-hosted orchestrator agent."""
    resolved_registry = registry or AgentRegistry()
    orchestrator = resolved_registry.get_orchestrator(mode='framework')
    if hasattr(orchestrator, 'local_orchestrator'):
        local_orchestrator = orchestrator.local_orchestrator
    else:
        local_orchestrator = orchestrator

    return {
        'name': agent_name,
        'description': local_orchestrator.config.description,
        'system_prompt': local_orchestrator.config.system_prompt,
        'model': {
            'deployment_name': local_orchestrator.config.model.model,
            'temperature': local_orchestrator.config.model.temperature,
            'max_output_tokens': local_orchestrator.config.model.max_output_tokens,
        },
        'orchestration_mode': resolved_registry.settings.mode,
        'communication': {
            'timeout_seconds': resolved_registry.settings.communication.timeout_seconds,
            'retry_attempts': resolved_registry.settings.communication.retry_attempts,
        },
        'framework_available': bool(
            getattr(orchestrator, 'framework_available', False)
        ),
        'specialists': [
            {
                'name': specialist_name,
                'tools': [
                    {
                        'name': tool.name,
                        'description': tool.description,
                    }
                    for tool in tools
                ],
            }
            for specialist_name, tools in local_orchestrator.specialist_tool_manifest().items()
        ],
    }


def deploy_orchestrator_agent(
    project_endpoint: str,
    *,
    agent_name: str = 'azure-ai-search-advisor-orchestrator',
    registry: AgentRegistry | None = None,
) -> dict[str, Any]:
    """Register the orchestrator as a Microsoft Foundry hosted agent."""
    resolved_registry = registry or AgentRegistry()
    manifest = build_hosted_agent_manifest(agent_name=agent_name, registry=resolved_registry)

    try:
        from azure.identity import DefaultAzureCredential
        from azure.ai.projects import AIProjectClient
        from azure.ai.agents.models import FunctionTool, ToolSet
    except ImportError:  # pragma: no cover - optional runtime dependency
        return {
            'project_endpoint': project_endpoint,
            'manifest': manifest,
            'status': 'sdk_unavailable',
            'instructions': _build_sdk_unavailable_instructions(
                project_endpoint=project_endpoint,
                agent_name=agent_name,
            ),
        }

    credential = DefaultAzureCredential()
    client = AIProjectClient(endpoint=project_endpoint, credential=credential)
    toolset = ToolSet()
    for function_tool in _build_function_tools(resolved_registry.iter_specialist_functions(), FunctionTool):
        toolset.add(function_tool)

    created_agent = client.agents.create_agent(
        model=manifest['model']['deployment_name'],
        name=agent_name,
        description=manifest['description'],
        instructions=manifest['system_prompt'],
        temperature=manifest['model']['temperature'],
        toolset=toolset,
        metadata={
            'orchestration_mode': str(manifest['orchestration_mode']),
            'framework_available': str(manifest['framework_available']).lower(),
            'specialist_count': str(len(manifest['specialists'])),
        },
    )
    return {
        'project_endpoint': project_endpoint,
        'manifest': manifest,
        'status': 'deployed',
        'agent_id': getattr(created_agent, 'id', None),
        'agent_name': getattr(created_agent, 'name', agent_name),
    }


def main() -> int:
    """CLI entry point for staging or registering a Foundry hosted agent."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--project-endpoint',
        default=Settings().azure_ai_foundry_endpoint,
        help='Microsoft Foundry project endpoint.',
    )
    parser.add_argument(
        '--agent-name',
        default='azure-ai-search-advisor-orchestrator',
        help='Hosted Agent name to register in Microsoft Foundry.',
    )
    args = parser.parse_args()

    result = deploy_orchestrator_agent(
        project_endpoint=args.project_endpoint,
        agent_name=args.agent_name,
    )
    print(json.dumps(result, indent=2))
    return 0


def _build_function_tools(
    functions: tuple[Callable[..., Any], ...],
    function_tool_cls: type[Any],
) -> list[Any]:
    grouped_tools: list[Any] = []
    for function in functions:
        grouped_tools.append(function_tool_cls({function}))
    return grouped_tools


def _build_sdk_unavailable_instructions(
    *,
    project_endpoint: str,
    agent_name: str,
) -> list[str]:
    return [
        'Install azure-ai-projects and azure-ai-agents in the deployment environment.',
        f'Re-run deployment with --project-endpoint {project_endpoint} --agent-name {agent_name}.',
        'Use the emitted manifest payload to review the orchestrator model, specialist tools, and communication settings.',
    ]


if __name__ == '__main__':
    raise SystemExit(main())
