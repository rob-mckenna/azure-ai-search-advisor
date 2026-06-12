"""Agent wrapper around the analysis domain service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.analysis import AnalysisResult, AnalysisService
from azure_ai_search_advisor.analysis.feature_analyzer import FeatureAnalysisResult
from azure_ai_search_advisor.analysis.provisioning_analyzer import ProvisioningAnalysisResult
from azure_ai_search_advisor.analysis.sku_analyzer import SkuAnalysisResult
from azure_ai_search_advisor.models import (
    AzureSearchServiceConfiguration,
    AzureSearchServiceMetrics,
    AzureSearchServiceSnapshot,
)
from azure_ai_search_advisor.orchestration.config import AgentConfig
from azure_ai_search_advisor.orchestration.tools.analysis_tools import (
    analyze_features,
    analyze_provisioning,
    analyze_sku,
    run_full_analysis,
)


class AnalysisAgent:
    """Specialist agent for Azure AI Search inefficiency detection."""

    def __init__(
        self,
        *,
        config: AgentConfig,
        service: AnalysisService | None = None,
    ) -> None:
        self.config = config
        self.service = service or AnalysisService()

    def analyze_provisioning(
        self,
        *,
        snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
        configuration: AzureSearchServiceConfiguration | Mapping[str, Any] | None = None,
        metrics: AzureSearchServiceMetrics | Mapping[str, Any] | None = None,
    ) -> ProvisioningAnalysisResult:
        """Run provisioning analysis for the supplied workload."""
        return analyze_provisioning(
            snapshot=snapshot,
            configuration=configuration,
            metrics=metrics,
            analyzer=self.service._provisioning_analyzer,
        )

    def analyze_sku(
        self,
        *,
        snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
        configuration: AzureSearchServiceConfiguration | Mapping[str, Any] | None = None,
        metrics: AzureSearchServiceMetrics | Mapping[str, Any] | None = None,
    ) -> SkuAnalysisResult:
        """Run SKU suitability analysis for the supplied workload."""
        return analyze_sku(
            snapshot=snapshot,
            configuration=configuration,
            metrics=metrics,
            analyzer=self.service._sku_analyzer,
        )

    def analyze_features(
        self,
        *,
        snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
        configuration: AzureSearchServiceConfiguration | Mapping[str, Any] | None = None,
        metrics: AzureSearchServiceMetrics | Mapping[str, Any] | None = None,
    ) -> FeatureAnalysisResult:
        """Run feature-efficiency analysis for the supplied workload."""
        return analyze_features(
            snapshot=snapshot,
            configuration=configuration,
            metrics=metrics,
            analyzer=self.service._feature_analyzer,
        )

    def run_full_analysis(
        self,
        *,
        snapshot: AzureSearchServiceSnapshot | Mapping[str, Any] | None = None,
        configuration: AzureSearchServiceConfiguration | Mapping[str, Any] | None = None,
        metrics: AzureSearchServiceMetrics | Mapping[str, Any] | None = None,
    ) -> AnalysisResult:
        """Run the complete analysis pipeline for the supplied workload."""
        return run_full_analysis(
            snapshot=snapshot,
            configuration=configuration,
            metrics=metrics,
            service=self.service,
        )
