from __future__ import annotations

from pathlib import Path

from azure_ai_search_advisor.analysis.provisioning_analyzer import (
    ProvisioningAnalysisInput,
    ProvisioningAnalyzer,
)
from azure_ai_search_advisor.ingestion import IngestionService
from azure_ai_search_advisor.models import DeploymentMode


def _load_snapshot(data_root: Path, filename: str):
    return IngestionService(data_root=data_root).ingest_file(data_root / filename)


def test_over_provisioned_replicas_are_detected(sample_snapshot) -> None:
    result = ProvisioningAnalyzer().analyze(
        ProvisioningAnalysisInput(
            configuration=sample_snapshot.configuration,
            metrics=sample_snapshot.metrics,
        )
    )

    replica_finding = next(
        finding
        for finding in result.findings
        if finding.title == "Replica count is high relative to sustained query demand"
    )

    assert result.avg_qps_per_replica == 0.035
    assert replica_finding.evidence["qps_per_replica"] < 5
    assert replica_finding.evidence["threshold_qps_per_replica"] == 5.0



def test_over_provisioned_partitions_are_detected(sample_snapshot) -> None:
    result = ProvisioningAnalyzer().analyze(
        ProvisioningAnalysisInput(
            configuration=sample_snapshot.configuration,
            metrics=sample_snapshot.metrics,
        )
    )

    partition_finding = next(
        finding
        for finding in result.findings
        if finding.title == "Partition allocation is oversized for current index storage"
    )

    assert result.index_size_gb_per_partition == 12.15
    assert result.partition_capacity_gb == 100.0
    assert partition_finding.evidence["fits_single_partition"] is True



def test_idle_service_is_detected(sample_snapshot) -> None:
    result = ProvisioningAnalyzer().analyze(
        ProvisioningAnalysisInput(
            configuration=sample_snapshot.configuration,
            metrics=sample_snapshot.metrics,
        )
    )

    idle_finding = next(
        finding for finding in result.findings if finding.title == "Service appears idle or near-idle"
    )

    assert idle_finding.severity == "high"
    assert idle_finding.evidence["avg_queries_per_second"] < 1
    assert idle_finding.evidence["idle_qps_threshold"] == 1.0



def test_well_optimized_service_produces_fewer_findings(data_root: Path, sample_snapshot) -> None:
    analyzer = ProvisioningAnalyzer()
    over_provisioned_result = analyzer.analyze(
        ProvisioningAnalysisInput(
            configuration=sample_snapshot.configuration,
            metrics=sample_snapshot.metrics,
        )
    )
    well_optimized_snapshot = _load_snapshot(data_root, "well_optimized.json")
    well_optimized_result = analyzer.analyze(
        ProvisioningAnalysisInput(
            configuration=well_optimized_snapshot.configuration,
            metrics=well_optimized_snapshot.metrics,
        )
    )

    assert len(well_optimized_result.findings) < len(over_provisioned_result.findings)
    assert all(
        finding.title != "Service appears idle or near-idle"
        for finding in well_optimized_result.findings
    )
    assert all(
        finding.title != "Partition allocation is oversized for current index storage"
        for finding in well_optimized_result.findings
    )



def test_serverless_services_are_handled_gracefully(sample_snapshot) -> None:
    serverless_snapshot = sample_snapshot.model_copy(
        update={
            "configuration": sample_snapshot.configuration.model_copy(
                update={
                    "deployment_mode": DeploymentMode.SERVERLESS,
                    "replicas": None,
                    "partitions": None,
                    "availability_zones_enabled": False,
                }
            )
        }
    )

    result = ProvisioningAnalyzer().analyze(
        ProvisioningAnalysisInput(
            configuration=serverless_snapshot.configuration,
            metrics=serverless_snapshot.metrics,
        )
    )

    assert result.avg_qps_per_replica is None
    assert result.index_size_gb_per_partition is None
    assert all("Replica count" not in finding.title for finding in result.findings)
    assert all("Partition allocation" not in finding.title for finding in result.findings)
