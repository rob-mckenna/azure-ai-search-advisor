"""Top-level orchestrator agent definition for Microsoft Foundry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import Field

from azure_ai_search_advisor.analysis import AnalysisResult
from azure_ai_search_advisor.models import AdvisorModel, AzureSearchServiceSnapshot, CostModelResponse
from azure_ai_search_advisor.models import RecommendationReport
from azure_ai_search_advisor.orchestration.agents.analysis_agent import AnalysisAgent
from azure_ai_search_advisor.orchestration.agents.cost_agent import CostAgent
from azure_ai_search_advisor.orchestration.agents.ingestion_agent import IngestionAgent
from azure_ai_search_advisor.orchestration.agents.recommendation_agent import RecommendationAgent
from azure_ai_search_advisor.orchestration.config import AgentConfig, ToolBinding


class OrchestratorPlan(AdvisorModel):
    """Resolved execution plan for a user request."""

    user_query: str
    steps: list[str] = Field(default_factory=list)
    include_cost_modeling: bool = True
    include_recommendations: bool = True


class OrchestratorResponse(AdvisorModel):
    """Aggregated output assembled by the orchestrator."""

    user_query: str
    plan: OrchestratorPlan
    summary: str
    snapshot: AzureSearchServiceSnapshot | None = None
    analysis: AnalysisResult | None = None
    cost: CostModelResponse | None = None
    recommendations: RecommendationReport | None = None
    notes: list[str] = Field(default_factory=list)


class OrchestratorAgent:
    """Coordinates specialist agents for Azure AI Search advisor workflows."""

    def __init__(
        self,
        *,
        config: AgentConfig,
        ingestion_agent: IngestionAgent,
        analysis_agent: AnalysisAgent,
        cost_agent: CostAgent,
        recommendation_agent: RecommendationAgent,
    ) -> None:
        self.config = config
        self.ingestion_agent = ingestion_agent
        self.analysis_agent = analysis_agent
        self.cost_agent = cost_agent
        self.recommendation_agent = recommendation_agent

    def decompose_query(
        self,
        user_query: str,
        *,
        include_cost_analysis: bool = True,
        include_recommendations: bool = True,
    ) -> OrchestratorPlan:
        """Translate a user query into specialist-agent work items."""
        normalized_query = user_query.lower()
        requires_cost = include_cost_analysis or any(
            token in normalized_query for token in ('cost', 'price', 'pricing', 'serverless', 'spend')
        )
        requires_recommendations = include_recommendations or any(
            token in normalized_query
            for token in ('recommend', 'guidance', 'optimize', 'improve', 'right-size')
        )

        steps = [
            'Validate workload input with the ingestion agent.',
            'Run workload inefficiency detection with the analysis agent.',
        ]
        if requires_cost:
            steps.append('Model dedicated and serverless pricing scenarios with the cost agent.')
        if requires_recommendations:
            steps.append('Generate prioritized guidance with the recommendation agent.')
        steps.append('Assemble the specialist outputs into the final orchestrator response.')

        return OrchestratorPlan(
            user_query=user_query,
            steps=steps,
            include_cost_modeling=requires_cost,
            include_recommendations=requires_recommendations,
        )

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
        """Run the local service-backed orchestration flow for a user request."""
        plan = self.decompose_query(
            user_query,
            include_cost_analysis=include_cost_analysis,
            include_recommendations=include_recommendations,
        )

        resolved_snapshot = self._resolve_snapshot(
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
                    'In Microsoft Foundry, the hosted orchestrator should gather missing context through agent prompts and tool calls.',
                ],
            )

        analysis_result = self.analysis_agent.run_full_analysis(snapshot=resolved_snapshot)
        cost_result = (
            self.cost_agent.estimate_cost(snapshot=resolved_snapshot)
            if plan.include_cost_modeling
            else None
        )
        recommendation_result = (
            self.recommendation_agent.generate_recommendations(
                analysis_result,
                cost_result or {'scenario_comparison': {}, 'potential_monthly_savings': 0.0},
            )
            if plan.include_recommendations
            else None
        )

        return OrchestratorResponse(
            user_query=user_query,
            plan=plan,
            summary=self._build_summary(
                analysis=analysis_result,
                cost=cost_result,
                recommendations=recommendation_result,
            ),
            snapshot=resolved_snapshot,
            analysis=analysis_result,
            cost=cost_result,
            recommendations=recommendation_result,
            notes=[
                'Local execution uses deterministic service chaining so the API layer and agent layer share the same business services.',
                'Will migrate to Microsoft Agent Framework orchestration primitives when the SDK surface is finalized.',
            ],
        )

    def specialist_tool_manifest(self) -> dict[str, tuple[ToolBinding, ...]]:
        """Expose tool bindings for specialist-agent registration."""
        return {
            self.ingestion_agent.config.name: self.ingestion_agent.config.tools,
            self.analysis_agent.config.name: self.analysis_agent.config.tools,
            self.cost_agent.config.name: self.cost_agent.config.tools,
            self.recommendation_agent.config.name: self.recommendation_agent.config.tools,
        }

    def _resolve_snapshot(
        self,
        *,
        payload: Mapping[str, Any] | None,
        snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None,
        snapshot_path: str | None,
    ) -> AzureSearchServiceSnapshot | None:
        if snapshot is not None:
            return self.ingestion_agent.validate_snapshot(snapshot)
        if payload is not None:
            return self.ingestion_agent.ingest_config(payload)
        if snapshot_path is not None:
            return self.ingestion_agent.ingest_config_file(snapshot_path)
        return None

    def _build_summary(
        self,
        *,
        analysis: AnalysisResult,
        cost: CostModelResponse | None,
        recommendations: RecommendationReport | None,
    ) -> str:
        finding_count = len(analysis.findings)
        recommendation_count = len(recommendations.recommendations) if recommendations else 0
        summary_parts = [f'Completed analysis with {finding_count} finding(s).']
        if cost is not None:
            summary_parts.append(
                'Compared dedicated and serverless cost models '
                f"(delta: {cost.comparison.monthly_difference_usd} USD/month)."
            )
        if recommendations is not None:
            summary_parts.append(f'Generated {recommendation_count} recommendation(s).')
        return ' '.join(summary_parts)
