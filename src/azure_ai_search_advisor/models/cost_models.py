"""Cost modeling contracts for Azure AI Search pricing scenarios."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from azure_ai_search_advisor.models.base import AdvisorModel


class PricingTier(StrEnum):
    """Dedicated Azure AI Search pricing tiers supported by the scaffold."""

    FREE = "free"
    BASIC = "basic"
    S1 = "s1"
    S2 = "s2"
    S3 = "s3"
    L1 = "l1"
    L2 = "l2"


class PricingModelOption(StrEnum):
    """High-level pricing model options for Azure AI Search workloads."""

    DEDICATED = "dedicated"
    SERVERLESS = "serverless"
    HYBRID = "hybrid"


class PricingReference(AdvisorModel):
    """Approximate pricing reference data for a dedicated Azure AI Search tier."""

    tier: PricingTier
    monthly_cost_per_search_unit_usd: float = Field(..., ge=0)
    included_search_units: int = Field(default=1, ge=0)
    region_note: str = "Approximate list pricing; verify against the Azure Pricing Calculator."
    approximate: bool = True
    notes: list[str] = Field(default_factory=list)


class SearchUnitCostInput(AdvisorModel):
    """Input contract for dedicated Search Unit cost modeling."""

    tier: PricingTier
    replicas: int = Field(..., ge=0)
    partitions: int = Field(..., ge=0)
    months: float = Field(default=1.0, gt=0)


class SearchUnitCostEstimate(AdvisorModel):
    """Output contract for dedicated Search Unit cost estimates."""

    tier: PricingTier
    replicas: int = Field(..., ge=0)
    partitions: int = Field(..., ge=0)
    search_units: int = Field(..., ge=0)
    monthly_cost_per_search_unit_usd: float = Field(..., ge=0)
    estimated_monthly_cost_usd: float = Field(..., ge=0)
    estimated_period_cost_usd: float = Field(..., ge=0)
    assumptions: list[str] = Field(default_factory=list)
    scaling_notes: list[str] = Field(default_factory=list)


class ServerlessCostInput(AdvisorModel):
    """Input contract for serverless Azure AI Search cost modeling."""

    monthly_queries: int = Field(..., ge=0)
    average_billable_compute_units_per_query: float = Field(default=1.0, ge=0)
    months: float = Field(default=1.0, gt=0)


class ServerlessCostEstimate(AdvisorModel):
    """Output contract for serverless query-based cost estimates."""

    monthly_queries: int = Field(..., ge=0)
    monthly_billable_compute_units: float = Field(..., ge=0)
    price_per_1k_compute_units_usd: float = Field(..., ge=0)
    estimated_monthly_cost_usd: float = Field(..., ge=0)
    estimated_period_cost_usd: float = Field(..., ge=0)
    assumptions: list[str] = Field(default_factory=list)


class FeatureCostInput(AdvisorModel):
    """Input contract for feature-level Azure AI Search add-on costs."""

    semantic_queries_per_month: int = Field(default=0, ge=0)
    enrichment_transactions_per_month: int = Field(default=0, ge=0)
    vector_index_storage_gb: float = Field(default=0.0, ge=0)
    months: float = Field(default=1.0, gt=0)


class FeatureCostLineItem(AdvisorModel):
    """Individual feature cost component."""

    feature_name: str
    unit_label: str
    unit_price_usd: float = Field(..., ge=0)
    usage_quantity: float = Field(..., ge=0)
    estimated_monthly_cost_usd: float = Field(..., ge=0)
    notes: list[str] = Field(default_factory=list)


class FeatureCostEstimate(AdvisorModel):
    """Output contract for feature-level cost estimates."""

    line_items: list[FeatureCostLineItem] = Field(default_factory=list)
    estimated_monthly_cost_usd: float = Field(..., ge=0)
    estimated_period_cost_usd: float = Field(..., ge=0)
    assumptions: list[str] = Field(default_factory=list)


class CostBreakdown(AdvisorModel):
    """Combined cost view across dedicated, serverless, and feature add-ons."""

    dedicated: SearchUnitCostEstimate | None = None
    serverless: ServerlessCostEstimate | None = None
    features: FeatureCostEstimate
    dedicated_total_monthly_cost_usd: float = Field(..., ge=0)
    serverless_total_monthly_cost_usd: float = Field(..., ge=0)
    assumptions: list[str] = Field(default_factory=list)


class CostComparison(AdvisorModel):
    """Side-by-side pricing comparison for dedicated and serverless models."""

    dedicated_total_monthly_cost_usd: float = Field(..., ge=0)
    serverless_total_monthly_cost_usd: float = Field(..., ge=0)
    monthly_difference_usd: float
    lower_cost_option: PricingModelOption | None = None
    notes: list[str] = Field(default_factory=list)


class CostModelRequest(AdvisorModel):
    """Top-level input contract for the cost modeling service."""

    dedicated_search: SearchUnitCostInput | None = None
    serverless_search: ServerlessCostInput | None = None
    feature_costs: FeatureCostInput = Field(default_factory=FeatureCostInput)


class CostModelResponse(AdvisorModel):
    """Top-level output contract for the cost modeling service."""

    breakdown: CostBreakdown
    comparison: CostComparison
    notes: list[str] = Field(default_factory=list)
