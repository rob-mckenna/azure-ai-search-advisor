"""Helpers for translating between API contracts and domain service models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from azure_ai_search_advisor.analysis.service import AnalysisResult
from azure_ai_search_advisor.api.schemas import (
    AnalysisFinding as ApiAnalysisFinding,
    AnalysisSummary,
    AnalyzeResponse,
    CostComparison as ApiCostComparison,
    FindingCategory,
    FindingEvidence as ApiFindingEvidence,
    ProjectedImpact,
    RecommendationItem,
    RecommendationPriority,
    RecommendationSource,
    RemediationStep,
    ScenarioCostEstimate,
    SearchServiceConfiguration,
    SearchWorkloadMetrics,
    SeverityLevel,
    SimulationChange,
    SimulationImpact,
    SimulateResponse,
)
from azure_ai_search_advisor.models import CostModelRequest, CostModelResponse, PricingModelOption
from azure_ai_search_advisor.models.configuration import DeploymentMode, SearchFeature, SearchSku
from azure_ai_search_advisor.models.cost_models import FeatureCostInput, PricingTier, SearchUnitCostInput, ServerlessCostInput
from azure_ai_search_advisor.models.recommendations import RecommendationReport

API_TO_DOMAIN_SKU: dict[str, SearchSku] = {
    "free": SearchSku.FREE,
    "basic": SearchSku.BASIC,
    "standard": SearchSku.S1,
    "standard1": SearchSku.S1,
    "s1": SearchSku.S1,
    "standard2": SearchSku.S2,
    "s2": SearchSku.S2,
    "standard3": SearchSku.S3,
    "s3": SearchSku.S3,
    "s3_hd": SearchSku.S3_HD,
    "l1": SearchSku.L1,
    "l2": SearchSku.L2,
}
DOMAIN_TO_PRICING_TIER: dict[SearchSku, PricingTier] = {
    SearchSku.FREE: PricingTier.FREE,
    SearchSku.BASIC: PricingTier.BASIC,
    SearchSku.S1: PricingTier.S1,
    SearchSku.S2: PricingTier.S2,
    SearchSku.S3: PricingTier.S3,
    SearchSku.S3_HD: PricingTier.S3,
    SearchSku.L1: PricingTier.L1,
    SearchSku.L2: PricingTier.L2,
}
SEVERITY_ORDER = {
    SeverityLevel.LOW: 0,
    SeverityLevel.MEDIUM: 1,
    SeverityLevel.HIGH: 2,
    SeverityLevel.CRITICAL: 3,
}


def build_snapshot_payload(
    configuration: SearchServiceConfiguration,
    metrics: SearchWorkloadMetrics,
) -> dict[str, Any]:
    """Translate API payloads into the domain snapshot ingestion contract."""

    avg_queries_per_day = max(
        int(round(metrics.query.monthly_query_volume / max(metrics.observation_window_days, 1))),
        1,
    )
    peak_queries_per_day = max(avg_queries_per_day, int(round(metrics.query.peak_queries_per_second * 3600)))
    semantic_query_percentage = min(
        (metrics.utilization.semantic_queries_per_day / avg_queries_per_day) * 100.0,
        100.0,
    )
    vector_query_percentage = min(
        (metrics.utilization.vector_queries_per_day / avg_queries_per_day) * 100.0,
        100.0,
    )
    inferred_sku = _map_api_sku(configuration.capacity.sku)
    features_enabled = _build_feature_list(configuration)
    ai_enrichment_enabled = configuration.features.ai_enrichment_enabled
    vector_enabled = configuration.features.vector_search_enabled
    semantic_enabled = configuration.features.semantic_ranker_enabled
    skillset_count = configuration.index_topology.skillset_count

    return {
        "schema_version": "1.0",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "service_name": configuration.service_name,
            "subscription_id": "api-submitted",
            "resource_group": f"{configuration.service_name}-rg",
            "location": configuration.region,
            "deployment_mode": configuration.capacity.pricing_model.value,
            "sku": inferred_sku.value,
            "replicas": configuration.capacity.replica_count
            if configuration.capacity.pricing_model.value == DeploymentMode.DEDICATED.value
            else None,
            "partitions": configuration.capacity.partition_count
            if configuration.capacity.pricing_model.value == DeploymentMode.DEDICATED.value
            else None,
            "high_density": inferred_sku == SearchSku.S3_HD,
            "availability_zones_enabled": configuration.capacity.zone_redundancy_enabled,
            "private_endpoint_enabled": configuration.security.private_endpoint_enabled,
            "public_network_access_enabled": not configuration.security.private_endpoint_enabled,
            "managed_identity_enabled": configuration.security.managed_identity_enabled,
            "index_count": configuration.index_topology.index_count,
            "indexer_count": configuration.index_topology.indexer_count,
            "data_source_count": configuration.index_topology.indexer_count,
            "skillset_count": skillset_count,
            "features_enabled": [feature.value for feature in features_enabled],
            "semantic_ranker": {
                "enabled": semantic_enabled,
                "default_configuration_name": "api-submitted-semantic-config" if semantic_enabled else None,
                "query_cap_per_month": metrics.query.monthly_query_volume if semantic_enabled else None,
                "prioritized_fields_configured": semantic_enabled,
            },
            "vector_search": {
                "enabled": vector_enabled,
                "algorithm": "hnsw" if vector_enabled else None,
                "profile_count": 1 if vector_enabled else 0,
                "vectorizer": "none",
                "integrated_vectorization_enabled": False,
                "vector_index_count": 1 if vector_enabled else 0,
            },
            "ai_enrichment": {
                "enabled": ai_enrichment_enabled,
                "skillset_count": max(skillset_count, 1) if ai_enrichment_enabled else 0,
                "knowledge_store_enabled": configuration.features.knowledge_store_enabled,
                "cognitive_services_attached": ai_enrichment_enabled,
                "image_extraction_enabled": False,
                "custom_skill_count": 0,
            },
        },
        "metrics": {
            "observation_window_days": metrics.observation_window_days,
            "query_volume": {
                "avg_queries_per_day": avg_queries_per_day,
                "peak_queries_per_day": peak_queries_per_day,
                "avg_queries_per_second": metrics.query.average_queries_per_second,
                "monthly_queries": metrics.query.monthly_query_volume,
            },
            "total_index_size_gb": configuration.index_topology.total_index_size_gb,
            "document_count": configuration.index_topology.total_document_count,
            "feature_usage": {
                "semantic_query_percentage": semantic_query_percentage if semantic_enabled else 0.0,
                "vector_query_percentage": vector_query_percentage if vector_enabled else 0.0,
                "ai_enrichment_runs_per_day": 1 if ai_enrichment_enabled else 0,
                "indexer_runs_per_day": float(configuration.index_topology.indexer_count),
                "skill_invocations_per_day": metrics.indexing.daily_document_updates
                if ai_enrichment_enabled
                else 0,
                "integrated_vectorization_calls_per_day": metrics.utilization.vector_queries_per_day
                if vector_enabled
                else 0,
            },
            "latency": {
                "p50_ms": round(metrics.query.p95_query_latency_ms * 0.6, 2),
                "p95_ms": metrics.query.p95_query_latency_ms,
                "p99_ms": round(metrics.query.p95_query_latency_ms * 1.3, 2),
            },
            "avg_cpu_utilization_pct": metrics.utilization.replica_utilization_percent,
            "storage_quota_utilization_pct": metrics.utilization.storage_utilization_percent,
            "throttled_queries_per_day": 0,
            "indexing_operations_per_day": metrics.indexing.daily_document_updates,
        },
        "notes": configuration.notes,
    }


def build_cost_model_request(
    configuration: SearchServiceConfiguration,
    metrics: SearchWorkloadMetrics | None,
    *,
    pricing_horizon_days: int = 30,
) -> CostModelRequest:
    """Translate API configuration and metrics into a cost-model request."""

    months = max(pricing_horizon_days / 30.0, 1 / 30.0)
    domain_sku = _map_api_sku(configuration.capacity.sku)
    dedicated_search = None
    if configuration.capacity.pricing_model.value == DeploymentMode.DEDICATED.value:
        dedicated_search = SearchUnitCostInput(
            tier=DOMAIN_TO_PRICING_TIER[domain_sku],
            replicas=max(configuration.capacity.replica_count, 1),
            partitions=max(configuration.capacity.partition_count, 1),
            months=months,
        )

    monthly_queries = _estimate_monthly_queries(metrics)
    serverless_search = ServerlessCostInput(
        monthly_queries=monthly_queries,
        average_billable_compute_units_per_query=(
            1.0
            + (0.25 if configuration.features.semantic_ranker_enabled else 0.0)
            + (0.25 if configuration.features.vector_search_enabled else 0.0)
            + (0.5 if configuration.features.ai_enrichment_enabled else 0.0)
        ),
        months=months,
    )
    feature_costs = FeatureCostInput(
        semantic_queries_per_month=(metrics.utilization.semantic_queries_per_day * 30)
        if metrics is not None and configuration.features.semantic_ranker_enabled
        else 0,
        enrichment_transactions_per_month=(metrics.indexing.daily_document_updates * 30)
        if metrics is not None and configuration.features.ai_enrichment_enabled
        else 0,
        vector_index_storage_gb=configuration.index_topology.vector_index_size_gb
        if configuration.features.vector_search_enabled
        else 0.0,
        months=months,
    )
    return CostModelRequest(
        dedicated_search=dedicated_search,
        serverless_search=serverless_search,
        feature_costs=feature_costs,
    )


def apply_proposed_changes(
    configuration: SearchServiceConfiguration,
    proposed_changes: list[SimulationChange],
) -> SearchServiceConfiguration:
    """Apply API simulation changes and return a validated configuration copy."""

    updated_payload = configuration.model_dump(mode="python")
    for change in proposed_changes:
        if change.target in {"capacity", "features", "index_topology", "security"}:
            updated_payload[change.target][change.attribute] = change.proposed_value
        else:
            updated_payload[change.attribute] = change.proposed_value
    return SearchServiceConfiguration.model_validate(updated_payload)


def map_analysis_result_to_response(result: AnalysisResult) -> AnalyzeResponse:
    """Map the domain analysis result into the HTTP response contract."""
    return map_analysis_result_to_response_with_notes(result)


def map_analysis_result_to_response_with_notes(
    result: AnalysisResult,
    *,
    extra_notes: list[str] | None = None,
) -> AnalyzeResponse:
    """Map the domain analysis result into the HTTP response contract."""

    findings = [_map_analysis_finding(item, index) for index, item in enumerate(result.findings, start=1)]
    highest_severity = max(
        (finding.severity for finding in findings),
        key=lambda item: SEVERITY_ORDER[item],
        default=SeverityLevel.LOW,
    )
    themes = sorted({finding.category.value for finding in findings})
    overall_assessment = (
        f"Detected {len(findings)} optimization opportunity(ies) across the submitted workload."
        if findings
        else "No obvious inefficiencies were detected by the current analysis heuristics."
    )

    return AnalyzeResponse(
        request_id=f"anl_{uuid4().hex}",
        status="completed",
        generated_at=datetime.now(timezone.utc),
        summary=AnalysisSummary(
            finding_count=len(findings),
            highest_severity=highest_severity,
            optimization_themes=themes,
            overall_assessment=overall_assessment,
        ),
        findings=findings,
        notes=[
            "Results combine the current analysis service plus lightweight API-to-domain normalization.",
            *(extra_notes or []),
        ],
    )


def build_recommendation_inputs(
    analysis: AnalyzeResponse,
    configuration: SearchServiceConfiguration | None,
    metrics: SearchWorkloadMetrics | None,
    cost_model_response: CostModelResponse | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the dictionaries expected by RecommendationService."""

    service: dict[str, Any] = {}
    topology: dict[str, Any] = {}
    features: dict[str, Any] = {}
    pricing: dict[str, Any] = {}
    alerting: dict[str, Any] = {}

    if configuration is not None:
        service = {
            "service_name": configuration.service_name,
            "replicas": configuration.capacity.replica_count,
            "partitions": configuration.capacity.partition_count,
            "sku": configuration.capacity.sku,
            "hosting_mode": configuration.capacity.pricing_model.value,
            "indexer_count": configuration.index_topology.indexer_count,
        }
        alerting.update(
            {
                "indexer_count": configuration.index_topology.indexer_count,
                "indexer_monitoring_configured": False,
            }
        )
        features.update(
            {
                "semantic_ranker_enabled": configuration.features.semantic_ranker_enabled,
                "vector_search_enabled": configuration.features.vector_search_enabled,
            }
        )

    if configuration is not None and metrics is not None:
        avg_daily_queries = max(
            metrics.query.monthly_query_volume / max(metrics.observation_window_days, 1),
            1.0,
        )
        features.update(
            {
                "semantic_query_ratio": min(
                    metrics.utilization.semantic_queries_per_day / avg_daily_queries,
                    1.0,
                ),
                "vector_optimization_opportunity": configuration.features.vector_search_enabled
                and metrics.utilization.vector_queries_per_day / avg_daily_queries < 0.05,
            }
        )
        if (
            configuration.capacity.pricing_model.value == DeploymentMode.DEDICATED.value
            and metrics.utilization.replica_utilization_percent < 50
            and configuration.capacity.replica_count > 1
        ):
            topology["replica_overprovisioned"] = True
            topology["suggested_replicas"] = max(configuration.capacity.replica_count - 1, 1)
        if (
            configuration.capacity.pricing_model.value == DeploymentMode.DEDICATED.value
            and metrics.utilization.partition_utilization_percent < 65
            and configuration.capacity.partition_count > 1
        ):
            topology["partition_overprovisioned"] = True
            topology["suggested_partitions"] = max(configuration.capacity.partition_count - 1, 1)
        alerting.update(
            {
                "query_latency_p95_ms": metrics.query.p95_query_latency_ms,
                "replica_utilization_percent": metrics.utilization.replica_utilization_percent,
                "storage_utilization_percent": metrics.utilization.storage_utilization_percent,
                "throttled_queries_per_day": 0.0,
                "avg_queries_per_second": metrics.query.average_queries_per_second,
                "avg_cpu_utilization_pct": metrics.utilization.replica_utilization_percent,
            }
        )
        if (
            configuration.capacity.pricing_model.value == DeploymentMode.DEDICATED.value
            and metrics.query.monthly_query_volume < 100_000
            and not configuration.features.semantic_ranker_enabled
            and not configuration.features.vector_search_enabled
            and not configuration.features.ai_enrichment_enabled
        ):
            pricing["switch_to_serverless_candidate"] = True

    analysis_cost_impact = sum(
        finding.potential_monthly_cost_impact_usd or 0.0 for finding in analysis.findings
    )

    for finding in analysis.findings:
        combined_text = " ".join(
            filter(
                None,
                [finding.title, finding.description, finding.recommendation_hint],
            )
        ).lower()
        if "replica" in combined_text:
            topology["replica_overprovisioned"] = True
        if "partition" in combined_text:
            topology["partition_overprovisioned"] = True
        if "serverless" in combined_text:
            pricing["switch_to_serverless_candidate"] = True
        if "semantic" in combined_text:
            features.setdefault("semantic_ranker_enabled", True)
        if "vector" in combined_text:
            features.setdefault("vector_search_enabled", True)
        if "latency" in combined_text:
            alerting.setdefault("query_latency_p95_ms", metrics.query.p95_query_latency_ms if metrics is not None else 0.0)
        if "throttl" in combined_text:
            alerting["throttled_queries_detected"] = True
        if "storage" in combined_text:
            alerting.setdefault(
                "storage_utilization_percent",
                metrics.utilization.storage_utilization_percent if metrics is not None else 0.0,
            )

    cost_data = _build_cost_data(cost_model_response)
    if analysis_cost_impact and not cost_model_response:
        cost_data["potential_monthly_savings"] = round(analysis_cost_impact, 2)
        cost_data["scenario_comparison"]["recommended_monthly_savings"] = round(analysis_cost_impact, 2)
        cost_data["scenario_comparison"]["recommended_annual_savings"] = round(analysis_cost_impact * 12, 2)
    scenario_comparison = cost_data.get("scenario_comparison", {})
    if topology.get("replica_overprovisioned"):
        topology.setdefault(
            "estimated_monthly_savings",
            scenario_comparison.get("replica_monthly_savings", cost_data.get("potential_monthly_savings", 0.0)),
        )
    if topology.get("partition_overprovisioned"):
        topology.setdefault(
            "estimated_partition_savings",
            scenario_comparison.get("partition_monthly_savings", cost_data.get("potential_monthly_savings", 0.0)),
        )
    if pricing.get("switch_to_serverless_candidate"):
        pricing.setdefault(
            "switch_to_serverless_candidate",
            scenario_comparison.get("serverless_monthly_savings", 0.0) > 0,
        )

    if cost_model_response is not None:
        feature_line_items = {
            item.feature_name: item.estimated_monthly_cost_usd
            for item in cost_model_response.breakdown.features.line_items
        }
        features["estimated_semantic_monthly_cost"] = feature_line_items.get("semantic_ranker", 0.0)
        features["estimated_vector_monthly_savings"] = feature_line_items.get("vector_storage", 0.0)

    return (
        {
            "service": service,
            "topology": topology,
            "features": features,
            "pricing": pricing,
            "alerting": alerting,
        },
        cost_data,
    )


