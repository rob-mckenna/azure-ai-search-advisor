"""SKU selection analyzer."""

from __future__ import annotations

from pydantic import Field

from azure_ai_search_advisor.models import (
    AdvisorModel,
    AnalysisFinding,
    AzureSearchServiceConfiguration,
    AzureSearchServiceMetrics,
)
from azure_ai_search_advisor.models.configuration import DeploymentMode, SearchSku


class SkuAnalysisInput(AdvisorModel):
    """Inputs required to evaluate SKU suitability."""

    configuration: AzureSearchServiceConfiguration = Field(
        description="Azure AI Search service configuration to evaluate.",
    )
    metrics: AzureSearchServiceMetrics = Field(
        description="Observed Azure AI Search workload metrics.",
    )


class SkuAnalysisResult(AdvisorModel):
    """SKU-specific findings."""

    findings: list[AnalysisFinding] = Field(
        default_factory=list,
        description="SKU mismatch issues identified for the workload.",
    )


class SkuAnalyzer:
    """Identifies likely SKU over-sizing or under-sizing."""

    _SKU_TOTAL_STORAGE_LIMITS_GB: dict[SearchSku, float] = {
        SearchSku.FREE: 0.05,
        SearchSku.BASIC: 2.0,
        SearchSku.S1: 25.0 * 12,
        SearchSku.S2: 100.0 * 12,
        SearchSku.S3: 200.0 * 12,
        SearchSku.S3_HD: 200.0 * 12,
    }
    _S1_FIT_MONTHLY_QUERY_THRESHOLD = 1_000_000
    _BASIC_HIGH_QUERY_THRESHOLD = 1_000_000
    _SERVERLESS_MONTHLY_QUERY_THRESHOLD = 100_000
    _SERVERLESS_CPU_THRESHOLD_PCT = 15.0

    def analyze(self, analysis_input: SkuAnalysisInput) -> SkuAnalysisResult:
        """Compare SKU choice to workload scale and feature requirements."""
        findings: list[AnalysisFinding] = []
        configuration = analysis_input.configuration
        metrics = analysis_input.metrics
        monthly_queries = metrics.query_volume.monthly_queries
        total_index_size_gb = metrics.total_index_size_gb
        avg_qps = metrics.query_volume.avg_queries_per_second

        if (
            configuration.deployment_mode == DeploymentMode.DEDICATED
            and configuration.sku in {SearchSku.S3, SearchSku.S3_HD}
            and total_index_size_gb <= self._SKU_TOTAL_STORAGE_LIMITS_GB[SearchSku.S1]
            and monthly_queries <= self._S1_FIT_MONTHLY_QUERY_THRESHOLD
        ):
            findings.append(
                AnalysisFinding(
                    severity="medium",
                    category="sku",
                    title="Current S3 workload appears to fit within S1 limits",
                    description=(
                        f"The service is running on {configuration.sku.value}, but the observed "
                        f"{total_index_size_gb:.2f} GB index footprint and {monthly_queries:,} monthly "
                        "queries both fall within this analyzer's S1 fit thresholds."
                    ),
                    evidence={
                        "current_sku": configuration.sku.value,
                        "target_sku": SearchSku.S1.value,
                        "total_index_size_gb": round(total_index_size_gb, 2),
                        "s1_storage_limit_gb": self._SKU_TOTAL_STORAGE_LIMITS_GB[SearchSku.S1],
                        "monthly_queries": monthly_queries,
                        "s1_fit_monthly_query_threshold": self._S1_FIT_MONTHLY_QUERY_THRESHOLD,
                        "avg_queries_per_second": round(avg_qps, 2),
                    },
                    impact=(
                        "Downgrading from S3 to S1 could materially reduce dedicated search spend if "
                        "latency, feature, and growth requirements also remain within S1 limits."
                    ),
                )
            )

        basic_storage_limit_gb = self._SKU_TOTAL_STORAGE_LIMITS_GB[SearchSku.BASIC]
        is_basic = configuration.sku == SearchSku.BASIC
        storage_pressure = total_index_size_gb > basic_storage_limit_gb
        query_pressure = monthly_queries >= self._BASIC_HIGH_QUERY_THRESHOLD
        if configuration.deployment_mode == DeploymentMode.DEDICATED and is_basic and (
            storage_pressure or query_pressure
        ):
            reasons: list[str] = []
            if storage_pressure:
                reasons.append(
                    f"index storage is {total_index_size_gb:.2f} GB versus the {basic_storage_limit_gb:.2f} GB Basic limit"
                )
            if query_pressure:
                reasons.append(
                    f"monthly query volume is {monthly_queries:,}, above the {self._BASIC_HIGH_QUERY_THRESHOLD:,} high-volume threshold"
                )
            findings.append(
                AnalysisFinding(
                    severity="high",
                    category="sku",
                    title="Basic SKU may be undersized for the observed workload",
                    description=(
                        "The workload shows signs that Basic may be too small for the current demand: "
                        + "; ".join(reasons)
                        + "."
                    ),
                    evidence={
                        "current_sku": configuration.sku.value,
                        "total_index_size_gb": round(total_index_size_gb, 2),
                        "basic_storage_limit_gb": basic_storage_limit_gb,
                        "monthly_queries": monthly_queries,
                        "high_query_threshold": self._BASIC_HIGH_QUERY_THRESHOLD,
                        "avg_queries_per_second": round(avg_qps, 2),
                        "storage_quota_utilization_pct": round(
                            metrics.storage_quota_utilization_pct,
                            2,
                        ),
                    },
                    impact=(
                        "An undersized Basic service can run into storage ceilings or struggle to absorb "
                        "query growth, creating operational risk and forcing reactive scale changes."
                    ),
                )
            )

        if (
            configuration.deployment_mode == DeploymentMode.DEDICATED
            and monthly_queries < self._SERVERLESS_MONTHLY_QUERY_THRESHOLD
            and metrics.avg_cpu_utilization_pct < self._SERVERLESS_CPU_THRESHOLD_PCT
        ):
            findings.append(
                AnalysisFinding(
                    severity="medium",
                    category="sku",
                    title="Dedicated service may be a serverless candidate",
                    description=(
                        f"The service processed only {monthly_queries:,} monthly queries with average CPU "
                        f"utilization of {metrics.avg_cpu_utilization_pct:.1f}%, which is consistent with a "
                        "low-duty-cycle workload that may be cheaper on serverless pricing."
                    ),
                    evidence={
                        "deployment_mode": configuration.deployment_mode.value,
                        "current_sku": configuration.sku.value,
                        "monthly_queries": monthly_queries,
                        "serverless_monthly_query_threshold": self._SERVERLESS_MONTHLY_QUERY_THRESHOLD,
                        "avg_cpu_utilization_pct": round(metrics.avg_cpu_utilization_pct, 2),
                        "serverless_cpu_threshold_pct": self._SERVERLESS_CPU_THRESHOLD_PCT,
                    },
                    impact=(
                        "Moving a lightly used dedicated service to serverless could better align cost "
                        "with sporadic demand."
                    ),
                )
            )

        return SkuAnalysisResult(findings=findings)
