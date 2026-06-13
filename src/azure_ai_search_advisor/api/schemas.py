"""HTTP request and response schemas for the API layer."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from azure_ai_search_advisor.models import CostModelRequest, CostModelResponse
from azure_ai_search_advisor.models.base import AdvisorModel


class ApiModel(AdvisorModel):
    """Base model for HTTP contracts."""

    model_config = ConfigDict(extra="forbid")


class PricingModel(StrEnum):
    """Azure AI Search pricing models exposed by the API."""

    DEDICATED = "dedicated"
    SERVERLESS = "serverless"


class FindingCategory(StrEnum):
    """High-level classes of analysis findings."""

    CAPACITY = "capacity"
    COST = "cost"
    FEATURE_USAGE = "feature_usage"
    QUERY_PERFORMANCE = "query_performance"
    INDEXING = "indexing"
    AVAILABILITY = "availability"


class SeverityLevel(StrEnum):
    """Severity scale shared across findings and recommendations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HealthStatus(StrEnum):
    """Service health states exposed by the API."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class RecommendationPriority(StrEnum):
    """Prioritization levels for recommendation output."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationSource(StrEnum):
    """Indicates how a recommendation request was fulfilled."""

    ANALYSIS_INPUT = "analysis_input"
    END_TO_END = "end_to_end"


class ErrorDetail(ApiModel):
    """Machine-readable error detail."""

    path: list[str] = Field(
        default_factory=list,
        description="Location of the invalid field or request attribute.",
        examples=[["body", "configuration", "capacity", "replica_count"]],
    )
    message: str = Field(
        description="Human-readable validation or processing message.",
        examples=["Input should be greater than or equal to 1"],
    )
    error_type: str = Field(
        description="Stable error category suitable for programmatic handling.",
        examples=["greater_than_equal"],
    )


class ErrorResponse(ApiModel):
    """Standard error envelope for API failures."""

    error_code: str = Field(
        description="Stable application error code.",
        examples=["validation_error"],
    )
    message: str = Field(
        description="Top-level description of the failure.",
        examples=["The request payload failed schema validation."],
    )
    status_code: int = Field(
        description="HTTP status code returned to the client.",
        examples=[422],
    )
    details: list[ErrorDetail] = Field(
        default_factory=list,
        description="Optional field-level or contextual error details.",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Trace identifier to correlate logs and client-side diagnostics.",
        examples=["f6b0c720-b97a-4e8e-9ed9-ded4952df2ae"],
    )


class SearchCapacity(ApiModel):
    """Provisioning and capacity configuration for a search service."""

    pricing_model: PricingModel = Field(
        description="Whether the service is dedicated or serverless.",
        examples=[PricingModel.DEDICATED],
    )
    sku: str = Field(
        description="Azure AI Search SKU or tier label.",
        examples=["standard"],
    )
    replica_count: int = Field(
        ge=0,
        description="Number of replicas assigned to the service.",
        examples=[3],
    )
    partition_count: int = Field(
        ge=0,
        description="Number of partitions assigned to the service.",
        examples=[2],
    )
    zone_redundancy_enabled: bool = Field(
        default=False,
        description="Whether zone redundancy is enabled for the service.",
    )


class SearchFeatureFlags(ApiModel):
    """Feature toggles that materially affect capability and cost."""

    semantic_ranker_enabled: bool = Field(
        default=False,
        description="Whether semantic ranking is enabled for supported indexes.",
    )
    vector_search_enabled: bool = Field(
        default=False,
        description="Whether vector search is enabled for the workload.",
    )
    ai_enrichment_enabled: bool = Field(
        default=False,
        description="Whether AI enrichment or skillsets are in active use.",
    )
    knowledge_store_enabled: bool = Field(
        default=False,
        description="Whether skillset output is persisted to a knowledge store.",
    )


