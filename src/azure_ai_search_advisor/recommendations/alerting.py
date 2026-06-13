"""Alerting recommendation scaffolds."""

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.models.recommendations import Recommendation


def generate_alerting_recommendations(
    analysis_findings: Mapping[str, Any],
    cost_data: Mapping[str, Any],
) -> list[Recommendation]:
    """Generate Azure Monitor alert suggestions from workload health signals."""

    del cost_data

    service = _as_mapping(analysis_findings.get("service"))
    alerting = _as_mapping(analysis_findings.get("alerting"))
    recommendations: list[Recommendation] = []

    service_name = str(service.get("service_name") or "search-service")
    replicas = int(service.get("replicas", 0) or 0)
    latency_p95_ms = _as_float(alerting.get("query_latency_p95_ms"))
    replica_utilization_percent = _as_float(alerting.get("replica_utilization_percent"))
    storage_utilization_percent = _as_float(alerting.get("storage_utilization_percent"))
    throttled_queries_per_day = _as_float(alerting.get("throttled_queries_per_day"))
    avg_queries_per_second = _as_float(alerting.get("avg_queries_per_second"))
    avg_cpu_utilization_pct = _as_float(alerting.get("avg_cpu_utilization_pct"))
    indexer_count = int(alerting.get("indexer_count", service.get("indexer_count", 0)) or 0)
    indexer_monitoring_configured = bool(alerting.get("indexer_monitoring_configured", False))

    if latency_p95_ms is not None and latency_p95_ms > 500:
        recommendations.append(
            Recommendation(
                title="Add latency alert: p95 > 500ms for 5 min",
                description=(
                    f"Observed p95 query latency is {latency_p95_ms:.0f} ms. A percentile-based "
                    "Azure Monitor alert helps operators catch sustained search slowdowns before "
                    "they turn into user-visible outages."
                ),
                category="alerting",
                priority="high",
                impact_estimate=(
                    "Without this alert, degraded search responsiveness can continue unnoticed until "
                    "customers abandon queries or SLA targets are missed."
                ),
                effort="low",
                remediation_steps=[
                    "Enable Azure AI Search diagnostics export to a Log Analytics workspace.",
                    _scheduled_query_command(
                        name=f"{service_name}-latency-p95",
                        description="Alert when Azure AI Search p95 latency exceeds 500 ms for 5 minutes.",
                        query=(
                            'AzureDiagnostics '
                            '| where ResourceProvider == "MICROSOFT.SEARCH" '
                            '| summarize p95_latency_ms = percentile(DurationMs, 95) by bin(TimeGenerated, 5m) '
                            '| where p95_latency_ms > 500'
                        ),
                        severity=2,
                        frequency="5m",
                        window="5m",
                    ),
                ],
            )
        )

    if replica_utilization_percent is not None and 0 <= replica_utilization_percent < 30:
        recommendations.append(
            Recommendation(
                title="Add utilization alert: < 30% for 1 hour",
                description=(
                    f"Replica utilization is only {replica_utilization_percent:.1f}%. Alerting on "
                    "sustained under-utilization gives the team an automated trigger to review scale "
                    "settings and retire excess dedicated capacity."
                ),
                category="alerting",
                priority="medium",
                impact_estimate=(
                    "Without this alert, overprovisioned replicas can keep accruing avoidable monthly "
                    "capacity spend for extended periods."
                ),
                effort="low",
                remediation_steps=[
                    "Send the workload utilization metrics into Log Analytics or a custom Azure Monitor metric namespace.",
                    _scheduled_query_command(
                        name=f"{service_name}-low-utilization",
                        description="Alert when average replica utilization stays below 30 percent for one hour.",
                        query=(
                            'AzureMetrics '
                            '| where ResourceId =~ "<search-service-resource-id>" '
                            '| where MetricName in ("CpuPercentage", "avg_cpu_utilization_pct") '
                            '| summarize avg_utilization = avg(Average) by bin(TimeGenerated, 1h) '
                            '| where avg_utilization < 30'
                        ),
                        severity=3,
                        frequency="15m",
                        window="1h",
                    ),
                ],
            )
        )

    if storage_utilization_percent is not None and storage_utilization_percent > 80:
        recommendations.append(
            Recommendation(
                title="Add storage alert: > 80% utilization",
                description=(
                    f"Storage utilization is already {storage_utilization_percent:.1f}%. A storage alert "
                    "creates early warning before index growth blocks writes, slows indexing, or forces "
                    "an emergency scale event."
                ),
                category="alerting",
                priority="high",
                impact_estimate=(
                    "Without this alert, the service can run out of storage headroom and trigger failed "
                    "indexing operations or unplanned scaling work."
                ),
                effort="low",
                remediation_steps=[
                    _scheduled_query_command(
                        name=f"{service_name}-storage-80pct",
                        description="Alert when Azure AI Search storage usage exceeds 80 percent of quota.",
                        query=(
                            'AzureMetrics '
                            '| where ResourceId =~ "<search-service-resource-id>" and MetricName == "IndexStorageUsage" '
                            '| summarize max_storage_bytes = max(Maximum) by bin(TimeGenerated, 5m) '
                            '| where max_storage_bytes > (<storage-quota-bytes> * 0.8)'
                        ),
                        severity=2,
                        frequency="5m",
                        window="5m",
                    ),
                    "For ARM/Bicep, parameterize the storage quota in bytes and set the threshold to 80 percent of that value.",
                ],
            )
        )

    if (throttled_queries_per_day is not None and throttled_queries_per_day > 0) or bool(
        alerting.get("throttled_queries_detected")
    ):
        recommendations.append(
            Recommendation(
                title="Add throttling alert: > 0 throttled queries",
                description=(
                    f"The workload is already showing about {throttled_queries_per_day:.0f} throttled queries "
                    "per day. An Azure Monitor alert makes throttling visible before it becomes a broader "
                    "availability or latency incident."
                ),
                category="alerting",
                priority="high",
                impact_estimate=(
                    "Without this alert, search requests can be throttled long enough to hurt customer "
                    "experience before anyone investigates scale pressure."
                ),
                effort="low",
                remediation_steps=[
                    _metrics_alert_command(
                        name=f"{service_name}-throttled-queries",
                        description="Alert when Azure AI Search reports any throttled queries.",
                        condition="avg ThrottledSearchQueriesPercentage > 0",
                        severity=2,
                        window="5m",
                    ),
                ],
            )
        )

    if indexer_count > 0 and not indexer_monitoring_configured:
        recommendations.append(
            Recommendation(
                title="Add indexer failure alert",
                description=(
                    f"This service runs {indexer_count} indexer(s), but no explicit indexer failure "
                    "monitoring signal was provided. Alerting on failed document processing reduces the "
                    "risk of stale or partially populated indexes."
                ),
                category="alerting",
                priority="medium",
                impact_estimate=(
                    "Without indexer failure alerts, ingestion gaps can persist silently and leave search "
                    "results stale, incomplete, or inconsistent."
                ),
                effort="low",
                remediation_steps=[
                    _metrics_alert_command(
                        name=f"{service_name}-indexer-failures",
                        description="Alert when any Azure AI Search indexer processes failed documents.",
                        condition="total DocumentsProcessedCount > 0 where Failed eq 'true'",
                        severity=2,
                        window="5m",
                    ),
                ],
            )
        )

    if avg_queries_per_second is not None and 0 <= avg_queries_per_second < 1:
        recommendations.append(
            Recommendation(
                title="Add idle-service cost alert: < 1 QPS for 24 hours",
                description=(
                    f"Average traffic is only {avg_queries_per_second:.2f} QPS. An idle-service alert helps "
                    "surface dormant dedicated services that are still incurring monthly capacity cost."
                ),
                category="alerting",
                priority="medium",
                impact_estimate=(
                    "Without an idle-service alert, low-value environments can keep consuming budget long "
                    "after the workload has gone quiet."
                ),
                effort="low",
                remediation_steps=[
                    _metrics_alert_command(
                        name=f"{service_name}-idle-service",
                        description="Alert when search traffic stays below 1 QPS for 24 hours.",
                        condition="avg SearchQueriesPerSecond < 1",
                        severity=3,
                        window="24h",
                        frequency="1h",
                    ),
                ],
            )
        )

    if avg_cpu_utilization_pct is not None and avg_cpu_utilization_pct > 80 and 0 < replicas <= 2:
        recommendations.append(
            Recommendation(
                title="Add CPU alert: > 80% for 15 min (scale trigger)",
                description=(
                    f"Average CPU utilization is {avg_cpu_utilization_pct:.1f}% on a {replicas}-replica "
                    "topology. A short-window alert can trigger faster scale review before the service "
                    "saturates and latency climbs."
                ),
                category="alerting",
                priority="high",
                impact_estimate=(
                    "Without a CPU or compute-pressure alert, small replica pools can saturate and degrade "
                    "query latency before operators have time to scale out."
                ),
                effort="low",
                remediation_steps=[
                    "If CPU is exported as a custom Azure Monitor metric, wire the alert directly to that metric; otherwise use PerRequestComputeConsumption as a scale-pressure proxy.",
                    _scheduled_query_command(
                        name=f"{service_name}-cpu-high",
                        description="Alert when Azure AI Search CPU or compute pressure stays above 80 percent for 15 minutes.",
                        query=(
                            'AzureMetrics '
                            '| where ResourceId =~ "<search-service-resource-id>" '
                            '| where MetricName in ("CpuPercentage", "avg_cpu_utilization_pct", "PerRequestComputeConsumption") '
                            '| summarize avg_pressure = avg(Average) by bin(TimeGenerated, 15m) '
                            '| where avg_pressure > 80'
                        ),
                        severity=2,
                        frequency="5m",
                        window="15m",
                    ),
                ],
            )
        )

    return recommendations


def _metrics_alert_command(
    *,
    name: str,
    description: str,
    condition: str,
    severity: int,
    window: str,
    frequency: str = "1m",
) -> str:
    return (
        "az monitor metrics alert create "
        f'--name "{name}" '
        '--resource-group <resource-group> '
        '--scopes "<search-service-resource-id>" '
        f'--description "{description}" '
        f'--condition "{condition}" '
        f'--severity {severity} '
        f'--window-size {window} '
        f'--evaluation-frequency {frequency}'
    )


def _scheduled_query_command(
    *,
    name: str,
    description: str,
    query: str,
    severity: int,
    frequency: str,
    window: str,
) -> str:
    normalized_query = " ".join(query.split())
    return (
        "az monitor scheduled-query create "
        f'--name "{name}" '
        '--resource-group <resource-group> '
        '--scopes "<log-analytics-workspace-resource-id>" '
        f'--description "{description}" '
        f"--query '{normalized_query}' "
        '--condition "count > 0" '
        f'--severity {severity} '
        f'--evaluation-frequency {frequency} '
        f'--window-size {window}'
    )


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
