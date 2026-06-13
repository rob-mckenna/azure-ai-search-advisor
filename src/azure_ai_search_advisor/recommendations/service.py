"""Recommendation service scaffold."""

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.models.recommendations import Recommendation, RecommendationReport
from azure_ai_search_advisor.recommendations.alerting import (
    generate_alerting_recommendations,
)
from azure_ai_search_advisor.recommendations.feature_guidance import (
    generate_feature_guidance_recommendations,
)
from azure_ai_search_advisor.recommendations.pricing_advisor import (
    generate_pricing_model_recommendations,
)
from azure_ai_search_advisor.recommendations.rightsizing import (
    generate_rightsizing_recommendations,
)


class RecommendationService:
    """Generates actionable Azure AI Search guidance."""

    def recommend(
        self,
        analysis_findings: Mapping[str, Any],
        cost_data: Mapping[str, Any],
    ) -> RecommendationReport:
        """Generate a ranked recommendation report for the analyzed workload."""

        recommendations: list[Recommendation] = []
        recommendations.extend(generate_rightsizing_recommendations(analysis_findings, cost_data))
        recommendations.extend(
            generate_feature_guidance_recommendations(analysis_findings, cost_data)
        )
        recommendations.extend(
            generate_pricing_model_recommendations(analysis_findings, cost_data)
        )
        recommendations.extend(generate_alerting_recommendations(analysis_findings, cost_data))

        recommendations.sort(key=self._priority_sort_key)

        return RecommendationReport(
            summary=self._build_summary(recommendations),
            recommendations=recommendations,
            estimated_savings=self._build_estimated_savings(cost_data),
        )

    def _build_summary(self, recommendations: list[Recommendation]) -> str:
        """Create a concise summary for downstream APIs and sample output."""

        if not recommendations:
            return "No optimization opportunities identified for this workload."

        high_priority = sum(1 for item in recommendations if item.priority == "high")
        quick_wins = sum(1 for item in recommendations if item.effort == "low")
        return (
            f"Generated {len(recommendations)} recommendations, including {high_priority} "
            f"high-priority actions and {quick_wins} quick wins."
        )

    def _build_estimated_savings(self, cost_data: Mapping[str, Any]) -> dict[str, float | str]:
        """Build a high-level savings summary from cost scenarios."""

        scenario_comparison = _as_mapping(cost_data.get("scenario_comparison"))
        monthly_savings = float(
            scenario_comparison.get(
                "recommended_monthly_savings",
                cost_data.get("potential_monthly_savings", 0.0),
            )
            or 0.0
        )
        annual_savings = float(
            scenario_comparison.get("recommended_annual_savings", monthly_savings * 12) or 0.0
        )

        return {
            "monthly_usd": round(monthly_savings, 2),
            "annual_usd": round(annual_savings, 2),
            "confidence": str(scenario_comparison.get("confidence", "todo")),
        }

    def _priority_sort_key(self, recommendation: Recommendation) -> tuple[int, int, str]:
        """Sort higher-priority, lower-effort items first."""

        priority_rank = {"high": 0, "medium": 1, "low": 2}
        effort_rank = {"low": 0, "medium": 1, "high": 2}
        return (
            priority_rank.get(recommendation.priority, 99),
            effort_rank.get(recommendation.effort, 99),
            recommendation.title,
        )


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