class SearchIndexTopology(ApiModel):
    """Inventory and size profile of the service indexes."""

    index_count: int = Field(ge=0, description="Total number of indexes.", examples=[6])
    indexer_count: int = Field(
        ge=0,
        description="Number of indexers running against upstream data sources.",
        examples=[3],
    )
    skillset_count: int = Field(
        ge=0,
        description="Number of skillsets attached to indexing pipelines.",
        examples=[1],
    )
    total_document_count: int = Field(
        ge=0,
        description="Approximate total number of indexed documents.",
        examples=[1200000],
    )
    total_index_size_gb: float = Field(
        ge=0,
        description="Combined index size in gigabytes.",
        examples=[185.4],
    )
    vector_index_size_gb: float = Field(
        ge=0,
        default=0,
        description="Estimated vector payload size in gigabytes.",
        examples=[42.0],
    )


class SearchSecurityConfiguration(ApiModel):
    """Security and connectivity characteristics of the service."""

    api_keys_enabled: bool = Field(
        default=True,
        description="Whether admin or query API keys are enabled.",
    )
    managed_identity_enabled: bool = Field(
        default=False,
        description="Whether managed identity is used for downstream integrations.",
    )
    private_endpoint_enabled: bool = Field(
        default=False,
        description="Whether the service is isolated behind a private endpoint.",
    )
    customer_managed_keys_enabled: bool = Field(
        default=False,
        description="Whether encryption uses customer-managed keys.",
    )


class SearchServiceConfiguration(ApiModel):
    """Complete API-facing representation of an Azure AI Search service."""

    service_name: str = Field(
        min_length=1,
        description="Azure AI Search service name.",
        examples=["contoso-search-prod"],
    )
    region: str = Field(
        min_length=1,
        description="Azure region hosting the service.",
        examples=["eastus2"],
    )
    capacity: SearchCapacity = Field(
        description="Provisioning details that drive capacity and base cost."
    )
    features: SearchFeatureFlags = Field(
        description="Feature flags that influence cost and suitability."
    )
    index_topology: SearchIndexTopology = Field(
        description="Index inventory and storage profile."
    )
    security: SearchSecurityConfiguration = Field(
        description="Security and connectivity posture."
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Operator-provided notes or assumptions about the service.",
    )


class QueryMetrics(ApiModel):
    """Observed query demand and latency metrics."""

    average_queries_per_second: float = Field(
        ge=0,
        description="Mean sustained queries per second over the observation window.",
        examples=[18.2],
    )
    peak_queries_per_second: float = Field(
        ge=0,
        description="Peak observed queries per second.",
        examples=[74.0],
    )
    monthly_query_volume: int = Field(
        ge=0,
        description="Approximate monthly query count.",
        examples=[4300000],
    )
    p95_query_latency_ms: float = Field(
        ge=0,
        description="95th percentile end-user query latency in milliseconds.",
        examples=[185.0],
    )
    cache_hit_ratio: float = Field(
        ge=0,
        le=1,
        description="Observed cache hit ratio as a value between 0 and 1.",
        examples=[0.32],
    )


class IndexingMetrics(ApiModel):
    """Observed indexing throughput and maintenance behavior."""

    daily_document_updates: int = Field(
        ge=0,
        description="Approximate number of documents updated or ingested per day.",
        examples=[250000],
    )
    full_rebuilds_per_month: int = Field(
        ge=0,
        description="How often indexes are fully rebuilt in a typical month.",
        examples=[2],
    )
    average_indexing_latency_minutes: float = Field(
        ge=0,
        description="Average time between source change and searchable availability.",
        examples=[24.5],
    )


class UtilizationMetrics(ApiModel):
    """Utilization and feature adoption signals."""

    replica_utilization_percent: float = Field(
        ge=0,
        le=100,
        description="Estimated sustained utilization of replicas as a percentage.",
        examples=[41.0],
    )
    partition_utilization_percent: float = Field(
        ge=0,
        le=100,
        description="Estimated sustained utilization of partitions as a percentage.",
        examples=[58.0],
    )
    storage_utilization_percent: float = Field(
        ge=0,
        le=100,
        description="Percentage of storage currently consumed.",
        examples=[61.0],
    )
    semantic_queries_per_day: int = Field(
        ge=0,
        description="Daily query count using semantic ranking.",
        examples=[40000],
    )
    vector_queries_per_day: int = Field(
        ge=0,
        description="Daily vector query count.",
        examples=[12000],
    )


