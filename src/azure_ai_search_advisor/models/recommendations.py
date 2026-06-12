"""Recommendation output models."""

from pydantic import Field

from azure_ai_search_advisor.models.base import AdvisorModel


class Recommendation(AdvisorModel):
    """Actionable recommendation generated from analysis and cost signals."""

    title: str = Field(description="Short, action-oriented recommendation title.")
    description: str = Field(description="Rationale for the recommendation.")
    category: str = Field(description="Recommendation category, such as right_sizing.")
    priority: str = Field(description="Relative urgency for the recommendation.")
    impact_estimate: str = Field(description="Expected business or cost impact.")
    effort: str = Field(description="Relative implementation effort.")
    remediation_steps: list[str] = Field(
        default_factory=list,
        description="Ordered, actionable next steps for the customer.",
    )


class RecommendationReport(AdvisorModel):
    """Aggregated recommendation output for a workload."""

    summary: str = Field(description="Human-readable synopsis of the recommendation set.")
    recommendations: list[Recommendation] = Field(
        default_factory=list,
        description="Ranked recommendations for the workload.",
    )
    estimated_savings: dict[str, float | str] = Field(
        default_factory=dict,
        description="Estimated savings summary, typically monthly and annual.",
    )
