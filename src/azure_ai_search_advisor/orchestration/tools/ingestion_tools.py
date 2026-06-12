"""Tool functions that expose ingestion service capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from azure_ai_search_advisor.ingestion import IngestionService
from azure_ai_search_advisor.models import AzureSearchServiceSnapshot



def ingest_config(
    payload: Mapping[str, Any],
    *,
    service: IngestionService | None = None,
) -> AzureSearchServiceSnapshot:
    """Ingest and validate an Azure AI Search service snapshot payload."""
    ingestion_service = service or IngestionService()
    return ingestion_service.ingest_payload(payload)



def ingest_config_file(
    path: str,
    *,
    service: IngestionService | None = None,
) -> AzureSearchServiceSnapshot:
    """Load, ingest, and validate an Azure AI Search service snapshot file from disk."""
    ingestion_service = service or IngestionService()
    return ingestion_service.ingest_file(path)



def validate_snapshot(
    snapshot: AzureSearchServiceSnapshot | Mapping[str, Any],
) -> AzureSearchServiceSnapshot:
    """Validate a normalized snapshot before downstream analysis or costing."""
    if isinstance(snapshot, AzureSearchServiceSnapshot):
        return snapshot
    return AzureSearchServiceSnapshot.model_validate(snapshot)