class SearchWorkloadMetrics(ApiModel):
    """Observed workload metrics paired with a search service."""

    observation_window_days: int = Field(
        ge=1,
        description="Number of days represented by the metrics snapshot.",
        examples=[30],
    )
    query: QueryMetrics = Field(description="Query demand and latency metrics.")
    indexing: IndexingMetrics = Field(description="Indexing activity metrics.")
    utilization: UtilizationMetrics = Field(
        description="Utilization metrics used for right-sizing."
    )


class DiscoveredServiceSummary(ApiModel):
    """Live Azure AI Search service discovered from Azure Resource Graph."""

    name: str = Field(description="Azure AI Search service name.")
    resource_group: str = Field(description="Azure resource group containing the service.")
    subscription_id: str = Field(description="Azure subscription identifier.")
    location: str = Field(description="Azure region hosting the service.")
    sku: str | None = Field(default=None, description="Discovered service SKU or tier label.")
    replica_count: int | None = Field(
        default=None,
        ge=0,
        description="Replica count reported by Azure for dedicated services.",
    )
    partition_count: int | None = Field(
        default=None,
        ge=0,
        description="Partition count reported by Azure for dedicated services.",
    )


class DiscoverResponse(ApiModel):
    """Response for GET /discover."""

    services: list[DiscoveredServiceSummary] = Field(
        default_factory=list,
        description="Azure AI Search services visible to the caller.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Discovery notes or caveats for the caller.",
    )


