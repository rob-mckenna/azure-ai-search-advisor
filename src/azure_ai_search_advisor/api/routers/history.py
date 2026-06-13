"""History API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from azure_ai_search_advisor.api.dependencies import get_history_service, get_tenant
from azure_ai_search_advisor.api.rate_limit import check_rate_limit
from azure_ai_search_advisor.api.schemas import (
    ServiceHistoryResponse,
    ServiceHistoryTrendsResponse,
)
from azure_ai_search_advisor.core.tenancy import TenantContext
from azure_ai_search_advisor.repositories.history_service import HistoryService

router = APIRouter(
    prefix="/history",
    tags=["history"],
    dependencies=[Depends(check_rate_limit)],
)


@router.get(
    "/{service_name}",
    response_model=ServiceHistoryResponse,
    summary="Get stored analysis history for a service",
)
def get_service_history(
    service_name: str,
    days: int = Query(default=30, ge=1, le=3650),
    limit: int = Query(default=50, ge=1, le=500),
    tenant_context: TenantContext = Depends(get_tenant),
    history_service: HistoryService = Depends(get_history_service),
) -> ServiceHistoryResponse:
    """Return stored history summaries for the requested service."""

    return ServiceHistoryResponse(
        service_name=service_name,
        days=days,
        limit=limit,
        runs=history_service.get_history(
            service_name,
            tenant_id=str(tenant_context.current_tenant.id),
            days=days,
            limit=limit,
        ),
    )


@router.get(
    "/{service_name}/trends",
    response_model=ServiceHistoryTrendsResponse,
    summary="Get stored trend data for a service",
)
def get_service_history_trends(
    service_name: str,
    days: int = Query(default=90, ge=1, le=3650),
    limit: int = Query(default=50, ge=1, le=500),
    tenant_context: TenantContext = Depends(get_tenant),
    history_service: HistoryService = Depends(get_history_service),
) -> ServiceHistoryTrendsResponse:
    """Return finding and cost trends for the requested service."""

    trends = history_service.get_trends(
        service_name,
        tenant_id=str(tenant_context.current_tenant.id),
        days=days,
        limit=limit,
    )
    return ServiceHistoryTrendsResponse(
        service_name=service_name,
        days=days,
        limit=limit,
        **trends,
    )
