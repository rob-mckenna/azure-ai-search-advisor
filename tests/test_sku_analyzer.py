from __future__ import annotations

from azure_ai_search_advisor.analysis.sku_analyzer import SkuAnalysisInput, SkuAnalyzer
from azure_ai_search_advisor.models import SearchSku


def test_s3_workload_that_fits_s1_is_detected(sample_snapshot) -> None:
    configuration = sample_snapshot.configuration.model_copy(update={"sku": SearchSku.S3})

    result = SkuAnalyzer().analyze(
        SkuAnalysisInput(configuration=configuration, metrics=sample_snapshot.metrics)
    )

    finding = next(
        finding
        for finding in result.findings
        if finding.title == "Current S3 workload appears to fit within S1 limits"
    )

    assert finding.evidence["target_sku"] == "s1"
    assert finding.evidence["s1_storage_limit_gb"] == 300.0


def test_basic_sku_pressure_is_detected(sample_snapshot) -> None:
    configuration = sample_snapshot.configuration.model_copy(update={"sku": SearchSku.BASIC})
    metrics = sample_snapshot.metrics.model_copy(
        update={
            "total_index_size_gb": 3.4,
            "storage_quota_utilization_pct": 92.0,
            "query_volume": sample_snapshot.metrics.query_volume.model_copy(
                update={
                    "avg_queries_per_day": 40_000,
                    "peak_queries_per_day": 65_000,
                    "avg_queries_per_second": 3.5,
                    "monthly_queries": 1_200_000,
                }
            ),
        }
    )

    result = SkuAnalyzer().analyze(
        SkuAnalysisInput(configuration=configuration, metrics=metrics)
    )

    finding = next(
        finding
        for finding in result.findings
        if finding.title == "Basic SKU may be undersized for the observed workload"
    )

    assert finding.severity == "high"
    assert finding.evidence["basic_storage_limit_gb"] == 2.0
    assert finding.evidence["monthly_queries"] == 1_200_000


def test_serverless_candidate_is_detected(sample_snapshot) -> None:
    metrics = sample_snapshot.metrics.model_copy(
        update={
            "avg_cpu_utilization_pct": 9.0,
            "query_volume": sample_snapshot.metrics.query_volume.model_copy(
                update={
                    "avg_queries_per_day": 1_500,
                    "peak_queries_per_day": 4_000,
                    "avg_queries_per_second": 0.03,
                    "monthly_queries": 45_000,
                }
            ),
        }
    )

    result = SkuAnalyzer().analyze(
        SkuAnalysisInput(configuration=sample_snapshot.configuration, metrics=metrics)
    )

    finding = next(
        finding
        for finding in result.findings
        if finding.title == "Dedicated service may be a serverless candidate"
    )

    assert finding.evidence["monthly_queries"] == 45_000
    assert finding.evidence["avg_cpu_utilization_pct"] == 9.0
