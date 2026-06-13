"""Feature utilization analyzer."""

from __future__ import annotations

from pydantic import Field

from azure_ai_search_advisor.models import (
    AdvisorModel,
    AnalysisFinding,
    AzureSearchServiceConfiguration,
    AzureSearchServiceMetrics,
)


class FeatureAnalysisInput(AdvisorModel):
    """Inputs required to assess feature usage efficiency."""

    configuration: AzureSearchServiceConfiguration = Field(
        description="Azure AI Search service configuration to evaluate.",
    )
    metrics: AzureSearchServiceMetrics = Field(
        description="Observed Azure AI Search workload metrics.",
    )


class FeatureAnalysisResult(AdvisorModel):
    """Feature utilization findings."""

    findings: list[AnalysisFinding] = Field(
        default_factory=list,
        description="Feature-level inefficiencies identified for the workload.",
    )


class FeatureAnalyzer:
    """Finds misused, unused, or misconfigured Azure AI Search features."""

    _SEMANTIC_USAGE_THRESHOLD_PCT = 10.0
    _VECTOR_USAGE_THRESHOLD_PCT = 5.0

    def analyze(self, analysis_input: FeatureAnalysisInput) -> FeatureAnalysisResult:
        """Inspect semantic, vector, and other feature usage against workload telemetry."""
        findings: list[AnalysisFinding] = []
        configuration = analysis_input.configuration
        metrics = analysis_input.metrics
        feature_usage = metrics.feature_usage
        monthly_queries = metrics.query_volume.monthly_queries

        if (
            configuration.semantic_ranker.enabled
            and feature_usage.semantic_query_percentage < self._SEMANTIC_USAGE_THRESHOLD_PCT
        ):
            semantic_queries = monthly_queries * (feature_usage.semantic_query_percentage / 100.0)
            findings.append(
                AnalysisFinding(
                    severity="medium",
                    category="feature_usage",
                    title="Semantic ranker is enabled but lightly adopted",
                    description=(
                        f"Semantic ranker is enabled, but only {feature_usage.semantic_query_percentage:.1f}% "
                        f"of the observed {monthly_queries:,} monthly queries use it. This is below the "
                        f"{self._SEMANTIC_USAGE_THRESHOLD_PCT:.0f}% adoption threshold and suggests the "
                        "feature is not broadly used by the workload."
                    ),
                    evidence={
                        "semantic_ranker_enabled": configuration.semantic_ranker.enabled,
                        "semantic_query_percentage": round(
                            feature_usage.semantic_query_percentage,
                            2,
                        ),
                        "monthly_queries": monthly_queries,
                        "estimated_semantic_queries_per_month": round(semantic_queries, 2),
                        "threshold_semantic_query_percentage": self._SEMANTIC_USAGE_THRESHOLD_PCT,
                    },
                    impact=(
                        "Unused semantic capacity can drive premium query charges without materially "
                        "improving relevance for most searches."
                    ),
                )
            )

        if (
            configuration.vector_search.enabled
            and feature_usage.vector_query_percentage < self._VECTOR_USAGE_THRESHOLD_PCT
        ):
            findings.append(
                AnalysisFinding(
                    severity="medium",
                    category="feature_usage",
                    title="Vector search is enabled but rarely queried",
                    description=(
                        f"Vector search is configured, but only {feature_usage.vector_query_percentage:.1f}% "
                        f"of observed queries use vector retrieval. This is below the "
                        f"{self._VECTOR_USAGE_THRESHOLD_PCT:.0f}% vector usage threshold, which suggests the "
                        "service may be carrying vector index and compute overhead for a small slice of traffic."
                    ),
                    evidence={
                        "vector_search_enabled": configuration.vector_search.enabled,
                        "vector_query_percentage": round(feature_usage.vector_query_percentage, 2),
                        "monthly_queries": monthly_queries,
                        "vector_index_count": configuration.vector_search.vector_index_count,
                        "integrated_vectorization_calls_per_day": (
                            feature_usage.integrated_vectorization_calls_per_day
                        ),
                        "threshold_vector_query_percentage": self._VECTOR_USAGE_THRESHOLD_PCT,
                    },
                    impact=(
                        "Vector-enabled indexes can consume storage and operational effort that may not be "
                        "justified by current query adoption."
                    ),
                )
            )

        if (
            configuration.ai_enrichment.enabled
            and feature_usage.ai_enrichment_runs_per_day == 0
        ):
            findings.append(
                AnalysisFinding(
                    severity="high",
                    category="feature_usage",
                    title="AI enrichment is enabled but inactive",
                    description=(
                        f"AI enrichment is enabled with {configuration.ai_enrichment.skillset_count} "
                        "configured skillset(s), but no enrichment runs were observed during the "
                        f"{metrics.observation_window_days}-day window."
                    ),
                    evidence={
                        "ai_enrichment_enabled": configuration.ai_enrichment.enabled,
                        "skillset_count": configuration.ai_enrichment.skillset_count,
                        "ai_enrichment_runs_per_day": feature_usage.ai_enrichment_runs_per_day,
                        "indexer_runs_per_day": round(feature_usage.indexer_runs_per_day, 2),
                        "skill_invocations_per_day": feature_usage.skill_invocations_per_day,
                    },
                    impact=(
                        "Inactive enrichment pipelines can add configuration and downstream Azure AI "
                        "service complexity without delivering indexing value."
                    ),
                )
            )

        return FeatureAnalysisResult(findings=findings)
