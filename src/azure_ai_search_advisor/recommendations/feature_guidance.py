"""Feature guidance recommendation scaffolds."""

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.models.recommendations import Recommendation


def generate_feature_guidance_recommendations(
    analysis_findings: Mapping[str, Any],
    cost_data: Mapping[str, Any],
) -> list[Recommendation]:
    """Generate recommendations for semantic and vector feature usage."""

    features = _as_mapping(analysis_findings.get("features"))
    recommendations: list[Recommendation] = []

    semantic_enabled = bool(features.get("semantic_ranker_enabled"))
    semantic_query_ratio = float(features.get("semantic_query_ratio", 0.0) or 0.0)

    # TODO: Replace these simple gates with per-index query quality and adoption scoring.
    if semantic_enabled and semantic_query_ratio < 0.1:
        recommendations.append(
            Recommendation(
                title="Disable semantic ranker on underused workloads",
                description=(
                    "Semantic ranker is enabled, but only a small share of queries use it. "
                    "You are paying for a premium feature without seeing broad workload benefit."
                ),
                category="feature_guidance",
                priority="medium",
                impact_estimate=(
                    f"Avoid roughly {_format_currency(features.get('estimated_semantic_monthly_cost', 0.0))} in monthly feature spend."
                ),
                effort="low",
                remediation_steps=[
                    "Confirm which indexes and applications actively depend on semantic ranking.",
                    "Disable semantic ranker for indexes or environments where usage is negligible.",
                    "Compare click-through rate and top-result relevance before and after the change.",
                ],
            )
        )
    elif not semantic_enabled and features.get("semantic_quality_gap"):
        recommendations.append(
            Recommendation(
                title="Enable semantic ranker for relevance-sensitive queries",
                description=(
                    "Search quality findings suggest that traditional ranking is not meeting user "
                    "expectations for natural language or long-tail queries."
                ),
                category="feature_guidance",
                priority="medium",
                impact_estimate="Improve top-result relevance and reduce zero-click search sessions.",
                effort="medium",
                remediation_steps=[
                    "Enable semantic ranker on the affected index or environment.",
                    "Tune captions, answers, and query settings in the client application.",
                    "Measure relevance metrics and business conversion before broad rollout.",
                ],
            )
        )

    # TODO: Expand this into vector profile, embedding, and HNSW parameter-specific guidance.
    if features.get("vector_search_enabled") and features.get("vector_optimization_opportunity"):
        recommendations.append(
            Recommendation(
                title="Optimize vector search configuration",
                description=(
                    "Vector search is enabled, but current index settings suggest unnecessary "
                    "storage or compute overhead for the observed recall and latency targets."
                ),
                category="feature_guidance",
                priority="high",
                impact_estimate=(
                    f"Reduce vector-related spend by about {_format_currency(features.get('estimated_vector_monthly_savings', 0.0))} per month."
                ),
                effort="medium",
                remediation_steps=[
                    "Review embedding dimensionality, vector field count, and retention strategy.",
                    "Tune HNSW or vector profile settings to match the required recall and latency targets.",
                    "Rebuild the index in a lower environment and validate recall, latency, and storage savings.",
                ],
            )
        )

    return recommendations


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _format_currency(value: Any) -> str:
    amount = float(value or 0.0)
    return f"${amount:,.0f}"
