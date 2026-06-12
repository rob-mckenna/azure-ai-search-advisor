"""Analysis service scaffold."""

from __future__ import annotations

from pydantic import Field

from azure_ai_search_advisor.analysis.feature_analyzer import (
    FeatureAnalysisInput,
    FeatureAnalysisResult,
    FeatureAnalyzer,
)
from azure_ai_search_advisor.analysis.provisioning_analyzer import (
    ProvisioningAnalysisInput,
    ProvisioningAnalysisResult,
    ProvisioningAnalyzer,
)
from azure_ai_search_advisor.analysis.sku_analyzer import (
    SkuAnalysisInput,
    SkuAnalysisResult,
    SkuAnalyzer,
)
from azure_ai_search_advisor.cost_modeling.pricing_data import (
    APPROX_SEMANTIC_RANKER_PRICE_PER_1K_QUERIES_USD,
    APPROX_VECTOR_STORAGE_PRICE_PER_GB_MONTH_USD,
    get_pricing_reference,
)
from azure_ai_search_advisor.models import (
    AdvisorModel,
    AnalysisFinding,
    AzureSearchServiceConfiguration,
    AzureSearchServiceMetrics,
)
from azure_ai_search_advisor.models.configuration import DeploymentMode, SearchFeature, SearchSku
from azure_ai_search_advisor.models.cost_models import PricingTier

SKU_TO_PRICING_TIER: dict[SearchSku, PricingTier] = {
    SearchSku.FREE: PricingTier.FREE,
    SearchSku.BASIC: PricingTier.BASIC,
    SearchSku.S1: PricingTier.S1,
    SearchSku.S2: PricingTier.S2,
    SearchSku.S3: PricingTier.S3,
    SearchSku.S3_HD: PricingTier.S3,
    SearchSku.L1: PricingTier.L1,
    SearchSku.L2: PricingTier.L2,
}


class AnalysisRequest(AdvisorModel):
    """Top-level input contract for workload analysis."""

    configuration: AzureSearchServiceConfiguration | None = Field(
        default=None,
        description="Azure AI Search configuration to analyze.",
    )
    metrics: AzureSearchServiceMetrics | None = Field(
        default=None,
        description="Observed workload metrics paired to the configuration.",
    )


class AnalysisResult(AdvisorModel):
    """Aggregated analysis output across all analyzers."""

    findings: list[AnalysisFinding] = Field(
        default_factory=list,
        description="Flattened findings produced by all analyzers.",
    )
    provisioning: ProvisioningAnalysisResult = Field(
        default_factory=ProvisioningAnalysisResult,
        description="Provisioning-specific analysis output.",
    )
    sku: SkuAnalysisResult = Field(
        default_factory=SkuAnalysisResult,
        description="SKU suitability analysis output.",
    )
    features: FeatureAnalysisResult = Field(
        default_factory=FeatureAnalysisResult,
        description="Feature usage analysis output.",
    )


