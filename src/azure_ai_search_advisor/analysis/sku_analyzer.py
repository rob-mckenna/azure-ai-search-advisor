"""SKU selection analyzer scaffold."""

from __future__ import annotations

from pydantic import Field

from azure_ai_search_advisor.models import AdvisorModel, AnalysisFinding


class SkuAnalysisInput(AdvisorModel):
    """Inputs required to evaluate SKU suitability."""

    configuration: AdvisorModel | None = Field(
        default=None,
        description="TODO: Replace with the concrete Azure AI Search configuration model.",
    )
    metrics: AdvisorModel | None = Field(
        default=None,
        description="TODO: Replace with the concrete workload metrics model.",
    )


class SkuAnalysisResult(AdvisorModel):
    """SKU-specific findings."""

    findings: list[AnalysisFinding] = Field(
        default_factory=list,
        description="SKU mismatch issues identified for the workload.",
    )


class SkuAnalyzer:
    """Identifies likely SKU over-sizing or under-sizing."""

    def analyze(self, analysis_input: SkuAnalysisInput) -> SkuAnalysisResult:
        """Compare SKU choice to workload scale and feature requirements."""
        findings: list[AnalysisFinding] = []

        # TODO: Add SKU fit checks such as premium-tier usage without premium-only demand.
        _ = analysis_input

        return SkuAnalysisResult(findings=findings)
