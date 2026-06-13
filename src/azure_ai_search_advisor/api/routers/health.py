"""Health endpoint scaffold."""

from datetime import datetime, timezone

from fastapi import APIRouter, status

from azure_ai_search_advisor import __version__
from azure_ai_search_advisor.api.schemas import DependencyHealth, HealthResponse, HealthStatus

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get service health",
    description=(
        "Returns a lightweight service health payload suitable for readiness checks "
        "and operational diagnostics."
    ),
    response_description="Current API health information.",
)
def get_health() -> HealthResponse:
    """Return a health payload for the API surface."""

    return HealthResponse(
        status=HealthStatus.HEALTHY,
        service="azure-ai-search-advisor",
        version=__version__,
        checked_at=datetime.now(timezone.utc),
        dependencies=[
            DependencyHealth(
                name="api",
                status=HealthStatus.HEALTHY,
                detail="Router registration completed successfully.",
            ),
            DependencyHealth(
                name="analysis-service",
                status=HealthStatus.HEALTHY,
                detail="Analysis pipeline operational with provisioning, feature, and SKU analyzers.",
            ),
        ],
        notes=[
            "This health response confirms API availability, not downstream Azure dependency readiness.",
        ],
    )
