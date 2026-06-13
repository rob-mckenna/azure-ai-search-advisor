"""Right-sizing recommendation scaffolds."""

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.models.recommendations import Recommendation


def generate_rightsizing_recommendations(
    analysis_findings: Mapping[str, Any],
    cost_data: Mapping[str, Any],
) -> list[Recommendation]:
    """Generate right-sizing recommendations from topology findings and spend."""

    topology = _as_mapping(analysis_findings.get("topology"))
    service = _as_mapping(analysis_findings.get("service"))
    recommendations: list[Recommendation] = []

    # Future: Replace boolean gates with utilization thresholds and forecast-aware analysis.
    if topology.get("replica_overprovisioned"):
        current_replicas = int(service.get("replicas", 2))
        target_replicas = int(topology.get("suggested_replicas", max(current_replicas - 1, 1)))
        recommendations.append(
            Recommendation(
                title=f"Reduce replicas from {current_replicas} to {target_replicas}",
                description=(
                    "Replica capacity is higher than current query concurrency and availability "
                    "requirements demand. Downscaling releases unused search units without "
                    "changing the indexing topology."
                ),
                category="right_sizing",
                priority="high",
                impact_estimate=(
                    f"Lower monthly capacity spend by about {_format_currency(topology.get('estimated_monthly_savings', 0.0))}."
                ),
                effort="low",
                remediation_steps=[
                    "Validate the minimum replica count needed for SLA and query concurrency.",
                    "Apply the replica change in the Azure portal, ARM template, or IaC pipeline.",
                    "Monitor query latency and throttling for one full business cycle after the change.",
                ],
            )
        )

    # Future: Fold in index growth forecasts and ingestion burst patterns before finalizing targets.
    if topology.get("partition_overprovisioned"):
        current_partitions = int(service.get("partitions", 1))
        target_partitions = int(
            topology.get("suggested_partitions", max(current_partitions - 1, 1))
        )
        recommendations.append(
            Recommendation(
                title=f"Reduce partitions from {current_partitions} to {target_partitions}",
                description=(
                    "Storage and ingestion headroom materially exceed the current index footprint. "
                    "Reducing partitions removes excess capacity while preserving the existing SKU."
                ),
                category="right_sizing",
                priority="high",
                impact_estimate=(
                    f"Reduce monthly search unit cost by about {_format_currency(topology.get('estimated_partition_savings', 0.0))}."
                ),
                effort="medium",
                remediation_steps=[
                    "Confirm index size, projected growth, and ingestion throughput still fit the smaller partition count.",
                    "Schedule the scale-down during a low-ingestion window to minimize operational risk.",
                    "Track indexing duration and storage utilization after the change.",
                ],
            )
        )

    # Future: Add SKU compatibility checks for storage limits, semantic features, and vector workloads.
    if topology.get("sku_downgrade_candidate"):
        current_sku = str(service.get("sku", "current SKU"))
        target_sku = str(topology.get("suggested_sku", "lower SKU"))
        recommendations.append(
            Recommendation(
                title=f"Downgrade SKU from {current_sku} to {target_sku}",
                description=(
                    "Observed workload patterns do not justify the current tier. A lower SKU should "
                    "meet demand while improving cost efficiency."
                ),
                category="right_sizing",
                priority="medium",
                impact_estimate=(
                    f"Capture an estimated {_format_currency(topology.get('estimated_sku_savings', 0.0))} in monthly savings."
                ),
                effort="medium",
                remediation_steps=[
                    "Review feature dependencies and service limits that differ between the current and target SKUs.",
                    "Rehearse the tier change in a non-production environment or during a maintenance window.",
                    "Update infrastructure definitions so the lower SKU remains the desired state.",
                ],
            )
        )

    return recommendations


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _format_currency(value: Any) -> str:
    amount = float(value or 0.0)
    return f"${amount:,.0f}"