class TenantRole(StrEnum):
    """Tenant membership role."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class TenantSummary(ApiModel):
    """Tenant metadata returned by tenant APIs."""

    id: UUID = Field(description="Tenant identifier.")
    name: str = Field(description="Tenant display name.")
    created_at: datetime = Field(description="Tenant creation timestamp.")


class TenantContextResponse(ApiModel):
    """Resolved tenant context for the current caller."""

    tenant: TenantSummary = Field(description="Tenant resolved for the current request.")
    current_user_oid: str | None = Field(
        default=None,
        description="Microsoft Entra object id used to resolve the current membership.",
    )
    role: TenantRole = Field(description="Effective role for the current user.")
    permissions: list[str] = Field(
        default_factory=list,
        description="Tenant-scoped permissions granted to the current user.",
    )


class CreateTenantRequest(ApiModel):
    """Payload for POST /tenant."""

    name: str = Field(min_length=1, description="Display name for the new tenant.")


class TenantMemberRequest(ApiModel):
    """Payload for POST /tenant/members."""

    user_oid: str = Field(min_length=1, description="Microsoft Entra object id for the member.")
    role: TenantRole = Field(description="Role to assign to the member.")
    display_name: str | None = Field(default=None, description="Optional display name for the member.")
    email: str | None = Field(default=None, description="Optional email address for the member.")


class TenantMemberResponse(ApiModel):
    """Tenant membership returned by the API."""

    id: UUID = Field(description="Membership identifier.")
    tenant_id: UUID = Field(description="Tenant identifier for the membership.")
    user_oid: str = Field(description="Microsoft Entra object id for the member.")
    role: TenantRole = Field(description="Assigned tenant role.")
    display_name: str | None = Field(default=None, description="Optional display name for the member.")
    email: str | None = Field(default=None, description="Optional email address for the member.")
    added_at: datetime | None = Field(default=None, description="When the member was added.")


class TenantMembersResponse(ApiModel):
    """List of tenant members."""

    members: list[TenantMemberResponse] = Field(default_factory=list, description="Tenant members.")


class ServiceRegistrationRequest(ApiModel):
    """Payload for POST /tenant/services."""

    subscription_id: str = Field(min_length=1, description="Azure subscription identifier.")
    resource_group: str = Field(min_length=1, description="Azure resource group name.")
    service_name: str = Field(min_length=1, description="Azure AI Search service name.")


class ServiceRegistrationResponse(ApiModel):
    """Tenant service registration returned by the API."""

    id: UUID = Field(description="Service registration identifier.")
    tenant_id: UUID = Field(description="Tenant identifier owning the registration.")
    subscription_id: str = Field(description="Azure subscription identifier.")
    resource_group: str = Field(description="Azure resource group name.")
    service_name: str = Field(description="Azure AI Search service name.")
    added_by: str = Field(description="User who registered the service.")
    added_at: datetime = Field(description="When the service was registered.")


class TenantServicesResponse(ApiModel):
    """List of tenant-registered Azure AI Search services."""

    services: list[ServiceRegistrationResponse] = Field(
        default_factory=list,
        description="Azure AI Search services registered for the current tenant.",
    )


class AnalyzeRequest(ApiModel):
    """Payload for POST /analyze."""

    configuration: SearchServiceConfiguration = Field(
        description="Current Azure AI Search service configuration to analyze."
    )
    metrics: SearchWorkloadMetrics = Field(
        description="Observed workload metrics used to evaluate the configuration."
    )
    include_cost_signals: bool = Field(
        default=True,
        description="Whether to attach cost-oriented findings when analysis is implemented.",
    )
    include_feature_assessment: bool = Field(
        default=True,
        description="Whether to inspect feature adoption and misconfiguration patterns.",
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "configuration": {
                    "service_name": "contoso-search-prod",
                    "region": "eastus2",
                    "capacity": {
                        "pricing_model": "dedicated",
                        "sku": "standard",
                        "replica_count": 3,
                        "partition_count": 2,
                        "zone_redundancy_enabled": True,
                    },
                    "features": {
                        "semantic_ranker_enabled": True,
                        "vector_search_enabled": True,
                        "ai_enrichment_enabled": False,
                        "knowledge_store_enabled": False,
                    },
                    "index_topology": {
                        "index_count": 6,
                        "indexer_count": 3,
                        "skillset_count": 0,
                        "total_document_count": 1200000,
                        "total_index_size_gb": 185.4,
                        "vector_index_size_gb": 42.0,
                    },
                    "security": {
                        "api_keys_enabled": True,
                        "managed_identity_enabled": True,
                        "private_endpoint_enabled": True,
                        "customer_managed_keys_enabled": False,
                    },
                    "notes": ["Customer suspects the service is over-provisioned overnight."],
                },
                "metrics": {
                    "observation_window_days": 30,
                    "query": {
                        "average_queries_per_second": 18.2,
                        "peak_queries_per_second": 74.0,
                        "monthly_query_volume": 4300000,
                        "p95_query_latency_ms": 185.0,
                        "cache_hit_ratio": 0.32,
                    },
                    "indexing": {
                        "daily_document_updates": 250000,
                        "full_rebuilds_per_month": 2,
                        "average_indexing_latency_minutes": 24.5,
                    },
                    "utilization": {
                        "replica_utilization_percent": 41.0,
                        "partition_utilization_percent": 58.0,
                        "storage_utilization_percent": 61.0,
                        "semantic_queries_per_day": 40000,
                        "vector_queries_per_day": 12000,
                    },
                },
                "include_cost_signals": True,
                "include_feature_assessment": True,
            }
        },
    )


class FindingEvidence(ApiModel):
    """Evidence supporting an analysis finding."""

    metric: str = Field(
        description="Metric or attribute that supports the finding.",
        examples=["replica_utilization_percent"],
    )
    observed_value: Any = Field(
        description="Value observed in the request payload or downstream telemetry."
    )
    expected_range: str | None = Field(
        default=None,
        description="Optional expected or target range used for comparison.",
        examples=["60-80% during peak traffic"],
    )
    explanation: str = Field(
        description="Why the observed value matters for this finding.",
        examples=["Replica utilization appears low relative to peak query demand."],
    )


class AnalysisFinding(ApiModel):
    """Structured inefficiency or issue identified during analysis."""

    finding_id: str = Field(description="Stable identifier for the finding.")
    category: FindingCategory = Field(description="Type of issue identified.")
    severity: SeverityLevel = Field(description="Impact level of the issue.")
    title: str = Field(description="Short title summarizing the finding.")
    description: str = Field(description="Detailed explanation of the issue.")
    evidence: list[FindingEvidence] = Field(
        default_factory=list,
        description="Supporting evidence used to explain the finding.",
    )
    impacted_resources: list[str] = Field(
        default_factory=list,
        description="Resources or dimensions affected by the issue.",
    )
    potential_monthly_cost_impact_usd: float | None = Field(
        default=None,
        description="Estimated monthly cost impact once pricing logic exists.",
        examples=[180.0],
    )
    recommendation_hint: str | None = Field(
        default=None,
        description="Short hint that can seed recommendation generation.",
    )


class AnalysisSummary(ApiModel):
    """Top-level rollup of analysis output."""

    finding_count: int = Field(ge=0, description="Total number of findings returned.")
    highest_severity: SeverityLevel = Field(
        description="Highest severity level present in the findings."
    )
    optimization_themes: list[str] = Field(
        default_factory=list,
        description="High-level themes surfaced by the findings.",
    )
    overall_assessment: str = Field(
        description="Plain-language summary of the current workload posture."
    )


class AnalyzeResponse(ApiModel):
    """Response for POST /analyze."""

    request_id: str = Field(description="Correlation identifier for the analysis request.")
    status: Literal["placeholder", "completed"] = Field(
        description="Whether the response is illustrative or produced by a full engine.",
        examples=["placeholder"],
    )
    generated_at: datetime = Field(
        description="Timestamp when the response payload was generated."
    )
    summary: AnalysisSummary = Field(description="Rollup summary of the analysis.")
    findings: list[AnalysisFinding] = Field(
        default_factory=list,
        description="Detailed analysis findings.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Implementation notes, caveats, or follow-up guidance.",
    )


class RecommendationPreferences(ApiModel):
    """Client preferences for recommendation generation."""

    max_recommendations: int = Field(
        ge=1,
        le=20,
        default=5,
        description="Maximum number of recommendations to return.",
    )
    prioritize_for: list[Literal["cost", "performance", "availability", "operability"]] = Field(
        default_factory=lambda: ["cost", "performance"],
        description="Optimization goals to prioritize when ranking recommendations.",
    )
    include_remediation_steps: bool = Field(
        default=True,
        description="Whether remediation steps should be included in each recommendation.",
    )


class RecommendRequest(ApiModel):
    """Payload for POST /recommend."""

    analysis: AnalyzeResponse | None = Field(
        default=None,
        description="Optional precomputed analysis findings to convert into recommendations.",
    )
    configuration: SearchServiceConfiguration | None = Field(
        default=None,
        description="Raw Azure AI Search configuration for end-to-end recommendation flows.",
    )
    metrics: SearchWorkloadMetrics | None = Field(
        default=None,
        description="Optional metrics used for end-to-end recommendation flows.",
    )
    preferences: RecommendationPreferences = Field(
        default_factory=RecommendationPreferences,
        description="Controls recommendation ranking and detail level.",
    )

    @model_validator(mode="after")
    def validate_source_payload(self) -> "RecommendRequest":
        """Require either analysis findings or raw configuration."""

        if self.analysis is None and self.configuration is None:
            raise ValueError("Either analysis or configuration must be provided.")

        if self.metrics is not None and self.configuration is None:
            raise ValueError("metrics cannot be provided without configuration.")

        if self.configuration is not None and self.metrics is None:
            raise ValueError("metrics must be provided when configuration is supplied for end-to-end recommendations.")

        return self

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "analysis": {
                    "request_id": "anl_01JY0D5K5W2K2T6K06P2Q1CV8P",
                    "status": "completed",
                    "generated_at": "2026-06-12T15:00:00Z",
                    "summary": {
                        "finding_count": 2,
                        "highest_severity": "high",
                        "optimization_themes": ["replica_right_sizing", "semantic_usage_alignment"],
                        "overall_assessment": "The service is stable but appears oversized for sustained demand.",
                    },
                    "findings": [
                        {
                            "finding_id": "capacity-low-utilization",
                            "category": "capacity",
                            "severity": "high",
                            "title": "Replica utilization is consistently low",
                            "description": "The service appears to maintain more replicas than the observed workload requires.",
                            "evidence": [
                                {
                                    "metric": "replica_utilization_percent",
                                    "observed_value": 41.0,
                                    "expected_range": "60-80% during peak traffic",
                                    "explanation": "Replica utilization is well below typical efficiency targets.",
                                }
                            ],
                            "impacted_resources": ["capacity", "cost"],
                            "potential_monthly_cost_impact_usd": 180.0,
                            "recommendation_hint": "Evaluate reducing replicas during steady-state traffic.",
                        }
                    ],
                    "notes": [],
                },
                "preferences": {
                    "max_recommendations": 3,
                    "prioritize_for": ["cost", "availability"],
                    "include_remediation_steps": True,
                },
            }
        },
    )


class RemediationStep(ApiModel):
    """Single recommendation implementation step."""

    step_number: int = Field(ge=1, description="Execution order for the step.")
    action: str = Field(description="Short action statement.")
    detail: str = Field(description="Implementation guidance for the action.")
    owner_hint: str | None = Field(
        default=None,
        description="Suggested owner such as platform, search, or app team.",
    )


class ProjectedImpact(ApiModel):
    """Expected recommendation outcomes."""

    monthly_cost_delta_usd: float | None = Field(
        default=None,
        description="Estimated monthly cost change once models are implemented.",
        examples=[-180.0],
    )
    performance_impact: str | None = Field(
        default=None,
        description="Narrative summary of likely performance impact.",
    )
    risk_reduction: str | None = Field(
        default=None,
        description="Narrative summary of operational or availability risk reduction.",
    )


class RecommendationItem(ApiModel):
    """Prioritized recommendation returned by the API."""

    recommendation_id: str = Field(description="Stable identifier for the recommendation.")
    priority: RecommendationPriority = Field(description="Recommendation priority level.")
    title: str = Field(description="Short recommendation title.")
    summary: str = Field(description="Plain-language recommendation summary.")
    rationale: str = Field(description="Why this recommendation is being made.")
    projected_impact: ProjectedImpact = Field(
        description="Expected outcomes if the recommendation is implemented."
    )
    remediation_steps: list[RemediationStep] = Field(
        default_factory=list,
        description="Ordered steps to implement the recommendation.",
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        description="Dependencies or checks required before execution.",
    )
    tradeoffs: list[str] = Field(
        default_factory=list,
        description="Known tradeoffs or cautionary notes.",
    )


class RecommendResponse(ApiModel):
    """Response for POST /recommend."""

    request_id: str = Field(
        description="Correlation identifier for the recommendation request."
    )
    status: Literal["placeholder", "completed"] = Field(
        description="Whether the response is illustrative or fully computed."
    )
    generated_at: datetime = Field(
        description="Timestamp when recommendation output was generated."
    )
    source: RecommendationSource = Field(
        description="Whether the response was based on analysis input or raw configuration."
    )
    recommendations: list[RecommendationItem] = Field(
        default_factory=list,
        description="Prioritized recommendations for the workload.",
    )
    summary: str = Field(description="Top-level summary of recommendation output.")
    notes: list[str] = Field(
        default_factory=list,
        description="Implementation notes or caveats for the client.",
    )


class HistoricalRunSummary(ApiModel):
    """Stored summary for a historical analysis run."""

    id: str = Field(description="Unique identifier for the stored analysis run.")
    service_name: str = Field(description="Azure AI Search service name.")
    subscription_id: str = Field(description="Azure subscription identifier.")
    resource_group: str = Field(description="Azure resource group containing the service.")
    run_at: datetime = Field(description="Timestamp when the analysis run was recorded.")
    finding_count: int = Field(ge=0, description="Number of findings captured for the run.")
    highest_severity: SeverityLevel = Field(description="Highest severity captured for the run.")
    configuration_hash: str = Field(description="Stable hash of the analyzed configuration.")
    dedicated_monthly_usd: float | None = Field(
        default=None,
        description="Estimated dedicated monthly cost for the run, when available.",
    )
    serverless_monthly_usd: float | None = Field(
        default=None,
        description="Estimated serverless monthly cost for the run, when available.",
    )
    lower_cost_option: PricingModel | None = Field(
        default=None,
        description="Lower-cost option observed for the stored run, when available.",
    )
    recommendation_count: int = Field(
        ge=0,
        default=0,
        description="Number of recommendations stored for the run.",
    )


class ServiceHistoryResponse(ApiModel):
    """Historical analysis runs for a single service."""

    service_name: str = Field(description="Azure AI Search service name.")
    days: int = Field(ge=1, description="Window used to filter historical runs.")
    limit: int = Field(ge=1, description="Maximum number of runs requested.")
    runs: list[HistoricalRunSummary] = Field(
        default_factory=list,
        description="Historical runs ordered from newest to oldest.",
    )


class FindingCountTrendPoint(ApiModel):
    """Finding-count trend point."""

    run_at: datetime = Field(description="Timestamp for the recorded analysis run.")
    finding_count: int = Field(ge=0, description="Finding count captured at that time.")


class CostTrendPoint(ApiModel):
    """Cost trend point."""

    run_at: datetime = Field(description="Timestamp for the recorded analysis run.")
    dedicated_monthly_usd: float | None = Field(
        default=None,
        description="Estimated dedicated monthly cost for that run.",
    )
    serverless_monthly_usd: float | None = Field(
        default=None,
        description="Estimated serverless monthly cost for that run.",
    )
    lower_cost_option: PricingModel | None = Field(
        default=None,
        description="Lower-cost option observed for that run.",
    )


class ServiceHistoryTrendsResponse(ApiModel):
    """Historical trend data for a single service."""

    service_name: str = Field(description="Azure AI Search service name.")
    days: int = Field(ge=1, description="Window used to filter trend data.")
    limit: int = Field(ge=1, description="Maximum number of trend points requested.")
    finding_count_over_time: list[FindingCountTrendPoint] = Field(
        default_factory=list,
        description="Finding count trend ordered from oldest to newest.",
    )
    cost_over_time: list[CostTrendPoint] = Field(
        default_factory=list,
        description="Cost trend ordered from oldest to newest.",
    )


class SimulationChange(ApiModel):
    """Atomic configuration change to simulate."""

    change_id: str = Field(description="Stable identifier for the proposed change.")
    target: str = Field(
        description="Logical configuration area affected by the change.",
        examples=["capacity"],
    )
    attribute: str = Field(
        description="Specific attribute or setting to adjust.",
        examples=["replica_count"],
    )
    current_value: Any | None = Field(
        default=None,
        description="Current value before applying the change, if known.",
    )
    proposed_value: Any = Field(description="Desired value for the simulated scenario.")
    rationale: str = Field(description="Why the change is being considered.")


class SimulationAssumptions(ApiModel):
    """Assumptions used during cost simulation."""

    pricing_horizon_days: int = Field(
        ge=1,
        default=30,
        description="Number of days over which the simulation should be normalized.",
    )
    currency: str = Field(
        default="USD",
        description="Currency for all simulated cost outputs.",
        examples=["USD"],
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Explicit assumptions that should appear in the response.",
    )


class SimulateRequest(ApiModel):
    """Payload for POST /simulate."""

    current_configuration: SearchServiceConfiguration | None = Field(
        default=None,
        description="Current search service configuration.",
    )
    current_metrics: SearchWorkloadMetrics | None = Field(
        default=None,
        description="Optional current workload metrics used to interpret the change.",
    )
    proposed_changes: list[SimulationChange] = Field(
        default_factory=list,
        description="One or more proposed configuration changes to simulate.",
    )
    cost_model_request: CostModelRequest | None = Field(
        default=None,
        description="Optional direct cost-model request when simulating pricing without configuration diffs.",
    )
    assumptions: SimulationAssumptions = Field(
        default_factory=SimulationAssumptions,
        description="Simulation assumptions and normalization controls.",
    )

    @model_validator(mode="after")
    def validate_simulation_source(self) -> "SimulateRequest":
        """Require either a direct cost model request or a configuration diff request."""

        if self.cost_model_request is not None:
            return self

        if self.current_configuration is None:
            raise ValueError("current_configuration is required when cost_model_request is not provided.")

        if not self.proposed_changes:
            raise ValueError("At least one proposed change is required when simulating configuration differences.")

        return self

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "current_configuration": {
                    "service_name": "contoso-search-prod",
                    "region": "eastus2",
                    "capacity": {
                        "pricing_model": "dedicated",
                        "sku": "standard",
                        "replica_count": 3,
                        "partition_count": 2,
                        "zone_redundancy_enabled": True,
                    },
                    "features": {
                        "semantic_ranker_enabled": True,
                        "vector_search_enabled": True,
                        "ai_enrichment_enabled": False,
                        "knowledge_store_enabled": False,
                    },
                    "index_topology": {
                        "index_count": 6,
                        "indexer_count": 3,
                        "skillset_count": 0,
                        "total_document_count": 1200000,
                        "total_index_size_gb": 185.4,
                        "vector_index_size_gb": 42.0,
                    },
                    "security": {
                        "api_keys_enabled": True,
                        "managed_identity_enabled": True,
                        "private_endpoint_enabled": True,
                        "customer_managed_keys_enabled": False,
                    },
                    "notes": [],
                },
                "proposed_changes": [
                    {
                        "change_id": "reduce-replicas",
                        "target": "capacity",
                        "attribute": "replica_count",
                        "current_value": 3,
                        "proposed_value": 2,
                        "rationale": "Observed replica utilization is below 50% during sustained traffic.",
                    }
                ],
                "assumptions": {
                    "pricing_horizon_days": 30,
                    "currency": "USD",
                    "notes": ["Compare like-for-like monthly cost without reserved capacity discounts."],
                },
            }
        },
    )


class ScenarioCostEstimate(ApiModel):
    """Cost estimate for a single scenario."""

    currency: str = Field(description="Currency for the estimate.", examples=["USD"])
    monthly_total: float = Field(
        ge=0,
        description="Estimated total monthly cost.",
        examples=[540.0],
    )
    compute_monthly: float = Field(
        ge=0,
        description="Estimated base compute or search unit cost.",
        examples=[420.0],
    )
    semantic_monthly: float = Field(
        ge=0,
        default=0,
        description="Estimated semantic ranking cost component.",
        examples=[80.0],
    )
    vector_monthly: float = Field(
        ge=0,
        default=0,
        description="Estimated vector search cost component.",
        examples=[40.0],
    )
    enrichment_monthly: float = Field(
        ge=0,
        default=0,
        description="Estimated AI enrichment cost component.",
        examples=[0.0],
    )


class CostComparison(ApiModel):
    """Side-by-side current and proposed scenario cost output."""

    current_estimate: ScenarioCostEstimate = Field(
        description="Illustrative cost estimate for the current state."
    )
    proposed_estimate: ScenarioCostEstimate = Field(
        description="Illustrative cost estimate for the proposed scenario."
    )
    monthly_delta: float = Field(
        description="Proposed minus current estimated monthly total.",
        examples=[-120.0],
    )
    monthly_savings_percent: float | None = Field(
        default=None,
        description="Percentage savings if the proposal reduces cost.",
        examples=[22.22],
    )


class SimulationImpact(ApiModel):
    """Narrative impact assessment for a simulation run."""

    capacity_risk: str = Field(
        description="Risk posture introduced by the proposed changes."
    )
    latency_expectation: str = Field(
        description="Expected effect on latency once implemented."
    )
    operational_notes: list[str] = Field(
        default_factory=list,
        description="Follow-up notes or caveats for interpreting the output.",
    )


class SimulateResponse(ApiModel):
    """Response for POST /simulate."""

    request_id: str = Field(description="Correlation identifier for the simulation.")
    status: Literal["placeholder", "completed"] = Field(
        description="Whether the payload is illustrative or fully calculated."
    )
    generated_at: datetime = Field(
        description="Timestamp when the simulation response was generated."
    )
    comparison: CostComparison = Field(
        description="Current-versus-proposed cost comparison."
    )
    projected_impact: SimulationImpact = Field(
        description="Narrative interpretation of the proposed changes."
    )
    current_cost_model: CostModelResponse | None = Field(
        default=None,
        description="Detailed cost model output for the current or baseline scenario.",
    )
    proposed_cost_model: CostModelResponse | None = Field(
        default=None,
        description="Detailed cost model output for the proposed scenario when applicable.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Implementation notes and modeling caveats.",
    )


class DependencyHealth(ApiModel):
    """Health status for a dependency or subsystem."""

    name: str = Field(description="Dependency or subsystem name.", examples=["api"])
    status: HealthStatus = Field(description="Current dependency health state.")
    detail: str = Field(description="Operator-facing health detail.")


class HealthResponse(ApiModel):
    """Response for GET /health."""

    status: HealthStatus = Field(description="Overall service health state.")
    service: str = Field(description="Service name.", examples=["azure-ai-search-advisor"])
    version: str = Field(description="Running application version.", examples=["0.1.0"])
    checked_at: datetime = Field(
        description="Timestamp when the health response was generated."
    )
    dependencies: list[DependencyHealth] = Field(
        default_factory=list,
        description="Health signals for key subsystems and dependencies.",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Operator notes about health scope or known limitations.",
    )
