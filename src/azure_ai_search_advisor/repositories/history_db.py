"""SQLite-backed persistence for historical analysis runs."""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

class HistoryDatabase:
    """Persist and query advisor history in a local SQLite database."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        resolved_path = Path(db_path or os.environ.get("HISTORY_DB_PATH", "data/history.db"))
        self._db_path = resolved_path.expanduser()
        self._schema_lock = threading.Lock()
        self._initialized = False

    @property
    def db_path(self) -> Path:
        """Return the configured database path."""

        return self._db_path

    def insert_analysis_run(
        self,
        analysis_run: dict[str, Any],
        findings: list[dict[str, Any]],
        cost_snapshot: dict[str, Any] | None,
        recommendations: list[dict[str, Any]],
    ) -> None:
        """Insert a full analysis run and its related child records."""

        self._ensure_initialized()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO analysis_runs (
                    id,
                    tenant_id,
                    service_name,
                    subscription_id,
                    resource_group,
                    run_at,
                    finding_count,
                    highest_severity,
                    configuration_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_run["id"],
                    analysis_run["tenant_id"],
                    analysis_run["service_name"],
                    analysis_run["subscription_id"],
                    analysis_run["resource_group"],
                    analysis_run["run_at"],
                    analysis_run["finding_count"],
                    analysis_run["highest_severity"],
                    analysis_run["configuration_hash"],
                ),
            )
            connection.executemany(
                """
                INSERT INTO findings_history (
                    id,
                    run_id,
                    category,
                    severity,
                    title,
                    description,
                    evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        finding["id"],
                        analysis_run["id"],
                        finding["category"],
                        finding["severity"],
                        finding["title"],
                        finding["description"],
                        finding["evidence_json"],
                    )
                    for finding in findings
                ],
            )
            if cost_snapshot is not None:
                connection.execute(
                    """
                    INSERT INTO cost_snapshots (
                        id,
                        run_id,
                        dedicated_monthly_usd,
                        serverless_monthly_usd,
                        lower_cost_option
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        cost_snapshot["id"],
                        analysis_run["id"],
                        cost_snapshot["dedicated_monthly_usd"],
                        cost_snapshot["serverless_monthly_usd"],
                        cost_snapshot["lower_cost_option"],
                    ),
                )
            connection.executemany(
                """
                INSERT INTO recommendations_history (
                    id,
                    run_id,
                    title,
                    category,
                    priority,
                    effort
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        recommendation["id"],
                        analysis_run["id"],
                        recommendation["title"],
                        recommendation["category"],
                        recommendation["priority"],
                        recommendation["effort"],
                    )
                    for recommendation in recommendations
                ],
            )

    def fetch_history(
        self,
        service_name: str,
        *,
        tenant_id: str,
        days: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch summarized history rows for a single service."""

        self._ensure_initialized()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    ar.id,
                    ar.service_name,
                    ar.subscription_id,
                    ar.resource_group,
                    ar.run_at,
                    ar.finding_count,
                    ar.highest_severity,
                    ar.configuration_hash,
                    cs.dedicated_monthly_usd,
                    cs.serverless_monthly_usd,
                    cs.lower_cost_option,
                    (
                        SELECT COUNT(*)
                        FROM recommendations_history rh
                        WHERE rh.run_id = ar.id
                    ) AS recommendation_count
                FROM analysis_runs ar
                LEFT JOIN cost_snapshots cs ON cs.run_id = ar.id
                WHERE ar.tenant_id = ?
                  AND ar.service_name = ?
                  AND datetime(ar.run_at) >= datetime('now', ?)
                ORDER BY datetime(ar.run_at) DESC
                LIMIT ?
                """,
                (tenant_id, service_name, f"-{days} days", limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def fetch_trends(
        self,
        service_name: str,
        *,
        tenant_id: str,
        days: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch trend rows ordered from oldest to newest."""

        self._ensure_initialized()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    ar.run_at,
                    ar.finding_count,
                    cs.dedicated_monthly_usd,
                    cs.serverless_monthly_usd,
                    cs.lower_cost_option
                FROM analysis_runs ar
                LEFT JOIN cost_snapshots cs ON cs.run_id = ar.id
                WHERE ar.tenant_id = ?
                  AND ar.service_name = ?
                  AND datetime(ar.run_at) >= datetime('now', ?)
                ORDER BY datetime(ar.run_at) ASC
                LIMIT ?
                """,
                (tenant_id, service_name, f"-{days} days", limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def fetch_latest(self, service_name: str, *, tenant_id: str) -> dict[str, Any] | None:
        """Fetch the most recent run with child records."""

        self._ensure_initialized()
        with self._connect() as connection:
            run = connection.execute(
                """
                SELECT
                    ar.id,
                    ar.service_name,
                    ar.subscription_id,
                    ar.resource_group,
                    ar.run_at,
                    ar.finding_count,
                    ar.highest_severity,
                    ar.configuration_hash,
                    cs.dedicated_monthly_usd,
                    cs.serverless_monthly_usd,
                    cs.lower_cost_option
                FROM analysis_runs ar
                LEFT JOIN cost_snapshots cs ON cs.run_id = ar.id
                WHERE ar.tenant_id = ?
                  AND ar.service_name = ?
                ORDER BY datetime(ar.run_at) DESC
                LIMIT 1
                """,
                (tenant_id, service_name),
            ).fetchone()
            if run is None:
                return None

            findings = connection.execute(
                """
                SELECT category, severity, title, description, evidence_json
                FROM findings_history
                WHERE run_id = ?
                ORDER BY rowid ASC
                """,
                (run["id"],),
            ).fetchall()
            recommendations = connection.execute(
                """
                SELECT title, category, priority, effort
                FROM recommendations_history
                WHERE run_id = ?
                ORDER BY rowid ASC
                """,
                (run["id"],),
            ).fetchall()

        payload = dict(run)
        payload["findings"] = [dict(row) for row in findings]
        payload["recommendations"] = [dict(row) for row in recommendations]
        return payload

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        with self._schema_lock:
            if self._initialized:
                return
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS analysis_runs (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
                        service_name TEXT NOT NULL,
                        subscription_id TEXT NOT NULL,
                        resource_group TEXT NOT NULL,
                        run_at TEXT NOT NULL,
                        finding_count INTEGER NOT NULL,
                        highest_severity TEXT NOT NULL,
                        configuration_hash TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS findings_history (
                        id TEXT PRIMARY KEY,
                        run_id TEXT NOT NULL,
                        category TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL,
                        evidence_json TEXT NOT NULL,
                        FOREIGN KEY (run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS cost_snapshots (
                        id TEXT PRIMARY KEY,
                        run_id TEXT NOT NULL,
                        dedicated_monthly_usd REAL,
                        serverless_monthly_usd REAL,
                        lower_cost_option TEXT,
                        FOREIGN KEY (run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS recommendations_history (
                        id TEXT PRIMARY KEY,
                        run_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        category TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        effort TEXT NOT NULL,
                        FOREIGN KEY (run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS idx_analysis_runs_service_time
                        ON analysis_runs(tenant_id, service_name, run_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_findings_history_run_id
                        ON findings_history(run_id);
                    CREATE INDEX IF NOT EXISTS idx_cost_snapshots_run_id
                        ON cost_snapshots(run_id);
                    CREATE INDEX IF NOT EXISTS idx_recommendations_history_run_id
                        ON recommendations_history(run_id);
                    """
                )
                columns = {
                    row["name"]
                    for row in connection.execute("PRAGMA table_info(analysis_runs)").fetchall()
                }
                if "tenant_id" not in columns:
                    connection.execute(
                        """
                        ALTER TABLE analysis_runs
                        ADD COLUMN tenant_id TEXT NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001'
                        """
                    )
            self._initialized = True

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
