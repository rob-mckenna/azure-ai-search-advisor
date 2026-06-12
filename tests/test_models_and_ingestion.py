"""Validation tests for scaffolded data models and ingestion."""

from __future__ import annotations

import unittest
from pathlib import Path

from pydantic import ValidationError

from azure_ai_search_advisor.ingestion import IngestionService
from azure_ai_search_advisor.models import AzureSearchServiceSnapshot


class AzureSearchModelsAndIngestionTests(unittest.TestCase):
    """Exercise the snapshot contract and ingestion entrypoints."""

    def setUp(self) -> None:
        """Resolve repository-relative test paths."""
        self.repo_root = Path(__file__).resolve().parents[1]
        self.data_root = self.repo_root / "data" / "inputs"

    def test_mock_inputs_validate(self) -> None:
        """All curated mock datasets should validate successfully."""
        service = IngestionService(data_root=self.data_root)

        snapshots = service.ingest_directory()

        self.assertEqual(len(snapshots), 4)
        self.assertTrue(all(isinstance(snapshot, AzureSearchServiceSnapshot) for snapshot in snapshots))

    def test_search_units_are_computed_for_dedicated_services(self) -> None:
        """Dedicated services expose a computed search unit count."""
        service = IngestionService(data_root=self.data_root)
        snapshot = service.ingest_file(self.data_root / "over_provisioned.json")

        self.assertEqual(snapshot.configuration.search_units, 24)

    def test_dedicated_services_require_capacity_dimensions(self) -> None:
        """Dedicated services must define replica and partition counts."""
        with self.assertRaises(ValidationError):
            AzureSearchServiceSnapshot.model_validate(
                {
                    "schema_version": "1.0",
                    "collected_at": "2026-05-31T23:45:00Z",
                    "configuration": {
                        "service_name": "invalid-search",
                        "subscription_id": "00000000-0000-0000-0000-000000000000",
                        "resource_group": "rg-invalid",
                        "location": "eastus",
                        "deployment_mode": "dedicated",
                        "sku": "s1",
                        "features_enabled": [],
                        "semantic_ranker": {"enabled": False},
                        "vector_search": {"enabled": False},
                        "ai_enrichment": {"enabled": False},
                    },
                    "metrics": {
                        "observation_window_days": 30,
                        "query_volume": {
                            "avg_queries_per_day": 1,
                            "peak_queries_per_day": 1,
                            "avg_queries_per_second": 0,
                            "monthly_queries": 30
                        },
                        "total_index_size_gb": 1,
                        "document_count": 1,
                        "feature_usage": {
                            "semantic_query_percentage": 0,
                            "vector_query_percentage": 0,
                            "ai_enrichment_runs_per_day": 0,
                            "indexer_runs_per_day": 0,
                            "skill_invocations_per_day": 0,
                            "integrated_vectorization_calls_per_day": 0
                        },
                        "latency": {
                            "p50_ms": 1,
                            "p95_ms": 1,
                            "p99_ms": 1
                        },
                        "avg_cpu_utilization_pct": 1,
                        "storage_quota_utilization_pct": 1,
                        "throttled_queries_per_day": 0,
                        "indexing_operations_per_day": 0
                    }
                }
            )


if __name__ == "__main__":
    unittest.main()
