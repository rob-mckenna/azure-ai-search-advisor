"""Top-level validated input contract for advisor ingestion."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import Field, validator

from azure_ai_search_advisor.models.base import AdvisorModel
from azure_ai_search_advisor.models.configuration import AzureSearchServiceConfiguration
from azure_ai_search_advisor.models.metrics import AzureSearchServiceMetrics


class AzureSearchServiceSnapshot(AdvisorModel):
    """Single point-in-time configuration and metrics snapshot."""

    schema_version: str = Field(default="1.0")
    collected_at: datetime
    configuration: AzureSearchServiceConfiguration
    metrics: AzureSearchServiceMetrics | None = None
    notes: list[str] = Field(default_factory=list)

    @validator("schema_version")
    def validate_schema_version(cls, value: str) -> str:
        """Ensure version strings follow a simple major.minor shape."""
        if re.match(r"^\d+\.\d+$", value) is None:
            raise ValueError("schema_version must match <major>.<minor>.")
        return value
