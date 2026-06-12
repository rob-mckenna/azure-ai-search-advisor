"""Deployment entry point for the Microsoft Foundry hosted orchestrator agent."""

from __future__ import annotations

import argparse
import json
from typing import Any

from azure_ai_search_advisor.orchestration.registry import AgentRegistry



def build_hosted_agent_manifest(
    *,
    agent_name: str = 'azure-ai-search-advisor-orchestrator',
    registry: AgentRegistry | None = None,
) -> dict[str, Any]:
    """Build the registration payload for the Foundry-hosted orchestrator agent."""
    orchestrator = (registry or AgentRegistry()).build()
    return {
        'name': agent_name,
        'description': orchestrator.config.description,
        'system_prompt': orchestrator.config.system_prompt,
        'model': {
            'deployment_name': orchestrator.config.model.model,
            'temperature': orchestrator.config.model.temperature,
            'max_output_tokens': orchestrator.config.model.max_output_tokens,
        },
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
            for specialist_name, tools in orchestrator.specialist_tool_manifest().items()
        ],
    }



def deploy_orchestrator_agent(
    project_endpoint: str,
    *,
    agent_name: str = 'azure-ai-search-advisor-orchestrator',
    registry: AgentRegistry | None = None,
) -> dict[str, Any]:
    """Register the orchestrator as a Microsoft Foundry hosted agent."""
    from azure.identity import DefaultAzureCredential

    try:
        from azure.ai.projects import AIProjectClient
    except ImportError as exc:  # pragma: no cover - optional runtime dependency
        raise RuntimeError(
            'azure-ai-projects must be installed in the deployment environment.'
        ) from exc

    credential = DefaultAzureCredential()
    client = AIProjectClient(endpoint=project_endpoint, credential=credential)
    manifest = build_hosted_agent_manifest(agent_name=agent_name, registry=registry)

    # TODO: Replace this placeholder with the concrete hosted-agent registration API once
    # azure-ai-projects exposes the final Microsoft Foundry agent creation surface.
    _ = client
    return {
        'project_endpoint': project_endpoint,
        'manifest': manifest,
        'status': 'pending_sdk_support',
        'notes': [
            'TODO: Call the azure-ai-projects hosted agent registration API here.',
            'The orchestrator manifest already contains the system prompt, model settings, and specialist tool catalog.',
        ],
    }



def main() -> int:
    """CLI entry point for staging a Foundry hosted-agent deployment payload."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-endpoint', required=True, help='Microsoft Foundry project endpoint.')
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


if __name__ == '__main__':
    raise SystemExit(main())
