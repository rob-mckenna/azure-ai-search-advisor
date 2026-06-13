"""Cost modeling service scaffold."""

from __future__ import annotations

from azure_ai_search_advisor.cost_modeling.feature_costs import estimate_feature_costs
from azure_ai_search_advisor.cost_modeling.search_units import estimate_search_unit_cost
from azure_ai_search_advisor.cost_modeling.serverless_pricing import estimate_serverless_cost
from azure_ai_search_advisor.models.cost_models import (
    CostBreakdown,
    CostComparison,
    CostModelRequest,
    CostModelResponse,
    FeatureCostInput,
    PricingModelOption,
)


class CostModelingService:
    """Calculates pricing scenarios for Azure AI Search workloads."""

    def simulate(self, request: CostModelRequest) -> CostModelResponse:
        """Estimate dedicated, serverless, and add-on costs for a workload."""
        dedicated_estimate = (
            estimate_search_unit_cost(request.dedicated_search)
            if request.dedicated_search is not None
            else None
        )
        serverless_estimate = (
            estimate_serverless_cost(request.serverless_search)
            if request.serverless_search is not None
            else None
        )
        feature_estimate = estimate_feature_costs(request.feature_costs or FeatureCostInput())

        dedicated_total = round(
            (dedicated_estimate.estimated_monthly_cost_usd if dedicated_estimate else 0.0)
            + feature_estimate.estimated_monthly_cost_usd,
            2,
        )
        serverless_total = round(
            (serverless_estimate.estimated_monthly_cost_usd if serverless_estimate else 0.0)
            + feature_estimate.estimated_monthly_cost_usd,
            2,
        )
        comparison_notes = self._build_comparison_notes(
            dedicated_total,
            serverless_total,
            has_dedicated_model=dedicated_estimate is not None,
            has_serverless_model=serverless_estimate is not None,
        )

        breakdown = CostBreakdown(
            dedicated=dedicated_estimate,
            serverless=serverless_estimate,
            features=feature_estimate,
            dedicated_total_monthly_cost_usd=dedicated_total,
            serverless_total_monthly_cost_usd=serverless_total,
            assumptions=[
                "Feature add-on estimates are included in both dedicated and serverless totals to support a like-for-like comparison.",
                "Dedicated estimates use provisioned search units, while serverless estimates use query-driven billable compute units.",
            ],
        )
        comparison = self.compare_options(
            dedicated_total,
            serverless_total,
            has_dedicated_model=dedicated_estimate is not None,
            has_serverless_model=serverless_estimate is not None,
        )

        return CostModelResponse(
            breakdown=breakdown,
            comparison=comparison,
            notes=comparison_notes,
        )

    def compare_options(
        self,
        dedicated_total_monthly_cost_usd: float,
        serverless_total_monthly_cost_usd: float,
        *,
        has_dedicated_model: bool,
        has_serverless_model: bool,
    ) -> CostComparison:
        """Compare dedicated and serverless monthly totals."""
        monthly_difference_usd = round(
            dedicated_total_monthly_cost_usd - serverless_total_monthly_cost_usd,
            2,
        )

        lower_cost_option = None
        notes = self._build_comparison_notes(
            dedicated_total_monthly_cost_usd,
            serverless_total_monthly_cost_usd,
            has_dedicated_model=has_dedicated_model,
            has_serverless_model=has_serverless_model,
        )
        if not (has_dedicated_model and has_serverless_model):
            notes.append(
                "Comparison is partial because one pricing model input is missing; the opposite total reflects only shared feature add-ons."
            )
        elif dedicated_total_monthly_cost_usd < serverless_total_monthly_cost_usd:
            lower_cost_option = PricingModelOption.DEDICATED
        elif serverless_total_monthly_cost_usd < dedicated_total_monthly_cost_usd:
            lower_cost_option = PricingModelOption.SERVERLESS

        return CostComparison(
            dedicated_total_monthly_cost_usd=dedicated_total_monthly_cost_usd,
            serverless_total_monthly_cost_usd=serverless_total_monthly_cost_usd,
            monthly_difference_usd=monthly_difference_usd,
            lower_cost_option=lower_cost_option,
            notes=notes,
        )

    def _build_comparison_notes(
        self,
        dedicated_total_monthly_cost_usd: float,
        serverless_total_monthly_cost_usd: float,
        *,
        has_dedicated_model: bool,
        has_serverless_model: bool,
    ) -> list[str]:
        notes = [
            "Comparison is cost-only and excludes SLA, migration effort, latency targets, reservations, and regional pricing differences.",
        ]
        if has_dedicated_model and has_serverless_model:
            if dedicated_total_monthly_cost_usd < serverless_total_monthly_cost_usd:
                notes.append(
                    "Dedicated is estimated to be cheaper by "
                    f"${serverless_total_monthly_cost_usd - dedicated_total_monthly_cost_usd:.2f} per month."
                )
            elif serverless_total_monthly_cost_usd < dedicated_total_monthly_cost_usd:
                notes.append(
                    "Serverless is estimated to be cheaper by "
                    f"${dedicated_total_monthly_cost_usd - serverless_total_monthly_cost_usd:.2f} per month."
                )
            else:
                notes.append("Dedicated and serverless are estimated to have the same monthly cost.")
        return notes
