"""Tool functions that expose analysis capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.analysis import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisService,
    FeatureAnalysisInput,
    FeatureAnalysisResult,
    FeatureAnalyzer,
    ProvisioningAnalysisInput,
    ProvisioningAnalysisResult,
    ProvisioningAnalyzer,
    SkuAnalysisInput,
    SkuAnalysisResult,
    SkuAnalyzer,
)
from azure_ai_search_advisor.models import (
    AzureSearchServiceConfiguration,
    AzureSearchServiceMetrics,
    AzureSearchServiceSnapshot,
)



def analyze_provisioning(
    *,
    snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
    configuration: AzureSearchServiceConfiguration | Mapping[str, Any] | None = None,
    metrics: AzureSearchServiceMetrics | Mapping[str, Any] | None = None,
    analyzer: ProvisioningAnalyzer | None = None,
) -> ProvisioningAnalysisResult:
    """Analyze replica and partition efficiency for an Azure AI Search workload."""
    resolved_configuration, resolved_metrics = _resolve_analysis_inputs(snapshot, configuration, metrics)
    return (analyzer or ProvisioningAnalyzer()).analyze(
        ProvisioningAnalysisInput(
            configuration=resolved_configuration,
            metrics=resolved_metrics,
        )
    )



def analyze_sku(
    *,
    snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
    configuration: AzureSearchServiceConfiguration | Mapping[str, Any] | None = None,
    metrics: AzureSearchServiceMetrics | Mapping[str, Any] | None = None,
    analyzer: SkuAnalyzer | None = None,
) -> SkuAnalysisResult:
    """Analyze SKU fit for an Azure AI Search workload."""
    resolved_configuration, resolved_metrics = _resolve_analysis_inputs(snapshot, configuration, metrics)
    return (analyzer or SkuAnalyzer()).analyze(
        SkuAnalysisInput(
            configuration=resolved_configuration,
            metrics=resolved_metrics,
        )
    )



def analyze_features(
    *,
    snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
    configuration: AzureSearchServiceConfiguration | Mapping[str, Any] | None = None,
    metrics: AzureSearchServiceMetrics | Mapping[str, Any] | None = None,
    analyzer: FeatureAnalyzer | None = None,
) -> FeatureAnalysisResult:
    """Analyze Azure AI Search feature usage efficiency and misconfiguration risk."""
    resolved_configuration, resolved_metrics = _resolve_analysis_inputs(snapshot, configuration, metrics)
    return (analyzer or FeatureAnalyzer()).analyze(
        FeatureAnalysisInput(
            configuration=resolved_configuration,
            metrics=resolved_metrics,
        )
    )



def run_full_analysis(
    *,
    snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
    configuration: AzureSearchServiceConfiguration | Mapping[str, Any] | None = None,
    metrics: AzureSearchServiceMetrics | Mapping[str, Any] | None = None,
    service: AnalysisService | None = None,
) -> AnalysisResult:
    """Run the full Azure AI Search workload analysis pipeline."""
    resolved_configuration, resolved_metrics = _resolve_analysis_inputs(snapshot, configuration, metrics)
    analysis_service = service or AnalysisService()
    return analysis_service.analyze(
        AnalysisRequest(
            configuration=resolved_configuration,
            metrics=resolved_metrics,
        )
    )



def _resolve_analysis_inputs(
    snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None,
    configuration: AzureSearchServiceConfiguration | Mapping[str, Any] | None,
    metrics: AzureSearchServiceMetrics | Mapping[str, Any] | None,
) -> tuple[AzureSearchServiceConfiguration | None, AzureSearchServiceMetrics | None]:
    if snapshot is not None:
        resolved_snapshot = _coerce_snapshot(snapshot)
        return resolved_snapshot.configuration, resolved_snapshot.metrics

    return _coerce_configuration(configuration), _coerce_metrics(metrics)



def _coerce_snapshot(
    snapshot: AzureSearchServiceSnapshot | Mapping[str, Any],
) -> AzureSearchServiceSnapshot:
    if isinstance(snapshot, AzureSearchServiceSnapshot):
        return snapshot
    return AzureSearchServiceSnapshot.model_validate(snapshot)



def _coerce_configuration(
    configuration: AzureSearchServiceConfiguration | Mapping[str, Any] | None,
) -> AzureSearchServiceConfiguration | None:
    if configuration is None or isinstance(configuration, AzureSearchServiceConfiguration):
        return configuration
    return AzureSearchServiceConfiguration.model_validate(configuration)



def _coerce_metrics(
    metrics: AzureSearchServiceMetrics | Mapping[str, Any] | None,
) -> AzureSearchServiceMetrics | None:
    if metrics is None or isinstance(metrics, AzureSearchServiceMetrics):
        return metrics
    return AzureSearchServiceMetrics.model_validate(metrics)
