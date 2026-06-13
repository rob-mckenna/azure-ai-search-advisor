"""Live Azure AI Search discovery and analysis endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from azure_ai_search_advisor.analysis.service import AnalysisRequest, AnalysisService
from azure_ai_search_advisor.api.auth import CurrentUser, get_current_user
from azure_ai_search_advisor.api.dependencies import get_analysis_service, get_live_ingestion_service
from azure_ai_search_advisor.api.schemas import AnalyzeResponse, DiscoverResponse, DiscoveredServiceSummary, ErrorResponse
from azure_ai_search_advisor.api.service_adapters import map_analysis_result_to_response_with_notes
from azure_ai_search_advisor.ingestion.live_exceptions import (
    AzureCredentialsUnavailableError,
    AzureLiveIngestionError,
    AzureSearchServiceNotFoundError,
)
from azure_ai_search_advisor.ingestion.live_ingestion_service import LiveIngestionService

router = APIRouter(prefix="/discover", tags=["discovery"])


@router.get(
    "",
    response_model=DiscoverResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover live Azure AI Search services",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "Azure credentials are not configured for live discovery.",
        }
    },
)
def discover_search_services(
    current_user: CurrentUser = Depends(get_current_user),
    live_ingestion_service: LiveIngestionService = Depends(get_live_ingestion_service),
    subscription_id: Annotated[str | None, Query(description="Optional Azure subscription filter.")] = None,
    resource_group: Annotated[str | None, Query(description="Optional Azure resource group filter.")] = None,
) -> DiscoverResponse:
    """List Azure AI Search services visible to the current credential."""

    _ = current_user
    try:
        services = live_ingestion_service.discover_services(
            subscription_id=subscription_id,
            resource_group=resource_group,
        )
    except AzureCredentialsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except AzureLiveIngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return DiscoverResponse(
        services=[
            DiscoveredServiceSummary(
                name=service.name,
                resource_group=service.resource_group,
                subscription_id=service.subscription_id,
                location=service.location,
                sku=service.sku,
                replica_count=service.replica_count,
                partition_count=service.partition_count,
            )
            for service in services
        ],
        notes=[],
    )


@router.post(
    "/{service_name}/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a live Azure AI Search service",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "The requested Azure AI Search service could not be resolved.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "The requested service name matched multiple Azure resources.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "Azure credentials are not configured for live analysis.",
        },
    },
)
def analyze_live_search_service(
    service_name: str,
    current_user: CurrentUser = Depends(get_current_user),
    live_ingestion_service: LiveIngestionService = Depends(get_live_ingestion_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    subscription_id: Annotated[str | None, Query(description="Optional Azure subscription filter.")] = None,
    resource_group: Annotated[str | None, Query(description="Optional Azure resource group filter.")] = None,
) -> AnalyzeResponse:
    """Discover, ingest, and analyze a live Azure AI Search service."""

    _ = current_user

    try:
        if subscription_id and resource_group:
            snapshot = live_ingestion_service.ingest_live_service(
                subscription_id=subscription_id,
                resource_group=resource_group,
                service_name=service_name,
            )
        else:
            services = [
                service
                for service in live_ingestion_service.discover_services(
                    subscription_id=subscription_id,
                    resource_group=resource_group,
                )
                if service.name == service_name
            ]
            if not services:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No Azure AI Search service named '{service_name}' was found.",
                )
            if len(services) > 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Multiple Azure AI Search services named '{service_name}' were found. "
                        "Specify subscription_id and resource_group to disambiguate."
                    ),
                )
            resolved_service = services[0]
            snapshot = live_ingestion_service.ingest_live_service(
                subscription_id=resolved_service.subscription_id,
                resource_group=resolved_service.resource_group,
                service_name=service_name,
            )
    except AzureCredentialsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except AzureSearchServiceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AzureLiveIngestionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    result = analysis_service.analyze(
        AnalysisRequest(
            configuration=snapshot.configuration,
            metrics=snapshot.metrics,
        )
    )
    return map_analysis_result_to_response_with_notes(result, extra_notes=snapshot.notes)
