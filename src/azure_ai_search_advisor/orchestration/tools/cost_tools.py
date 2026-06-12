"""Tool functions that expose cost modeling capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.cost_modeling import CostModelingService
from azure_ai_search_advisor.models import (
    CostComparison,
    CostModelRequest,
    CostModelResponse,
    DeploymentMode,
    FeatureCostInput,
    PricingTier,
    SearchSku,
    SearchUnitCostInput,
    ServerlessCostInput,
    AzureSearchServiceSnapshot,
)


SKU_TO_PRICING_TIER = {
    SearchSku.FREE: PricingTier.FREE,
    SearchSku.BASIC: PricingTier.BASIC,
    SearchSku.S1: PricingTier.S1,
    SearchSku.S2: PricingTier.S2,
    SearchSku.S3: PricingTier.S3,
    SearchSku.S3_HD: PricingTier.S3,
    SearchSku.L1: PricingTier.L1,
    SearchSku.L2: PricingTier.L2,
}



def estimate_cost(
    *,
    snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
    request: CostModelRequest | Mapping[str, Any] | None = None,
    service: CostModelingService | None = None,
) -> CostModelResponse:
    """Estimate Azure AI Search workload costs for dedicated, serverless, and feature scenarios."""
    cost_service = service or CostModelingService()
    cost_request = _coerce_cost_request(snapshot=snapshot, request=request)
    return cost_service.simulate(cost_request)



def compare_pricing_models(
    *,
    snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
    request: CostModelRequest | Mapping[str, Any] | None = None,
    service: CostModelingService | None = None,
) -> CostComparison:
    """Compare dedicated and serverless pricing models for the supplied workload."""
    return estimate_cost(snapshot=snapshot, request=request, service=service).comparison



def _coerce_cost_request(
    *,
    snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None,
    request: CostModelRequest | Mapping[str, Any] | None,
) -> CostModelRequest:
    if request is not None:
        if isinstance(request, CostModelRequest):
            return request
        return CostModelRequest.model_validate(request)
    if snapshot is None:
        return CostModelRequest()

    resolved_snapshot = _coerce_snapshot(snapshot)
    configuration = resolved_snapshot.configuration
    metrics = resolved_snapshot.metrics
    monthly_queries = metrics.query_volume.monthly_queries
    feature_usage = metrics.feature_usage

    dedicated_search = None
    if configuration.deployment_mode == DeploymentMode.DEDICATED:
        dedicated_search = SearchUnitCostInput(
            tier=SKU_TO_PRICING_TIER[configuration.sku],
            replicas=configuration.replicas or 1,
            partitions=configuration.partitions or 1,
        )

    serverless_search = ServerlessCostInput(
        monthly_queries=monthly_queries,
        average_billable_compute_units_per_query=1.0,
    )

    feature_costs = FeatureCostInput(
        semantic_queries_per_month=int(
            monthly_queries * (feature_usage.semantic_query_percentage / 100)
        ),
        enrichment_transactions_per_month=int(feature_usage.ai_enrichment_runs_per_day * 30),
        vector_index_storage_gb=(
            metrics.total_index_size_gb if configuration.vector_search.enabled else 0.0
        ),
    )

    return CostModelRequest(
        dedicated_search=dedicated_search,
        serverless_search=serverless_search,
        feature_costs=feature_costs,
    )



def _coerce_snapshot(
    snapshot: AzureSearchServiceSnapshot | Mapping[str, Any],
) -> AzureSearchServiceSnapshot:
    if isinstance(snapshot, AzureSearchServiceSnapshot):
        return snapshot
    return AzureSearchServiceSnapshot.model_validate(snapshot)
