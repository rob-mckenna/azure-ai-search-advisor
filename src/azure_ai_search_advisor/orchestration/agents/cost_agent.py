"""Agent wrapper around the cost modeling domain service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.cost_modeling import CostModelingService
from azure_ai_search_advisor.models import CostComparison, CostModelRequest, CostModelResponse
from azure_ai_search_advisor.models import AzureSearchServiceSnapshot
from azure_ai_search_advisor.orchestration.config import AgentConfig
from azure_ai_search_advisor.orchestration.tools.cost_tools import (
    compare_pricing_models,
    estimate_cost,
)


class CostAgent:
    """Specialist agent for Azure AI Search cost scenario modeling."""

    def __init__(
        self,
        *,
        config: AgentConfig,
        service: CostModelingService | None = None,
    ) -> None:
        self.config = config
        self.service = service or CostModelingService()

    def estimate_cost(
        self,
        *,
        snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
        request: CostModelRequest | Mapping[str, Any] | None = None,
    ) -> CostModelResponse:
        """Estimate cost scenarios for the supplied workload."""
        return estimate_cost(snapshot=snapshot, request=request, service=self.service)

    def compare_pricing_models(
        self,
        *,
        snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
        request: CostModelRequest | Mapping[str, Any] | None = None,
    ) -> CostComparison:
        """Compare dedicated and serverless pricing models for the workload."""
        return compare_pricing_models(snapshot=snapshot, request=request, service=self.service)
