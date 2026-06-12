from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from azure_ai_search_advisor.ingestion import IngestionService
from azure_ai_search_advisor.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def data_root() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "inputs"


@pytest.fixture
def sample_snapshot(data_root: Path):
    return IngestionService(data_root=data_root).ingest_file(data_root / "over_provisioned.json")
