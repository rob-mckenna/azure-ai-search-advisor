"""Provisioning inefficiency analyzer."""

from __future__ import annotations

from pydantic import Field

from azure_ai_search_advisor.models import (
    AdvisorModel,
    AnalysisFinding,
    AzureSearchServiceConfiguration,
    AzureSearchServiceMetrics,
    SearchSku,
)


class ProvisioningAnalysisInput(AdvisorModel):
    """Inputs required to assess replica and partition efficiency."""

    configuration: AzureSearchServiceConfiguration = Field(
        description="Azure AI Search service configuration to evaluate.",
    )
    metrics: AzureSearchServiceMetrics = Field(
        description="Observed Azure AI Search workload metrics.",
    )


class ProvisioningAnalysisResult(AdvisorModel):
    """Provisioning-specific findings."""

    findings: list[AnalysisFinding] = Field(
        default_factory=list,
        description="Provisioning issues identified for the workload.",
    )
    avg_qps_per_replica: float | None = Field(
        default=None,
        description="Average queries per second handled by each configured replica.",
    )
    index_size_gb_per_partition: float | None = Field(
        default=None,
        description="Average index storage assigned to each configured partition.",
    )
    partition_capacity_gb: float | None = Field(
        default=None,
        description="Estimated storage capacity per partition for the current SKU.",
    )


class ProvisioningAnalyzer:
    """Detects over-provisioned or imbalanced search service capacity."""

    _PARTITION_CAPACITY_GB: dict[SearchSku, float] = {
        SearchSku.BASIC: 2.0,
        SearchSku.FREE: 2.0,
        SearchSku.S1: 25.0,
        SearchSku.S2: 100.0,
        SearchSku.S3: 200.0,
        SearchSku.S3_HD: 200.0,
    }

    def analyze(self, analysis_input: ProvisioningAnalysisInput) -> ProvisioningAnalysisResult:
        """Evaluate replicas and partitions against observed workload metrics."""
        findings: list[AnalysisFinding] = []
        configuration = analysis_input.configuration
        metrics = analysis_input.metrics

        replicas = configuration.replicas or 0
        partitions = configuration.partitions or 0
        avg_qps = metrics.query_volume.avg_queries_per_second
        total_index_size_gb = metrics.total_index_size_gb
        qps_per_replica = avg_qps / replicas if replicas else None
        index_size_per_partition = total_index_size_gb / partitions if partitions else None
        partition_capacity_gb = self._PARTITION_CAPACITY_GB.get(configuration.sku)

        if qps_per_replica is not None and replicas > 1 and qps_per_replica < 5:
            findings.append(
                AnalysisFinding(
                    severity="medium",
                    category="provisioning",
                    title="Replica count is high relative to sustained query demand",
                    description=(
                        f"The service averages {avg_qps:.2f} QPS across {replicas} replicas, which is "
                        f"only {qps_per_replica:.2f} QPS per replica. This is below the 5 QPS per replica "
                        "threshold and suggests the service is paying for more query capacity than the "
                        "observed workload requires."
                    ),
                    evidence={
                        "avg_queries_per_second": round(avg_qps, 2),
                        "replicas": replicas,
                        "qps_per_replica": round(qps_per_replica, 2),
                        "threshold_qps_per_replica": 5.0,
                    },
                    impact=(
                        "Reducing one or more replicas could lower search unit cost while maintaining "
                        "current average query throughput."
                    ),
                )
            )

        has_explicit_ha_requirement = configuration.availability_zones_enabled
        if replicas > 3 and not has_explicit_ha_requirement:
            findings.append(
                AnalysisFinding(
                    severity="low",
                    category="provisioning",
                    title="Replica count exceeds typical baseline without an HA signal",
                    description=(
                        f"The service is configured with {replicas} replicas, which is above the baseline "
                        "of three replicas often used for query availability and rolling maintenance. No "
                        "explicit high-availability signal was found in configuration, so the extra replicas "
                        "may be unnecessary."
                    ),
                    evidence={
                        "replicas": replicas,
                        "availability_zones_enabled": configuration.availability_zones_enabled,
                        "ha_baseline_replicas": 3,
                    },
                    impact=(
                        "Reducing excess replicas can lower ongoing compute cost if uptime requirements "
                        "do not require the additional capacity."
                    ),
                )
            )

        if (
            partition_capacity_gb is not None
            and index_size_per_partition is not None
            and partition_capacity_gb > 0
        ):
            utilization_ratio = index_size_per_partition / partition_capacity_gb
            fits_single_partition = partitions > 1 and total_index_size_gb <= partition_capacity_gb

            if utilization_ratio < 0.25 or fits_single_partition:
                recommendation = (
                    "The full index payload fits within a single partition."
                    if fits_single_partition
                    else "Each partition is using less than 25% of the available storage capacity."
                )
                findings.append(
                    AnalysisFinding(
                        severity="medium",
                        category="provisioning",
                        title="Partition allocation is oversized for current index storage",
                        description=(
                            f"The service stores {total_index_size_gb:.2f} GB across {partitions} partitions "
                            f"on SKU {configuration.sku.value}, which works out to {index_size_per_partition:.2f} "
                            f"GB per partition. That is {utilization_ratio:.1%} of the estimated "
                            f"{partition_capacity_gb:.0f} GB capacity per partition. {recommendation}"
                        ),
                        evidence={
                            "sku": configuration.sku.value,
                            "partitions": partitions,
                            "total_index_size_gb": round(total_index_size_gb, 2),
                            "index_size_gb_per_partition": round(index_size_per_partition, 2),
                            "partition_capacity_gb": partition_capacity_gb,
                            "partition_capacity_utilization_ratio": round(utilization_ratio, 4),
                            "threshold_utilization_ratio": 0.25,
                            "fits_single_partition": fits_single_partition,
                        },
                        impact=(
                            "Reducing partitions can lower search unit cost when storage demand is well "
                            "below the allocated partition capacity."
                        ),
                    )
                )

        if avg_qps < 1:
            findings.append(
                AnalysisFinding(
                    severity="high",
                    category="provisioning",
                    title="Service appears idle or near-idle",
                    description=(
                        f"The service averages {avg_qps:.2f} QPS over the {metrics.observation_window_days}-day "
                        "observation window, which is below the 1 QPS idle-service threshold. This suggests "
                        "the service may be inactive for long periods or materially over-provisioned for its "
                        "current workload."
                    ),
                    evidence={
                        "avg_queries_per_second": round(avg_qps, 2),
                        "observation_window_days": metrics.observation_window_days,
                        "idle_qps_threshold": 1.0,
                    },
                    impact=(
                        "An idle service can often be downsized aggressively or consolidated, producing "
                        "meaningful infrastructure savings."
                    ),
                )
            )

        return ProvisioningAnalysisResult(
            findings=findings,
            avg_qps_per_replica=round(qps_per_replica, 4) if qps_per_replica is not None else None,
            index_size_gb_per_partition=(
                round(index_size_per_partition, 4)
                if index_size_per_partition is not None
                else None
            ),
            partition_capacity_gb=partition_capacity_gb,
        )
