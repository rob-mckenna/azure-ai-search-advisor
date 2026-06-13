"""Analyze endpoint scaffold."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import ValidationError

from azure_ai_search_advisor.analysis.service import AnalysisRequest, AnalysisService
from azure_ai_search_advisor.api.auth import CurrentUser, get_current_user
from azure_ai_search_advisor.api.dependencies import get_analysis_service, get_ingestion_service
from azure_ai_search_advisor.api.rate_limit import check_rate_limit
from azure_ai_search_advisor.api.schemas import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from azure_ai_search_advisor.api.service_adapters import build_snapshot_payload, map_analysis_result_to_response
from azure_ai_search_advisor.ingestion.service import IngestionService

router = APIRouter(
    prefix="/analyze",
    tags=["analysis"],
    dependencies=[Depends(check_rate_limit)],
)

ANALYZE_REQUEST_EXAMPLES = {
    "right-sizing": {
        "summary": "Dedicated service with potential replica over-provisioning",
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
                "notes": ["Replica utilization is believed to be low overnight."],
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
        },
    }
}


@router.post(
    "",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze an Azure AI Search workload",
    description=(
        "Accepts current Azure AI Search configuration and workload metrics, then "
        "returns structured findings that highlight inefficiencies, risks, and "
        "potential optimization opportunities."
    ),
    response_description="Structured analysis findings for the submitted workload.",
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
def analyze_search_configuration(
    request: Annotated[
        AnalyzeRequest,
        Body(openapi_examples=ANALYZE_REQUEST_EXAMPLES),
    ],
    current_user: CurrentUser = Depends(get_current_user),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> AnalyzeResponse:
    """Analyze an Azure AI Search workload."""

    _ = current_user
    try:
        snapshot = ingestion_service.ingest_payload(
            build_snapshot_payload(request.configuration, request.metrics)
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Input validation failed during ingestion: {exc}",
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest the submitted workload payload.",
        ) from exc

    try:
        result = analysis_service.analyze(
            AnalysisRequest(
                configuration=snapshot.configuration,
                metrics=snapshot.metrics,
            )
        )
        return map_analysis_result_to_response(result)
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis service failed to process the validated workload.",
        ) from exc