def map_recommendation_report(
    report: RecommendationReport,
    *,
    source: RecommendationSource,
    include_remediation_steps: bool,
    max_recommendations: int,
) -> tuple[list[RecommendationItem], list[str]]:
    """Map domain recommendations into the HTTP response contract."""

    recommendations: list[RecommendationItem] = []
    for index, item in enumerate(report.recommendations[:max_recommendations], start=1):
        recommendations.append(
            RecommendationItem(
                recommendation_id=f"rec_{index:02d}_{_slugify(item.title)}",
                priority=_map_priority(item.priority),
                title=item.title,
                summary=item.description,
                rationale=item.impact_estimate,
                projected_impact=ProjectedImpact(
                    monthly_cost_delta_usd=_extract_currency_delta(item.impact_estimate),
                    performance_impact=(
                        "Low implementation effort; validate latency and relevance after rollout."
                        if item.effort == "low"
                        else "Moderate operational change; benchmark before production rollout."
                    ),
                    risk_reduction=(
                        "Addresses a cost or configuration inefficiency surfaced by the advisor."
                    ),
                ),
                remediation_steps=[
                    RemediationStep(
                        step_number=step_number,
                        action=step,
                        detail=step,
                        owner_hint="search-platform",
                    )
                    for step_number, step in enumerate(item.remediation_steps, start=1)
                ]
                if include_remediation_steps
                else [],
                prerequisites=[],
                tradeoffs=[f"Estimated effort: {item.effort}."],
            )
        )

    notes = [
        f"Estimated monthly savings: ${float(report.estimated_savings.get('monthly_usd', 0.0)):,.2f}.",
        f"Savings confidence: {report.estimated_savings.get('confidence', 'approximate')}",
    ]
    return recommendations, notes


