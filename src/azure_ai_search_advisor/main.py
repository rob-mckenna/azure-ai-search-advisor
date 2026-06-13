"""Application entrypoint for Azure AI Search Advisor."""

import os
from collections.abc import Mapping

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from azure_ai_search_advisor import __version__
from azure_ai_search_advisor.api.middleware import CorrelationIdMiddleware
from azure_ai_search_advisor.api.routers import analyze, discover, health, history, recommend, simulate, tenant
from azure_ai_search_advisor.api.schemas import ErrorDetail, ErrorResponse
from azure_ai_search_advisor.core.logging import configure_logging


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
    configure_logging()
    app = FastAPI(
        title="Azure AI Search Advisor",
        version=__version__,
        description=(
            "Analyzes Azure AI Search workloads to detect inefficiencies, model costs, "
            "and generate actionable optimization recommendations. Supports both standalone "
            "analysis and end-to-end advisory pipelines."
        ),
        openapi_tags=[
            {
                "name": "analysis",
                "description": "Analyze Azure AI Search configurations for provisioning, SKU, and feature inefficiencies.",
            },
            {
                "name": "recommendations",
                "description": "Generate prioritized optimization recommendations with remediation steps.",
            },
            {
                "name": "simulation",
                "description": "Model cost scenarios comparing dedicated vs serverless pricing.",
            },
            {
                "name": "health",
                "description": "Operational health and readiness probe endpoints.",
            },
            {
                "name": "discovery",
                "description": "Discover and analyze live Azure AI Search services using Azure credentials.",
            },
            {
                "name": "history",
                "description": "Retrieve stored analysis history and trend data for Azure AI Search services.",
            },
            {
                "name": "tenancy",
                "description": "Manage tenant membership and tenant-scoped Azure AI Search service registrations.",
            },
        ],
    )

    app.add_middleware(CorrelationIdMiddleware)

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
    app.include_router(discover.router)
    app.include_router(history.router)
    app.include_router(recommend.router)
    app.include_router(simulate.router)
    app.include_router(health.router)
    app.include_router(tenant.router)

    # CORS — allow the React dev server and configured origins
    cors_origins = os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()
