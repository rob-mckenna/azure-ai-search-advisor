"""Recommend endpoint scaffold."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from pydantic import ValidationError

from azure_ai_search_advisor.analysis.service import AnalysisRequest, AnalysisService
from azure_ai_search_advisor.api.auth import CurrentUser, get_current_user
from azure_ai_search_advisor.api.dependencies import (
    get_analysis_service,
    get_cost_modeling_service,
    get_history_service,
    get_ingestion_service,
    get_recommendation_service,
    get_tenant_db,
)
from azure_ai_search_advisor.api.rate_limit import check_rate_limit
from azure_ai_search_advisor.api.schemas import (
    ErrorResponse,
    RecommendRequest,
    RecommendResponse,
    RecommendationSource,
)
from azure_ai_search_advisor.api.service_adapters import (
    build_cost_model_request,
    build_recommendation_inputs,
    build_snapshot_payload,
    map_analysis_result_to_response,
    map_recommendation_report,
)
from azure_ai_search_advisor.core.tenancy import get_tenant_context
from azure_ai_search_advisor.cost_modeling.service import CostModelingService
from azure_ai_search_advisor.ingestion.service import IngestionService
from azure_ai_search_advisor.repositories.history_service import HistoryService, compute_configuration_hash
from azure_ai_search_advisor.repositories.tenant_db import TenantDbRepository
from azure_ai_search_advisor.recommendations.service import RecommendationService

router = APIRouter(
    prefix="/recommend",
    tags=["recommendations"],
    dependencies=[Depends(check_rate_limit)],
)

RECOMMEND_REQUEST_EXAMPLES = {
    "from-analysis": {
        "summary": "Generate recommendations from analysis findings",
        "value": {
            "analysis": {
                "request_id": "anl_01JY0D5K5W2K2T6K06P2Q1CV8P",
                "status": "completed",
                "generated_at": "2026-06-12T15:00:00Z",
                "summary": {
                    "finding_count": 1,
                    "highest_severity": "high",
                    "optimization_themes": ["capacity_right_sizing"],
                    "overall_assessment": "The service appears oversized for sustained traffic.",
                },
                "findings": [
                    {
                        "finding_id": "capacity-low-utilization",
                        "category": "capacity",
                        "severity": "high",
                        "title": "Replica utilization is consistently low",
                        "description": "Sustained utilization is below the expected efficiency range.",
                        "evidence": [
                            {
                                "metric": "replica_utilization_percent",
                                "observed_value": 41.0,
                                "expected_range": "60-80% during peak traffic",
                                "explanation": "Low utilization suggests potential over-provisioning.",
                            }
                        ],
                        "impacted_resources": ["capacity", "cost"],
                        "potential_monthly_cost_impact_usd": 180.0,
                        "recommendation_hint": "Evaluate reducing replicas by one.",
                    }
                ],
                "notes": [],
            },
            "preferences": {
                "max_recommendations": 3,
                "prioritize_for": ["cost", "availability"],
                "include_remediation_steps": True,
            },
        },
    },
    "end-to-end": {
        "summary": "Generate recommendations directly from raw configuration",
        "value": {
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
                "notes": [],
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
            "preferences": {
                "max_recommendations": 5,
                "prioritize_for": ["cost", "performance"],
                "include_remediation_steps": True,
            },
        },
    },
}


@router.post(
    "",
    response_model=RecommendResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate workload recommendations",
    description=(
        "Accepts either prior analysis findings or raw Azure AI Search inputs for "
        "end-to-end recommendation generation, then returns prioritized remediation "
        "guidance with rationale and implementation steps."
    ),
    response_description="Prioritized recommendations for the submitted workload.",
    responses={
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "The payload failed schema or ingestion validation.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Unexpected API failure.",
        },
    },
)
def recommend_optimizations(
    request: Annotated[
        RecommendRequest,
        Body(openapi_examples=RECOMMEND_REQUEST_EXAMPLES),
    ],
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    tenant_db: TenantDbRepository = Depends(get_tenant_db),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    cost_modeling_service: CostModelingService = Depends(get_cost_modeling_service),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
    history_service: HistoryService = Depends(get_history_service),
) -> RecommendResponse:
    """Generate optimization recommendations for an Azure AI Search workload."""

    tenant_context = get_tenant_context(current_user, tenant_db=tenant_db, allow_local_fallback=True)
    source = (
        RecommendationSource.ANALYSIS_INPUT
        if request.analysis is not None and request.configuration is None
        else RecommendationSource.END_TO_END
    )
    analysis_response = request.analysis
    cost_model_response = None
    snapshot = None

    if request.configuration is not None and request.metrics is not None:
        try:
            snapshot = ingestion_service.ingest_payload(
                build_snapshot_payload(request.configuration, request.metrics)
            )
            analysis_result = analysis_service.analyze(
                AnalysisRequest(
                    configuration=snapshot.configuration,
                    metrics=snapshot.metrics,
                )
            )
            analysis_response = map_analysis_result_to_response(analysis_result)
            cost_model_response = cost_modeling_service.simulate(
                build_cost_model_request(
                    request.configuration,
                    request.metrics,
                )
            )
        except (ValidationError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unable to validate end-to-end recommendation input: {exc}",
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive API boundary
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate upstream analysis or cost data for recommendations.",
            ) from exc
    elif analysis_response is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either analysis or configuration plus metrics must be provided.",
        )

    try:
        analysis_findings, cost_data = build_recommendation_inputs(
            analysis_response,
            request.configuration,
            request.metrics,
            cost_model_response,
        )
        report = recommendation_service.recommend(analysis_findings, cost_data)
        recommendations, notes = map_recommendation_report(
            report,
            source=source,
            include_remediation_steps=request.preferences.include_remediation_steps,
            max_recommendations=request.preferences.max_recommendations,
        )
        response = RecommendResponse(
            request_id=f"rec_{uuid4().hex}",
            status="completed",
            generated_at=datetime.now(timezone.utc),
            source=source,
            recommendations=recommendations,
            summary=report.summary,
            notes=notes + (["Built from raw configuration and metrics."] if source == RecommendationSource.END_TO_END else []),
        )
        if source == RecommendationSource.END_TO_END and request.configuration is not None and snapshot is not None:
            background_tasks.add_task(
                history_service.record_analysis,
                request.configuration.service_name,
                analysis_response,
                cost_model_response,
                response.recommendations,
                tenant_id=str(tenant_context.current_tenant.id),
                subscription_id=snapshot.configuration.subscription_id,
                resource_group=snapshot.configuration.resource_group,
                configuration_hash=compute_configuration_hash(request.configuration),
            )
        return response
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recommendation service failed to generate a report.",
        ) from exc