def build_simulate_response(
    *,
    current_cost_model: CostModelResponse,
    proposed_cost_model: CostModelResponse | None,
    current_estimate: ScenarioCostEstimate,
    proposed_estimate: ScenarioCostEstimate,
    notes: list[str],
    projected_impact: SimulationImpact,
) -> SimulateResponse:
    """Create the standard simulation response payload."""

    monthly_delta = round(proposed_estimate.monthly_total - current_estimate.monthly_total, 2)
    monthly_savings_percent = (
        round((abs(monthly_delta) / current_estimate.monthly_total) * 100, 2)
        if current_estimate.monthly_total and monthly_delta < 0
        else None
    )
    return SimulateResponse(
        request_id=f"sim_{uuid4().hex}",
        status="completed",
        generated_at=datetime.now(timezone.utc),
        comparison=ApiCostComparison(
            current_estimate=current_estimate,
            proposed_estimate=proposed_estimate,
            monthly_delta=monthly_delta,
            monthly_savings_percent=monthly_savings_percent,
        ),
        projected_impact=projected_impact,
        current_cost_model=current_cost_model,
        proposed_cost_model=proposed_cost_model,
        notes=notes,
    )


def scenario_estimate_from_cost_model(
    cost_model: CostModelResponse,
    *,
    pricing_model: PricingModelOption,
    currency: str,
) -> ScenarioCostEstimate:
    """Extract a scenario estimate for the selected pricing model."""

    feature_items = {
        item.feature_name: item.estimated_monthly_cost_usd
        for item in cost_model.breakdown.features.line_items
    }
    if pricing_model == PricingModelOption.SERVERLESS:
        compute_monthly = (
            cost_model.breakdown.serverless.estimated_monthly_cost_usd
            if cost_model.breakdown.serverless is not None
            else 0.0
        )
        monthly_total = cost_model.breakdown.serverless_total_monthly_cost_usd
    else:
        compute_monthly = (
            cost_model.breakdown.dedicated.estimated_monthly_cost_usd
            if cost_model.breakdown.dedicated is not None
            else 0.0
        )
        monthly_total = cost_model.breakdown.dedicated_total_monthly_cost_usd

    return ScenarioCostEstimate(
        currency=currency,
        monthly_total=monthly_total,
        compute_monthly=compute_monthly,
        semantic_monthly=feature_items.get("semantic_ranker", 0.0),
        vector_monthly=feature_items.get("vector_storage", 0.0),
        enrichment_monthly=feature_items.get("ai_enrichment", 0.0),
    )


