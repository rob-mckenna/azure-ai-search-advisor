"""High-level helpers for recording and reading advisor history."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from azure_ai_search_advisor.core.tenancy import LOCAL_TENANT_ID
from azure_ai_search_advisor.repositories.history_db import HistoryDatabase

_LOGGER = logging.getLogger(__name__)
_SEVERITY_ORDER = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}


class HistoryService:
    """Coordinate best-effort history persistence and retrieval."""

    def __init__(self, database: HistoryDatabase | None = None) -> None:
        self._database = database or HistoryDatabase()

    def record_analysis(
        self,
        service_name: str,
        analysis_result: Any,
        cost_result: Any,
        recommendations: Any,
        *,
        tenant_id: str | None = None,
        subscription_id: str | None = None,
        resource_group: str | None = None,
        configuration_hash: str | None = None,
    ) -> None:
        """Persist a full analysis run without propagating storage failures."""

        try:
            analysis_payload = _as_mapping(analysis_result)
            normalized_findings = _normalize_findings(analysis_payload.get("findings", []))
            run_at = _extract_timestamp(analysis_payload.get("generated_at"))
            resolved_service_name = service_name or str(analysis_payload.get("service_name") or "")
            resolved_subscription_id = subscription_id or str(
                analysis_payload.get("subscription_id") or "api-submitted"
            )
            resolved_resource_group = resource_group or str(
                analysis_payload.get("resource_group") or f"{resolved_service_name}-rg"
            )
            resolved_configuration_hash = configuration_hash or compute_configuration_hash(
                {
                    "service_name": resolved_service_name,
                    "subscription_id": resolved_subscription_id,
                    "resource_group": resolved_resource_group,
                    "findings": normalized_findings,
                }
            )
            summary = _build_summary(analysis_payload, normalized_findings)
            normalized_recommendations = _normalize_recommendations(recommendations)
            normalized_cost = _normalize_cost_snapshot(cost_result)

            self._database.insert_analysis_run(
                {
                    "id": str(uuid4()),
                    "tenant_id": tenant_id or str(LOCAL_TENANT_ID),
                    "service_name": resolved_service_name,
                    "subscription_id": resolved_subscription_id,
                    "resource_group": resolved_resource_group,
                    "run_at": run_at,
                    "finding_count": summary["finding_count"],
                    "highest_severity": summary["highest_severity"],
                    "configuration_hash": resolved_configuration_hash,
                },
                normalized_findings,
                normalized_cost,
                normalized_recommendations,
            )
        except (OSError, ValueError, sqlite3.Error) as exc:
            _LOGGER.warning(
                "Unable to record history for service %s: %s",
                service_name,
                exc,
            )

    def get_history(
        self,
        service_name: str,
        *,
        tenant_id: str,
        days: int = 30,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return summarized history rows for a service."""

        try:
            return self._database.fetch_history(service_name, tenant_id=tenant_id, days=days, limit=limit)
        except (OSError, sqlite3.Error) as exc:
            _LOGGER.warning("Unable to read history for service %s: %s", service_name, exc)
            return []

    def get_trends(
        self,
        service_name: str,
        *,
        tenant_id: str,
        days: int = 90,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Return finding and cost trend series for a service."""

        try:
            rows = self._database.fetch_trends(service_name, tenant_id=tenant_id, days=days, limit=limit)
        except (OSError, sqlite3.Error) as exc:
            _LOGGER.warning("Unable to read trend history for service %s: %s", service_name, exc)
            rows = []

        return {
            "finding_count_over_time": [
                {
                    "run_at": row["run_at"],
                    "finding_count": row["finding_count"],
                }
                for row in rows
            ],
            "cost_over_time": [
                {
                    "run_at": row["run_at"],
                    "dedicated_monthly_usd": row["dedicated_monthly_usd"],
                    "serverless_monthly_usd": row["serverless_monthly_usd"],
                    "lower_cost_option": row["lower_cost_option"],
                }
                for row in rows
            ],
        }

    def get_latest(self, service_name: str, *, tenant_id: str) -> dict[str, Any] | None:
        """Return the most recent stored run for a service, if any."""

        try:
            return self._database.fetch_latest(service_name, tenant_id=tenant_id)
        except (OSError, sqlite3.Error) as exc:
            _LOGGER.warning("Unable to read latest history for service %s: %s", service_name, exc)
            return None


def compute_configuration_hash(configuration: Any) -> str:
    """Create a stable hash for a configuration payload."""

    payload = _as_json_compatible(configuration)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _build_summary(analysis_payload: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    summary = _as_mapping(analysis_payload.get("summary"))
    finding_count = int(summary.get("finding_count", len(findings)))
    highest_severity = str(summary.get("highest_severity") or _highest_severity(findings) or "low")
    return {
        "finding_count": finding_count,
        "highest_severity": highest_severity,
    }


def _normalize_findings(findings: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for finding in _as_list(findings):
        payload = _as_mapping(finding)
        evidence = payload.get("evidence", [])
        normalized.append(
            {
                "id": str(uuid4()),
                "category": str(payload.get("category") or "unknown"),
                "severity": str(payload.get("severity") or "low"),
                "title": str(payload.get("title") or ""),
                "description": str(payload.get("description") or ""),
                "evidence_json": json.dumps(_as_json_compatible(evidence), default=str),
            }
        )
    return normalized


def _normalize_cost_snapshot(cost_result: Any) -> dict[str, Any] | None:
    if cost_result is None:
        return None

    payload = _as_mapping(cost_result)
    breakdown = _as_mapping(payload.get("breakdown"))
    comparison = _as_mapping(payload.get("comparison"))
    if not breakdown and not comparison:
        return None

    return {
        "id": str(uuid4()),
        "dedicated_monthly_usd": _to_float(breakdown.get("dedicated_total_monthly_cost_usd")),
        "serverless_monthly_usd": _to_float(breakdown.get("serverless_total_monthly_cost_usd")),
        "lower_cost_option": comparison.get("lower_cost_option"),
    }


def _normalize_recommendations(recommendations: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for recommendation in _as_list(recommendations):
        payload = _as_mapping(recommendation)
        normalized.append(
            {
                "id": str(uuid4()),
                "title": str(payload.get("title") or ""),
                "category": str(payload.get("category") or "general"),
                "priority": str(payload.get("priority") or "medium"),
                "effort": str(
                    payload.get("effort")
                    or _infer_effort_from_tradeoffs(payload.get("tradeoffs"))
                    or "medium"
                ),
            }
        )
    return normalized


def _infer_effort_from_tradeoffs(tradeoffs: Any) -> str | None:
    for item in _as_list(tradeoffs):
        if not isinstance(item, str):
            continue
        lowered = item.lower()
        if "effort:" not in lowered:
            continue
        return lowered.split("effort:", maxsplit=1)[1].strip(" .")
    return None


def _highest_severity(findings: list[dict[str, Any]]) -> str:
    return max(
        (str(finding.get("severity") or "low") for finding in findings),
        key=lambda item: _SEVERITY_ORDER.get(item, -1),
        default="low",
    )


def _extract_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, str) and value:
        return value
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def _as_json_compatible(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _as_json_compatible(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_as_json_compatible(item) for item in value]
    if isinstance(value, tuple):
        return [_as_json_compatible(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _as_mapping(value: Any) -> dict[str, Any]:
    payload = _as_json_compatible(value)
    return payload if isinstance(payload, dict) else {}


def _as_list(value: Any) -> list[Any]:
    payload = _as_json_compatible(value)
    return payload if isinstance(payload, list) else []
