"""Application entrypoint for Azure AI Search Advisor."""

from collections.abc import Mapping

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from azure_ai_search_advisor import __version__
from azure_ai_search_advisor.api.routers import analyze, health, recommend, simulate
from azure_ai_search_advisor.api.schemas import ErrorDetail, ErrorResponse


def _json_error_response(
    *,
    status_code: int,
    error_code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Create a standardized JSON error response."""

    payload = ErrorResponse(
        error_code=error_code,
        message=message,
        status_code=status_code,
        details=details or [],
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers=dict(headers or {}),
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Azure AI Search Advisor",
        version=__version__,
        description="Scaffolded API for Azure AI Search optimization analysis and recommendations.",
        openapi_tags=[
            {"name": "analysis", "description": "Workload analysis endpoints."},
            {"name": "recommendations", "description": "Recommendation generation endpoints."},
            {"name": "simulation", "description": "Scenario and pricing simulation endpoints."},
            {"name": "health", "description": "Operational health endpoints."},
        ],
    )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Return validation failures in the shared error format."""

        _ = request
        details = [
            ErrorDetail(
                path=[str(item) for item in error["loc"]],
                message=error["msg"],
                error_type=error["type"],
            )
            for error in exc.errors()
        ]
        return _json_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="validation_error",
            message="The request payload failed schema validation.",
            details=details,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Return HTTP errors in the shared error format."""

        _ = request
        return _json_error_response(
            status_code=exc.status_code,
            error_code="http_error",
            message=str(exc.detail),
            headers=exc.headers,
        )

    app.include_router(analyze.router)
    app.include_router(recommend.router)
    app.include_router(simulate.router)
    app.include_router(health.router)

    return app


app = create_app()