def infer_simulation_impact(
    proposed_changes: list[SimulationChange],
) -> SimulationImpact:
    """Create a lightweight narrative for scenario simulations."""

    lowered_capacity = any(
        change.attribute in {"replica_count", "partition_count"}
        and _to_float(change.proposed_value) < _to_float(change.current_value)
        for change in proposed_changes
    )
    if lowered_capacity:
        capacity_risk = "Lower capacity can increase latency or indexing backlog during bursts; validate before rollout."
        latency_expectation = "Expect unchanged baseline latency if headroom remains, but peak latency could rise under load spikes."
    else:
        capacity_risk = "No immediate capacity reduction detected; operational risk is primarily configuration correctness."
        latency_expectation = "Latency should remain similar unless the proposed change alters query complexity or feature usage."
    return SimulationImpact(
        capacity_risk=capacity_risk,
        latency_expectation=latency_expectation,
        operational_notes=[change.rationale for change in proposed_changes],
    )


def compare_cost_model_options(
    cost_model: CostModelResponse,
    *,
    currency: str,
) -> tuple[ScenarioCostEstimate, ScenarioCostEstimate]:
    """Create a dedicated-versus-serverless view from a direct cost-model request."""

    current_model = (
        PricingModelOption.DEDICATED
        if cost_model.breakdown.dedicated is not None
        else PricingModelOption.SERVERLESS
    )
    proposed_model = (
        PricingModelOption.SERVERLESS
        if cost_model.breakdown.serverless is not None
        else current_model
    )
    return (
        scenario_estimate_from_cost_model(cost_model, pricing_model=current_model, currency=currency),
        scenario_estimate_from_cost_model(cost_model, pricing_model=proposed_model, currency=currency),
    )


