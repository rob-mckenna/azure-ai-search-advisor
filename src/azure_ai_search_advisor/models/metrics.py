"""Pydantic models for Azure AI Search usage metrics."""

from __future__ import annotations

from pydantic import Field, root_validator

from azure_ai_search_advisor.models.base import AdvisorModel


class QueryVolumeMetrics(AdvisorModel):
    """Observed query traffic over a measurement window."""

    avg_queries_per_day: int = Field(ge=0)
    peak_queries_per_day: int = Field(ge=0)
    avg_queries_per_second: float = Field(ge=0)
    monthly_queries: int = Field(ge=0)

    @root_validator(skip_on_failure=True)
    def validate_volume(cls, values: dict) -> dict:
        """Enforce basic traffic sanity checks."""
        if values.get("peak_queries_per_day", 0) < values.get("avg_queries_per_day", 0):
            raise ValueError("peak_queries_per_day must be greater than or equal to avg_queries_per_day.")
        return values


class FeatureUsageStats(AdvisorModel):
    """Feature adoption and usage signals."""

    semantic_query_percentage: float = Field(default=0, ge=0, le=100)
    vector_query_percentage: float = Field(default=0, ge=0, le=100)
    ai_enrichment_runs_per_day: int = Field(default=0, ge=0)
    indexer_runs_per_day: float = Field(default=0, ge=0)
    skill_invocations_per_day: int = Field(default=0, ge=0)
    integrated_vectorization_calls_per_day: int = Field(default=0, ge=0)


class LatencyMetrics(AdvisorModel):
    """Service latency percentiles in milliseconds."""

    p50_ms: float = Field(ge=0)
    p95_ms: float = Field(ge=0)
    p99_ms: float = Field(ge=0)

    @root_validator(skip_on_failure=True)
    def validate_percentiles(cls, values: dict) -> dict:
        """Ensure latency percentiles are ordered."""
        if not values.get("p50_ms", 0) <= values.get("p95_ms", 0) <= values.get("p99_ms", 0):
            raise ValueError("Latency percentiles must be ordered p50 <= p95 <= p99.")
        return values


class AzureSearchServiceMetrics(AdvisorModel):
    """Observed Azure AI Search service metrics."""

    observation_window_days: int = Field(default=30, gt=0, le=365)
    query_volume: QueryVolumeMetrics
    total_index_size_gb: float = Field(ge=0)
    document_count: int = Field(ge=0)
    feature_usage: FeatureUsageStats
    latency: LatencyMetrics
    avg_cpu_utilization_pct: float = Field(ge=0, le=100)
    storage_quota_utilization_pct: float = Field(ge=0, le=100)
    throttled_queries_per_day: int = Field(default=0, ge=0)
    indexing_operations_per_day: int = Field(default=0, ge=0)