class AnalysisService:
    """Coordinates inefficiency detection for Azure AI Search workloads."""

    def __init__(
        self,
        provisioning_analyzer: ProvisioningAnalyzer | None = None,
        sku_analyzer: SkuAnalyzer | None = None,
        feature_analyzer: FeatureAnalyzer | None = None,
    ) -> None:
        self._provisioning_analyzer = provisioning_analyzer or ProvisioningAnalyzer()
        self._sku_analyzer = sku_analyzer or SkuAnalyzer()
        self._feature_analyzer = feature_analyzer or FeatureAnalyzer()

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """Run all analyzers and aggregate their findings."""
        provisioning_result = self._provisioning_analyzer.analyze(
            ProvisioningAnalysisInput(
                configuration=request.configuration,
                metrics=request.metrics,
            )
        )
        sku_result = self._sku_analyzer.analyze(
            SkuAnalysisInput(
                configuration=request.configuration,
                metrics=request.metrics,
            )
        )
        feature_result = self._feature_analyzer.analyze(
            FeatureAnalysisInput(
                configuration=request.configuration,
                metrics=request.metrics,
            )
        )

        findings = [
            *provisioning_result.findings,
            *sku_result.findings,
            *feature_result.findings,
        ]
        findings.extend(self._generate_heuristic_findings(request))

        return AnalysisResult(
            findings=findings,
            provisioning=ProvisioningAnalysisResult(
                findings=[item for item in findings if item.category == "provisioning"]
            ),
            sku=SkuAnalysisResult(findings=[item for item in findings if item.category == "sku"]),
            features=FeatureAnalysisResult(
                findings=[item for item in findings if item.category == "feature_usage"]
            ),
        )

    def _generate_heuristic_findings(self, request: AnalysisRequest) -> list[AnalysisFinding]:
        configuration = request.configuration
        metrics = request.metrics
        if configuration is None or metrics is None:
            return []

        findings: list[AnalysisFinding] = []
        findings.extend(self._analyze_provisioning(configuration, metrics))
        findings.extend(self._analyze_sku_fit(configuration, metrics))
        findings.extend(self._analyze_feature_usage(configuration, metrics))
        return findings

    def _analyze_provisioning(
        self,
        configuration: AzureSearchServiceConfiguration,
        metrics: AzureSearchServiceMetrics,
    ) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        if configuration.deployment_mode != DeploymentMode.DEDICATED:
            return findings

        pricing_reference = get_pricing_reference(SKU_TO_PRICING_TIER[configuration.sku])
        replica_cost = pricing_reference.monthly_cost_per_search_unit_usd * max(
            configuration.partitions or 1,
            1,
        )
        partition_cost = pricing_reference.monthly_cost_per_search_unit_usd * max(
            configuration.replicas or 1,
            1,
        )

        if (configuration.replicas or 0) > 1 and metrics.avg_cpu_utilization_pct < 50:
            findings.append(
                AnalysisFinding(
                    severity="high" if metrics.avg_cpu_utilization_pct < 30 else "medium",
                    category="provisioning",
                    title="Review dedicated replica count",
                    description="Replica capacity appears oversized for the observed query demand and CPU load.",
                    evidence={
                        "metric": "avg_cpu_utilization_pct",
                        "observed_value": round(metrics.avg_cpu_utilization_pct, 1),
                        "expected_range": "35-70% for steady dedicated production workloads",
                        "recommendation_hint": "Reduce replicas by one and validate p95 latency before rollout.",
                        "potential_monthly_cost_impact_usd": round(replica_cost, 2),
                    },
                    impact="Unused replicas increase ongoing dedicated capacity spend.",
                )
            )

        if (configuration.partitions or 0) > 1 and metrics.storage_quota_utilization_pct < 50:
            findings.append(
                AnalysisFinding(
                    severity="medium",
                    category="provisioning",
                    title="Review dedicated partition count",
                    description="Partition capacity materially exceeds the current storage footprint.",
                    evidence={
                        "metric": "storage_quota_utilization_pct",
                        "observed_value": round(metrics.storage_quota_utilization_pct, 1),
                        "expected_range": "50-80% before adding partitions",
                        "recommendation_hint": "Consider reducing partitions if growth and indexing throughput allow it.",
                        "potential_monthly_cost_impact_usd": round(partition_cost, 2),
                    },
                    impact="Excess partitions increase search unit cost without improving current workload fit.",
                )
            )

        return findings

    def _analyze_sku_fit(
        self,
        configuration: AzureSearchServiceConfiguration,
        metrics: AzureSearchServiceMetrics,
    ) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        monthly_queries = metrics.query_volume.monthly_queries
        premium_features_enabled = any(
            feature in configuration.features_enabled
            for feature in (
                SearchFeature.SEMANTIC_RANKER,
                SearchFeature.VECTOR_SEARCH,
                SearchFeature.AI_ENRICHMENT,
            )
        )

        if (
            configuration.deployment_mode == DeploymentMode.DEDICATED
            and monthly_queries < 100_000
            and metrics.avg_cpu_utilization_pct < 15
            and not premium_features_enabled
        ):
            findings.append(
                AnalysisFinding(
                    severity="medium",
                    category="sku",
                    title="Evaluate serverless pricing for low-volume environments",
                    description="Dedicated capacity may be unnecessary for this small, bursty workload.",
                    evidence={
                        "metric": "monthly_queries",
                        "observed_value": monthly_queries,
                        "expected_range": "Dedicated pricing is usually better justified by sustained traffic",
                        "recommendation_hint": "Compare dedicated spend with a serverless scenario for this workload.",
                    },
                    impact="A dedicated SKU can cost more than a usage-based model for intermittent traffic.",
                )
            )

        return findings

    def _analyze_feature_usage(
        self,
        configuration: AzureSearchServiceConfiguration,
        metrics: AzureSearchServiceMetrics,
    ) -> list[AnalysisFinding]:
        findings: list[AnalysisFinding] = []
        monthly_queries = metrics.query_volume.monthly_queries

        if configuration.semantic_ranker.enabled and metrics.feature_usage.semantic_query_percentage < 10:
            semantic_queries = int(
                monthly_queries * (metrics.feature_usage.semantic_query_percentage / 100.0)
            )
            findings.append(
                AnalysisFinding(
                    severity="medium",
                    category="feature_usage",
                    title="Review semantic ranker usage",
                    description="Semantic ranker is enabled but used by a very small portion of queries.",
                    evidence={
                        "metric": "semantic_query_percentage",
                        "observed_value": round(metrics.feature_usage.semantic_query_percentage, 1),
                        "expected_range": ">=10% semantic usage to justify broad enablement",
                        "recommendation_hint": "Disable semantic ranker where it is not materially improving relevance.",
                        "potential_monthly_cost_impact_usd": round(
                            (semantic_queries / 1000.0)
                            * APPROX_SEMANTIC_RANKER_PRICE_PER_1K_QUERIES_USD,
                            2,
                        ),
                    },
                    impact="Premium semantic spend may not be aligned to actual query behavior.",
                )
            )

        if configuration.vector_search.enabled and metrics.feature_usage.vector_query_percentage < 5:
            findings.append(
                AnalysisFinding(
                    severity="medium",
                    category="feature_usage",
                    title="Review vector search footprint",
                    description="Vector search is enabled, but observed usage is low relative to stored vector data.",
                    evidence={
                        "metric": "vector_query_percentage",
                        "observed_value": round(metrics.feature_usage.vector_query_percentage, 1),
                        "expected_range": ">=5% vector usage for dedicated vector footprint",
                        "recommendation_hint": "Trim vector indexes or move low-value vector scenarios to a smaller footprint.",
                        "potential_monthly_cost_impact_usd": round(
                            metrics.total_index_size_gb * APPROX_VECTOR_STORAGE_PRICE_PER_GB_MONTH_USD,
                            2,
                        ),
                    },
                    impact="Vector storage and compute overhead may outweigh current workload value.",
                )
            )

        return findings
