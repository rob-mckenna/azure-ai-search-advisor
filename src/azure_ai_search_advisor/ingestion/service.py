"""Ingestion service scaffold."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from azure_ai_search_advisor.ingestion.validators import (
    ensure_json_input_path,
    validate_input_payload,
)
from azure_ai_search_advisor.models import AzureSearchServiceSnapshot


class IngestionService:
    """Loads, validates, and normalizes Azure AI Search inputs."""

    def __init__(self, data_root: str | Path | None = None) -> None:
        """Create a loader for JSON snapshots."""
        self.data_root = Path(data_root) if data_root is not None else Path("data/inputs")

    def ingest_file(self, path: str | Path) -> AzureSearchServiceSnapshot:
        """Load, validate, and normalize a single JSON snapshot."""
        json_path = ensure_json_input_path(path)
        payload = self._load_json_file(json_path)
        return self.ingest_payload(payload)

    def ingest_directory(self, directory: str | Path | None = None) -> list[AzureSearchServiceSnapshot]:
        """Load all JSON snapshots from a directory."""
        root = Path(directory) if directory is not None else self.data_root
        return [self.ingest_file(path) for path in sorted(root.glob("*.json"))]

    def ingest_payload(self, payload: Mapping[str, Any]) -> AzureSearchServiceSnapshot:
        """Validate and normalize an in-memory payload."""
        normalized_payload = self._normalize_payload(payload)
        snapshot = validate_input_payload(normalized_payload)
        return self._post_process_snapshot(snapshot)

    def ingest_many(
        self, payloads: Iterable[Mapping[str, Any]]
    ) -> list[AzureSearchServiceSnapshot]:
        """Validate many payloads using the same normalization pipeline."""
        return [self.ingest_payload(payload) for payload in payloads]

    def _load_json_file(self, path: Path) -> dict[str, Any]:
        """Read a JSON payload from disk."""
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _normalize_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Normalize inbound payloads before validation."""
        # TODO: Add version-aware normalization, alias handling, and default enrichment.
        return dict(payload)

    def _post_process_snapshot(
        self, snapshot: AzureSearchServiceSnapshot
    ) -> AzureSearchServiceSnapshot:
        """Apply post-validation enrichment hooks."""
        # TODO: Add cross-source joins, tagging, and ingestion provenance metadata.
        return snapshot
