"""JSON-backed repository for advisor artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonRepository:
    """Loads and persists JSON-backed advisor artifacts."""

    def __init__(self, base_path: Path | None = None) -> None:
        self._base_path = base_path or Path("data")

    def load(self, relative_path: str) -> dict[str, Any]:
        """Load a JSON file from the configured base path."""
        file_path = self._base_path / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"JSON artifact not found: {file_path}")
        with file_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save(self, relative_path: str, data: dict[str, Any]) -> Path:
        """Persist a JSON artifact to the configured base path."""
        file_path = self._base_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, default=str)
        return file_path

    def list_files(self, directory: str = "", pattern: str = "*.json") -> list[Path]:
        """List JSON files matching a pattern in the given directory."""
        search_path = self._base_path / directory
        if not search_path.exists():
            return []
        return sorted(search_path.glob(pattern))
