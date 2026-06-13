"""Simulation endpoint scaffold."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from pydantic import ValidationError

from azure_ai_search_advisor.api.auth import CurrentUser, get_current_user
from azure_ai_search_advisor.api.cache import ResponseCache
from azure_ai_search_advisor.api.dependencies import get_cost_modeling_service, get_response_cache
from azure_ai_search_advisor.api.rate_limit import check_rate_limit
from azure_ai_search_advisor.api.schemas import ErrorResponse, SimulateRequest, SimulateResponse
from azure_ai_search_advisor.api.service_adapters import (
    apply_proposed_changes,
    build_cost_model_request,
    build_simulate_response,
    compare_cost_model_options,
    infer_simulation_impact,
    scenario_estimate_from_cost_model,
)
from azure_ai_search_advisor.cost_modeling.service import CostModelingService
from azure_ai_search_advisor.models import PricingModelOption

router = APIRouter(
    prefix="/simulate",
    tags=["simulation"],
    dependencies=[Depends(check_rate_limit)],
)

SIMULATE_REQUEST_EXAMPLES = {
    "reduce-replicas": {
        "summary": "Compare current capacity against a lower replica count",
        "value": {
            "current_configuration": {
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
            "proposed_changes": [
                {
                    "change_id": "reduce-replicas",
                    "target": "capacity",
                    "attribute": "replica_count",
                    "current_value": 3,
                    "proposed_value": 2,
                    "rationale": "Observed replica utilization is below 50% during sustained traffic.",
                }
            ],
            "assumptions": {
                "pricing_horizon_days": 30,
                "currency": "USD",
                "notes": ["Illustrative comparison without reserved capacity discounts."],
            },
        },
    },
    "direct-cost-model": {
        "summary": "Submit a direct cost model request",
        "value": {
            "cost_model_request": {
                "dedicated_search": {
                    "tier": "s1",
                    "replicas": 3,
                    "partitions": 2,
                    "months": 1.0
                },
                "serverless_search": {
                    "monthly_queries": 4300000,
                    "average_billable_compute_units_per_query": 1.25,
                    "months": 1.0
                },
                "feature_costs": {
                    "semantic_queries_per_month": 1200000,
                    "enrichment_transactions_per_month": 0,
                    "vector_index_storage_gb": 42.0,
                    "months": 1.0
                }
            },
            "assumptions": {
                "currency": "USD"
            }
        },
    },
}


@router.post(
    "",
    response_model=SimulateResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate cost impact of proposed changes",
    description=(
        "Accepts the current Azure AI Search configuration plus one or more proposed "
        "changes, then returns a current-versus-proposed cost comparison with "
        "narrative impact guidance."
    ),
    response_description="Current-versus-proposed scenario output.",
    responses={
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "The payload failed schema validation.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Unexpected API failure.",
        },
    },
)
def simulate_cost_and_capacity(
    request: Annotated[
        SimulateRequest,
        Body(openapi_examples=SIMULATE_REQUEST_EXAMPLES),
    ],
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    cost_modeling_service: CostModelingService = Depends(get_cost_modeling_service),
    response_cache: ResponseCache = Depends(get_response_cache),
) -> SimulateResponse:
    """Simulate cost and capacity scenarios for Azure AI Search."""

    _ = current_user
    cache_key = response_cache.build_key(request.model_dump(mode="json"))
    response.headers["X-Cache-Key"] = cache_key
    cached_response = response_cache.get(cache_key)
    if cached_response is not None:
        response.headers["X-Cache"] = "HIT"
        return cached_response

    try:
        if request.cost_model_request is not None:
            cost_model = cost_modeling_service.simulate(request.cost_model_request)
            current_estimate, proposed_estimate = compare_cost_model_options(
                cost_model,
                currency=request.assumptions.currency,
            )
            payload = build_simulate_response(
                current_cost_model=cost_model,
                proposed_cost_model=None,
                current_estimate=current_estimate,
                proposed_estimate=proposed_estimate,
                projected_impact=infer_simulation_impact([]),
                notes=request.assumptions.notes
                + [
                    "Compared dedicated and serverless pricing models from the submitted cost model request."
                ],
            )
            response_cache.set(cache_key, payload)
            response.headers["X-Cache"] = "MISS"
            return payload

        if request.current_configuration is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="current_configuration is required when cost_model_request is omitted.",
            )

        proposed_configuration = apply_proposed_changes(
            request.current_configuration,
            request.proposed_changes,
        )
        current_request = build_cost_model_request(
            request.current_configuration,
            request.current_metrics,
            pricing_horizon_days=request.assumptions.pricing_horizon_days,
        )
        proposed_request = build_cost_model_request(
            proposed_configuration,
            request.current_metrics,
            pricing_horizon_days=request.assumptions.pricing_horizon_days,
        )
        current_cost_model = cost_modeling_service.simulate(current_request)
        proposed_cost_model = cost_modeling_service.simulate(proposed_request)

        current_pricing_model = PricingModelOption(
            request.current_configuration.capacity.pricing_model.value
        )
        proposed_pricing_model = PricingModelOption(
            proposed_configuration.capacity.pricing_model.value
        )
        current_estimate = scenario_estimate_from_cost_model(
            current_cost_model,
            pricing_model=current_pricing_model,
            currency=request.assumptions.currency,
        )
        proposed_estimate = scenario_estimate_from_cost_model(
            proposed_cost_model,
            pricing_model=proposed_pricing_model,
            currency=request.assumptions.currency,
        )
        payload = build_simulate_response(
            current_cost_model=current_cost_model,
            proposed_cost_model=proposed_cost_model,
            current_estimate=current_estimate,
            proposed_estimate=proposed_estimate,
            projected_impact=infer_simulation_impact(request.proposed_changes),
            notes=request.assumptions.notes
            + [f"Processed {len(request.proposed_changes)} proposed change(s)."],
        )
        response_cache.set(cache_key, payload)
        response.headers["X-Cache"] = "MISS"
        return payload
    except HTTPException:
        raise
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Simulation input could not be validated: {exc}",
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cost modeling service failed to simulate the requested scenario.",
        ) from exc
