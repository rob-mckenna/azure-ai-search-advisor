"""Input validation scaffold for Azure AI Search data."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from azure_ai_search_advisor.models import AzureSearchServiceSnapshot


def ensure_json_input_path(path: str | Path) -> Path:
    """Validate that an input path looks like a JSON snapshot."""
    json_path = Path(path)
    if json_path.suffix.lower() != ".json":
        raise ValueError("Input files must use the .json extension.")
    if not json_path.exists():
        raise FileNotFoundError(json_path)
    return json_path


def validate_input_payload(payload: Mapping[str, Any]) -> AzureSearchServiceSnapshot:
    """Validate a raw payload against the snapshot contract."""
    snapshot = AzureSearchServiceSnapshot.model_validate(payload)
    return validate_snapshot_consistency(snapshot)


def validate_snapshot_consistency(
    snapshot: AzureSearchServiceSnapshot,
) -> AzureSearchServiceSnapshot:
    """Run lightweight domain validation after schema parsing."""
    configuration = snapshot.configuration
    feature_usage = snapshot.metrics.feature_usage

    if not configuration.semantic_ranker.enabled and feature_usage.semantic_query_percentage > 0:
        raise ValueError("Semantic query usage cannot be reported when semantic ranker is disabled.")

    if not configuration.vector_search.enabled and feature_usage.vector_query_percentage > 0:
        raise ValueError("Vector query usage cannot be reported when vector search is disabled.")

    if not configuration.ai_enrichment.enabled and (
        feature_usage.ai_enrichment_runs_per_day > 0
        or feature_usage.skill_invocations_per_day > 0
    ):
        raise ValueError("AI enrichment usage cannot be reported when AI enrichment is disabled.")

    # TODO: Add workload-specific guardrails, schema migrations, and telemetry provenance checks.
    return snapshot