def _map_analysis_finding(finding: Any, index: int) -> ApiAnalysisFinding:
    primary_details = finding.evidence or {}
    return ApiAnalysisFinding(
        finding_id=f"{finding.category}-{index}",
        category=_map_finding_category(finding.category),
        severity=SeverityLevel(finding.severity),
        title=finding.title,
        description=finding.description,
        evidence=[_map_evidence(primary_details, finding.impact)] if primary_details else [],
        impacted_resources=_infer_impacted_resources(finding.category),
        potential_monthly_cost_impact_usd=_to_optional_float(
            primary_details.get("potential_monthly_cost_impact_usd")
        ),
        recommendation_hint=(
            str(primary_details.get("recommendation_hint"))
            if primary_details.get("recommendation_hint") is not None
            else None
        ),
    )


def _map_evidence(details: dict[str, Any], explanation: str) -> ApiFindingEvidence:
    return ApiFindingEvidence(
        metric=str(details.get("metric", "analysis_signal")),
        observed_value=details.get("observed_value", explanation),
        expected_range=(
            str(details.get("expected_range")) if details.get("expected_range") is not None else None
        ),
        explanation=explanation,
    )


def _map_finding_category(value: str) -> FindingCategory:
    return {
        "provisioning": FindingCategory.CAPACITY,
        "sku": FindingCategory.COST,
        "feature_usage": FindingCategory.FEATURE_USAGE,
    }.get(value, FindingCategory.COST)


