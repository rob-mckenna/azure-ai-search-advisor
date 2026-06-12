"""Shared domain and API models."""

from azure_ai_search_advisor.models.base import AdvisorModel
from azure_ai_search_advisor.models.configuration import (
    AIEnrichmentConfiguration,
    AzureSearchServiceConfiguration,
    DeploymentMode,
    SearchFeature,
    SearchSku,
    SemanticRankerConfiguration,
    VectorSearchAlgorithm,
    VectorSearchConfiguration,
    VectorizerType,
)
from azure_ai_search_advisor.models.cost_models import (
    CostBreakdown,
    CostComparison,
    CostModelRequest,
    CostModelResponse,
    FeatureCostEstimate,
    FeatureCostInput,
    FeatureCostLineItem,
    PricingModelOption,
    PricingReference,
    PricingTier,
    SearchUnitCostEstimate,
    SearchUnitCostInput,
    ServerlessCostEstimate,
    ServerlessCostInput,
)
from azure_ai_search_advisor.models.findings import AnalysisFinding, FindingEvidence
from azure_ai_search_advisor.models.metrics import (
    AzureSearchServiceMetrics,
    FeatureUsageStats,
    LatencyMetrics,
    QueryVolumeMetrics,
)
from azure_ai_search_advisor.models.recommendations import Recommendation, RecommendationReport
from azure_ai_search_advisor.models.snapshot import AzureSearchServiceSnapshot

__all__ = [
    "AIEnrichmentConfiguration",
    "AdvisorModel",
    "AnalysisFinding",
    "AzureSearchServiceConfiguration",
    "AzureSearchServiceMetrics",
    "AzureSearchServiceSnapshot",
    "CostBreakdown",
    "CostComparison",
    "CostModelRequest",
    "CostModelResponse",
    "DeploymentMode",
    "FeatureCostEstimate",
    "FeatureCostInput",
    "FeatureCostLineItem",
    "FeatureUsageStats",
    "FindingEvidence",
    "LatencyMetrics",
    "PricingModelOption",
    "PricingReference",
    "PricingTier",
    "QueryVolumeMetrics",
    "Recommendation",
    "RecommendationReport",
    "SearchFeature",
    "SearchSku",
    "SemanticRankerConfiguration",
    "SearchUnitCostEstimate",
    "SearchUnitCostInput",
    "ServerlessCostEstimate",
    "ServerlessCostInput",
    "VectorSearchAlgorithm",
    "VectorSearchConfiguration",
    "VectorizerType",
]
