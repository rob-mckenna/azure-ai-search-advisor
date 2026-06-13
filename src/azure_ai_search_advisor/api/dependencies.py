"""Dependency providers for API routes."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status

from azure_ai_search_advisor.analysis.service import AnalysisService
from azure_ai_search_advisor.api.auth import CurrentUser, get_current_user, is_auth_enabled
from azure_ai_search_advisor.api.cache import ResponseCache
from azure_ai_search_advisor.core.tenancy import TenantContext, get_tenant_context
from azure_ai_search_advisor.cost_modeling.service import CostModelingService
from azure_ai_search_advisor.ingestion.live_ingestion_service import LiveIngestionService
from azure_ai_search_advisor.ingestion.service import IngestionService
from azure_ai_search_advisor.repositories.tenant_db import TenantDbRepository
from azure_ai_search_advisor.repositories.history_service import HistoryService
from azure_ai_search_advisor.recommendations.service import RecommendationService


@lru_cache(maxsize=1)
def get_ingestion_service() -> IngestionService:
    """Provide the ingestion service dependency."""

    return IngestionService()


@lru_cache(maxsize=1)
def get_analysis_service() -> AnalysisService:
    """Provide the analysis service dependency."""

    return AnalysisService()


@lru_cache(maxsize=1)
def get_recommendation_service() -> RecommendationService:
    """Provide the recommendation service dependency."""

    return RecommendationService()


@lru_cache(maxsize=1)
def get_cost_modeling_service() -> CostModelingService:
    """Provide the cost modeling service dependency."""

    return CostModelingService()


@lru_cache(maxsize=1)
def get_live_ingestion_service() -> LiveIngestionService:
    """Provide the live Azure ingestion service dependency."""

    return LiveIngestionService()


@lru_cache(maxsize=1)
def get_response_cache() -> ResponseCache:
    """Provide the shared response cache dependency."""

    return ResponseCache.from_env()


def get_history_service() -> HistoryService:
    """Provide the history service dependency."""

    return HistoryService()


def get_tenant_db() -> TenantDbRepository:
    """Provide the tenant repository dependency."""

    return TenantDbRepository()


def get_tenant(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    tenant_db: TenantDbRepository = Depends(get_tenant_db),
) -> TenantContext:
    """Resolve and cache the current tenant context."""

    cached_context = getattr(request.state, "tenant_context", None)
    if cached_context is not None:
        return cached_context

    try:
        tenant_context = get_tenant_context(
            current_user,
            tenant_db=tenant_db,
            allow_local_fallback=not is_auth_enabled(),
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant is associated with the authenticated user.",
        ) from exc

    request.state.tenant_context = tenant_context
    return tenant_context