def _infer_impacted_resources(category: str) -> list[str]:
    return {
        "provisioning": ["capacity", "monthly_cost"],
        "sku": ["pricing_model", "monthly_cost"],
        "feature_usage": ["feature_configuration", "monthly_cost"],
    }.get(category, ["service"])


def _build_feature_list(configuration: SearchServiceConfiguration) -> list[SearchFeature]:
    features: list[SearchFeature] = []
    if configuration.features.ai_enrichment_enabled:
        features.append(SearchFeature.AI_ENRICHMENT)
    if configuration.features.knowledge_store_enabled:
        features.append(SearchFeature.KNOWLEDGE_STORE)
    if configuration.features.semantic_ranker_enabled:
        features.append(SearchFeature.SEMANTIC_RANKER)
    if configuration.features.vector_search_enabled:
        features.append(SearchFeature.VECTOR_SEARCH)
    if configuration.index_topology.indexer_count > 0:
        features.append(SearchFeature.INDEXERS)
    if configuration.security.private_endpoint_enabled:
        features.append(SearchFeature.PRIVATE_ENDPOINTS)
    if configuration.security.managed_identity_enabled:
        features.append(SearchFeature.MANAGED_IDENTITY)
    if configuration.capacity.zone_redundancy_enabled:
        features.append(SearchFeature.AVAILABILITY_ZONES)
    return features


