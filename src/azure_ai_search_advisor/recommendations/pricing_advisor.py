"""Pricing model recommendation scaffolds."""

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.models.recommendations import Recommendation


def generate_pricing_model_recommendations(
    analysis_findings: Mapping[str, Any],
    cost_data: Mapping[str, Any],
) -> list[Recommendation]:
    """Generate hosting model recommendations from pricing signals."""

    pricing = _as_mapping(analysis_findings.get("pricing"))
    service = _as_mapping(analysis_findings.get("service"))
    scenario_comparison = _as_mapping(cost_data.get("scenario_comparison"))
    recommendations: list[Recommendation] = []

    hosting_mode = str(service.get("hosting_mode", "dedicated"))

    # TODO: Replace scenario booleans with sustained utilization, burst, and SLA-aware scoring.
    if hosting_mode == "dedicated" and pricing.get("switch_to_serverless_candidate"):
        recommendations.append(
            Recommendation(
                title="Move bursty development workloads to serverless",
                description=(
                    "Current usage patterns show long idle periods and short bursts of activity. "
                    "A serverless deployment would align cost with actual consumption."
                ),
                category="pricing_model",
                priority="medium",
                impact_estimate=(
                    f"Cut monthly spend by about {_format_currency(scenario_comparison.get('serverless_monthly_savings', 0.0))} if burst patterns hold."
                ),
                effort="medium",
                remediation_steps=[
                    "Validate that workload latency, scale, and feature requirements are compatible with serverless.",
                    "Deploy a serverless test service and replay representative traffic.",
                    "Migrate non-production or intermittent workloads first, then monitor cost and latency.",
                ],
            )
        )

    # TODO: Add break-even modeling for sustained query volume, indexing cadence, and reserved capacity.
    if hosting_mode == "serverless" and pricing.get("switch_to_dedicated_candidate"):
        recommendations.append(
            Recommendation(
                title="Move sustained production traffic to dedicated pricing",
                description=(
                    "The workload is consistently active enough that consumption-based pricing is no "
                    "longer the lowest-cost option."
                ),
                category="pricing_model",
                priority="high",
                impact_estimate=(
                    f"Reduce monthly operating cost by roughly {_format_currency(scenario_comparison.get('dedicated_monthly_savings', 0.0))}."
                ),
                effort="high",
                remediation_steps=[
                    "Confirm sustained query and indexing demand over at least one full billing cycle.",
                    "Size the dedicated service for peak concurrency, storage, and availability requirements.",
                    "Plan the migration and cutover with rollback steps and KPI monitoring.",
                ],
            )
        )

    return recommendations


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _format_currency(value: Any) -> str:
    amount = float(value or 0.0)
    return f"${amount:,.0f}"
