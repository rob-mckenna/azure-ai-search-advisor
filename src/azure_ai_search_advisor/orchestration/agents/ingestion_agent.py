"""Agent wrapper around the ingestion domain service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.ingestion import IngestionService
from azure_ai_search_advisor.models import AzureSearchServiceSnapshot
from azure_ai_search_advisor.orchestration.config import AgentConfig
from azure_ai_search_advisor.orchestration.tools.ingestion_tools import (
    ingest_config,
    ingest_config_file,
    validate_snapshot,
)


class IngestionAgent:
    """Specialist agent for workload ingestion and validation."""

    def __init__(
        self,
        *,
        config: AgentConfig,
        service: IngestionService | None = None,
    ) -> None:
        self.config = config
        self.service = service or IngestionService()

    def ingest_config(self, payload: Mapping[str, Any]) -> AzureSearchServiceSnapshot:
        """Validate and normalize an in-memory workload snapshot."""
        return ingest_config(payload, service=self.service)

    def ingest_config_file(self, path: str) -> AzureSearchServiceSnapshot:
        """Validate and normalize a workload snapshot stored on disk."""
        return ingest_config_file(path, service=self.service)

    def validate_snapshot(
        self,
        snapshot: AzureSearchServiceSnapshot | Mapping[str, Any],
    ) -> AzureSearchServiceSnapshot:
        """Validate that a snapshot conforms to the shared contract."""
        return validate_snapshot(snapshot)