def _estimate_monthly_queries(metrics: SearchWorkloadMetrics | None) -> int:
    if metrics is None:
        return 0
    return metrics.query.monthly_query_volume


def _build_cost_data(cost_model_response: CostModelResponse | None) -> dict[str, Any]:
    if cost_model_response is None:
        return {"potential_monthly_savings": 0.0, "scenario_comparison": {"confidence": "limited"}}

    difference = abs(cost_model_response.comparison.monthly_difference_usd)
    lower_cost_option = cost_model_response.comparison.lower_cost_option
    return {
        "potential_monthly_savings": difference,
        "scenario_comparison": {
            "recommended_monthly_savings": difference,
            "recommended_annual_savings": round(difference * 12, 2),
            "confidence": "approximate",
            "dedicated_monthly_savings": difference
            if lower_cost_option == PricingModelOption.DEDICATED
            else 0.0,
            "serverless_monthly_savings": difference
            if lower_cost_option == PricingModelOption.SERVERLESS
            else 0.0,
        },
    }


def _map_api_sku(value: str) -> SearchSku:
    return API_TO_DOMAIN_SKU.get(value.lower(), SearchSku.S1)


def _map_priority(value: str) -> RecommendationPriority:
    return {
        "high": RecommendationPriority.HIGH,
        "medium": RecommendationPriority.MEDIUM,
        "low": RecommendationPriority.LOW,
    }.get(value, RecommendationPriority.MEDIUM)


def _slugify(value: str) -> str:
    return "-".join(part for part in value.lower().replace("/", " ").split() if part)


def _extract_currency_delta(value: str) -> float | None:
    for token in value.replace(",", "").split():
        if token.startswith("$"):
            try:
                return -abs(float(token.lstrip("$")))
            except ValueError:
                return None
    return None


def _to_optional_float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
