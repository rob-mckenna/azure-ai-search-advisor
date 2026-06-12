"""Analysis finding contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, StrictBool, StrictFloat, StrictInt

from azure_ai_search_advisor.models.base import AdvisorModel

FindingSeverity = Literal["low", "medium", "high"]
FindingCategory = Literal["provisioning", "sku", "feature_usage"]
EvidenceValue = StrictBool | StrictInt | StrictFloat | str | None


class FindingEvidence(AdvisorModel):
    """Structured evidence attached to an analysis finding."""

    summary: str = Field(description="Human-readable evidence supporting the finding.")
    details: dict[str, EvidenceValue] = Field(
        default_factory=dict,
        description="Optional structured metrics or configuration details referenced by the finding.",
    )


class AnalysisFinding(AdvisorModel):
    """Normalized issue reported by analysis components."""

    severity: FindingSeverity = Field(description="Relative urgency of the finding.")
    category: FindingCategory = Field(description="Analysis domain that produced the finding.")
    title: str = Field(description="Short one-line description of the finding.")
    description: str = Field(description="Clear explanation of the detected issue.")
    evidence: dict[str, EvidenceValue] = Field(
        default_factory=dict,
        description="Structured metrics and configuration details supporting the finding.",
    )
    impact: str = Field(description="Expected operational or cost impact if not addressed.")
