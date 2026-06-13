"""Live Azure AI Search discovery and analysis endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from azure_ai_search_advisor.analysis.service import AnalysisRequest, AnalysisService
from azure_ai_search_advisor.api.dependencies import (
    get_analysis_service,
    get_history_service,
    get_live_ingestion_service,
    get_tenant,
    get_tenant_db,
)
from azure_ai_search_advisor.api.schemas import AnalyzeResponse, DiscoverResponse, DiscoveredServiceSummary, ErrorResponse
from azure_ai_search_advisor.api.service_adapters import map_analysis_result_to_response_with_notes
from azure_ai_search_advisor.core.tenancy import ServiceRegistration, TenantContext
from azure_ai_search_advisor.core.resilience import CircuitBreakerOpenError
from azure_ai_search_advisor.ingestion.live_exceptions import (
    AzureCredentialsUnavailableError,
    AzureLiveIngestionError,
    AzureSearchServiceNotFoundError,
)
from azure_ai_search_advisor.ingestion.live_ingestion_service import LiveIngestionService
from azure_ai_search_advisor.repositories.history_service import HistoryService
from azure_ai_search_advisor.repositories.tenant_db import TenantDbRepository

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
    tenant_context: TenantContext = Depends(get_tenant),
    live_ingestion_service: LiveIngestionService = Depends(get_live_ingestion_service),
    tenant_db: TenantDbRepository = Depends(get_tenant_db),
    subscription_id: Annotated[str | None, Query(description="Optional Azure subscription filter.")] = None,
    resource_group: Annotated[str | None, Query(description="Optional Azure resource group filter.")] = None,
) -> DiscoverResponse:
    """List Azure AI Search services visible to the current credential."""

    registrations = _filter_registrations(
        tenant_db.list_services(tenant_context.current_tenant.id),
        subscription_id=subscription_id,
        resource_group=resource_group,
    )
    if tenant_context.membership is not None and not registrations:
        return DiscoverResponse(
            services=[],
            notes=["No Azure AI Search services are registered for the current tenant."],
        )

    try:
        services = live_ingestion_service.discover_services(
            subscription_id=subscription_id,
            resource_group=resource_group,
        )
    except CircuitBreakerOpenError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
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

    if registrations:
        services = _scope_discovered_services(services, registrations)

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
    tenant_context: TenantContext = Depends(get_tenant),
    live_ingestion_service: LiveIngestionService = Depends(get_live_ingestion_service),
    analysis_service: AnalysisService = Depends(get_analysis_service),
    history_service: HistoryService = Depends(get_history_service),
    tenant_db: TenantDbRepository = Depends(get_tenant_db),
    subscription_id: Annotated[str | None, Query(description="Optional Azure subscription filter.")] = None,
    resource_group: Annotated[str | None, Query(description="Optional Azure resource group filter.")] = None,
) -> AnalyzeResponse:
    """Discover, ingest, and analyze a live Azure AI Search service."""

    if not tenant_context.can("services:analyze"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The current tenant role does not allow live analysis.",
        )

    try:
        registrations = _filter_registrations(
            tenant_db.list_services(tenant_context.current_tenant.id),
            subscription_id=subscription_id,
            resource_group=resource_group,
            service_name=service_name,
        )
        resolved_subscription_id: str | None = None
        resolved_resource_group: str | None = None

        if registrations:
            if len(registrations) > 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Multiple registered Azure AI Search services named '{service_name}' were found. "
                        "Specify subscription_id and resource_group to disambiguate."
                    ),
                )
            resolved_registration = registrations[0]
            resolved_subscription_id = resolved_registration.subscription_id
            resolved_resource_group = resolved_registration.resource_group
            snapshot = live_ingestion_service.ingest_live_service(
                subscription_id=resolved_subscription_id,
                resource_group=resolved_resource_group,
                service_name=resolved_registration.service_name,
            )
        elif tenant_context.membership is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No registered Azure AI Search service named '{service_name}' was found for the current tenant.",
            )
        elif subscription_id and resource_group:
            resolved_subscription_id = subscription_id
            resolved_resource_group = resource_group
            snapshot = live_ingestion_service.ingest_live_service(
                subscription_id=resolved_subscription_id,
                resource_group=resolved_resource_group,
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
            resolved_subscription_id = resolved_service.subscription_id
            resolved_resource_group = resolved_service.resource_group
            snapshot = live_ingestion_service.ingest_live_service(
                subscription_id=resolved_service.subscription_id,
                resource_group=resolved_service.resource_group,
                service_name=service_name,
            )
    except CircuitBreakerOpenError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
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
    history_service.record_analysis(
        snapshot.configuration.service_name,
        map_analysis_result_to_response_with_notes(result, extra_notes=snapshot.notes),
        None,
        [],
        tenant_id=str(tenant_context.current_tenant.id),
        subscription_id=resolved_subscription_id or snapshot.configuration.subscription_id,
        resource_group=resolved_resource_group or snapshot.configuration.resource_group,
    )
    return map_analysis_result_to_response_with_notes(result, extra_notes=snapshot.notes)


def _filter_registrations(
    registrations: list[ServiceRegistration],
    *,
    subscription_id: str | None = None,
    resource_group: str | None = None,
    service_name: str | None = None,
) -> list[ServiceRegistration]:
    return [
        registration
        for registration in registrations
        if (subscription_id is None or registration.subscription_id == subscription_id)
        and (resource_group is None or registration.resource_group == resource_group)
        and (service_name is None or registration.service_name == service_name)
    ]


def _scope_discovered_services(
    services: list,
    registrations: list[ServiceRegistration],
) -> list:
    registered_keys = {
        (registration.subscription_id, registration.resource_group, registration.service_name)
        for registration in registrations
    }
    return [
        service
        for service in services
        if (service.subscription_id, service.resource_group, service.name) in registered_keys
    ]
