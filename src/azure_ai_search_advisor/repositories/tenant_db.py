"""SQLite-backed tenant persistence."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from azure_ai_search_advisor.core.tenancy import (
    AnalysisHistoryEntry,
    LOCAL_TENANT_ID,
    LOCAL_TENANT_NAME,
    ServiceRegistration,
    TeamMember,
    Tenant,
    TenantRole,
)


class TenantDbRepository:
    """Persist tenants, team members, services, and tenant history in SQLite."""

    def __init__(self, db_path: str | os.PathLike[str] | None = None) -> None:
        self._db_path = str(db_path or os.environ.get("TENANT_DB_PATH", "data/tenants.db"))
        self._is_uri = self._db_path.startswith("file:")
        if not self._is_uri and self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def create_tenant(self, name: str) -> Tenant:
        """Create a new tenant."""

        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Tenant name cannot be empty.")

        tenant = Tenant(id=uuid4(), name=normalized_name, created_at=_utcnow())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO tenants (id, name, created_at) VALUES (?, ?, ?)",
                (str(tenant.id), tenant.name, _serialize_datetime(tenant.created_at)),
            )
        return tenant

    def ensure_local_tenant(self) -> Tenant:
        """Ensure the default local-development tenant exists."""

        existing = self.get_tenant(LOCAL_TENANT_ID)
        if existing is not None:
            return existing

        tenant = Tenant(id=LOCAL_TENANT_ID, name=LOCAL_TENANT_NAME, created_at=_utcnow())
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO tenants (id, name, created_at) VALUES (?, ?, ?)",
                (str(tenant.id), tenant.name, _serialize_datetime(tenant.created_at)),
            )
        return self.get_tenant(LOCAL_TENANT_ID) or tenant

    def get_tenant(self, tenant_id: UUID | str) -> Tenant | None:
        """Fetch a tenant by identifier."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, created_at FROM tenants WHERE id = ?",
                (str(tenant_id),),
            ).fetchone()
        return _row_to_tenant(row) if row else None

    def add_member(
        self,
        tenant_id: UUID | str,
        user_oid: str,
        role: TenantRole,
        display_name: str | None,
        email: str | None = None,
    ) -> TeamMember:
        """Add a user to a tenant."""

        normalized_user_oid = user_oid.strip()
        if not normalized_user_oid:
            raise ValueError("User object id cannot be empty.")

        member = TeamMember(
            id=uuid4(),
            tenant_id=UUID(str(tenant_id)),
            user_oid=normalized_user_oid,
            role=role,
            display_name=(display_name or "").strip() or None,
            email=(email or "").strip() or None,
            added_at=_utcnow(),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO team_members (id, tenant_id, user_oid, role, display_name, email, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(member.id),
                    str(member.tenant_id),
                    member.user_oid,
                    member.role,
                    member.display_name,
                    member.email,
                    _serialize_datetime(member.added_at),
                ),
            )
        return member

    def list_members(self, tenant_id: UUID | str) -> list[TeamMember]:
        """List all members for a tenant."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, tenant_id, user_oid, role, display_name, email, added_at
                FROM team_members
                WHERE tenant_id = ?
                ORDER BY added_at ASC, display_name ASC, user_oid ASC
                """,
                (str(tenant_id),),
            ).fetchall()
        return [_row_to_member(row) for row in rows]

    def get_member_for_user(self, user_oid: str) -> TeamMember | None:
        """Return the tenant membership for the given user, if any."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, tenant_id, user_oid, role, display_name, email, added_at
                FROM team_members
                WHERE user_oid = ?
                LIMIT 1
                """,
                (user_oid.strip(),),
            ).fetchone()
        return _row_to_member(row) if row else None

    def get_tenant_for_user(self, user_oid: str) -> Tenant | None:
        """Return the tenant for the given user, if one exists."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT t.id, t.name, t.created_at
                FROM tenants t
                JOIN team_members tm ON tm.tenant_id = t.id
                WHERE tm.user_oid = ?
                LIMIT 1
                """,
                (user_oid.strip(),),
            ).fetchone()
        return _row_to_tenant(row) if row else None

    def list_services(self, tenant_id: UUID | str) -> list[ServiceRegistration]:
        """List tenant-registered Azure AI Search services."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, tenant_id, subscription_id, resource_group, service_name, added_by, added_at
                FROM service_registrations
                WHERE tenant_id = ?
                ORDER BY added_at DESC, service_name ASC
                """,
                (str(tenant_id),),
            ).fetchall()
        return [_row_to_service(row) for row in rows]

    def register_service(
        self,
        tenant_id: UUID | str,
        subscription_id: str,
        resource_group: str,
        service_name: str,
        added_by: str,
    ) -> ServiceRegistration:
        """Register an Azure AI Search service for a tenant."""

        registration = ServiceRegistration(
            id=uuid4(),
            tenant_id=UUID(str(tenant_id)),
            subscription_id=subscription_id.strip(),
            resource_group=resource_group.strip(),
            service_name=service_name.strip(),
            added_by=added_by.strip(),
            added_at=_utcnow(),
        )
        if not registration.subscription_id or not registration.resource_group or not registration.service_name:
            raise ValueError("Service registration fields cannot be empty.")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO service_registrations (
                    id, tenant_id, subscription_id, resource_group, service_name, added_by, added_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(registration.id),
                    str(registration.tenant_id),
                    registration.subscription_id,
                    registration.resource_group,
                    registration.service_name,
                    registration.added_by,
                    _serialize_datetime(registration.added_at),
                ),
            )
        return registration

    def remove_service(self, tenant_id: UUID | str, service_id: UUID | str) -> bool:
        """Delete a tenant service registration."""

        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM service_registrations WHERE tenant_id = ? AND id = ?",
                (str(tenant_id), str(service_id)),
            )
        return cursor.rowcount > 0

    def record_history(
        self,
        tenant_id: UUID | str,
        subscription_id: str,
        resource_group: str,
        service_name: str,
        analyzed_by: str,
    ) -> AnalysisHistoryEntry:
        """Persist a live analysis execution for the tenant."""

        entry = AnalysisHistoryEntry(
            id=uuid4(),
            tenant_id=UUID(str(tenant_id)),
            subscription_id=subscription_id.strip(),
            resource_group=resource_group.strip(),
            service_name=service_name.strip(),
            analyzed_by=analyzed_by.strip(),
            analyzed_at=_utcnow(),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO analysis_history (
                    id, tenant_id, subscription_id, resource_group, service_name, analyzed_by, analyzed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(entry.id),
                    str(entry.tenant_id),
                    entry.subscription_id,
                    entry.resource_group,
                    entry.service_name,
                    entry.analyzed_by,
                    _serialize_datetime(entry.analyzed_at),
                ),
            )
        return entry

    def list_history(self, tenant_id: UUID | str) -> list[AnalysisHistoryEntry]:
        """List live analysis history for a tenant."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, tenant_id, subscription_id, resource_group, service_name, analyzed_by, analyzed_at
                FROM analysis_history
                WHERE tenant_id = ?
                ORDER BY analyzed_at DESC, service_name ASC
                """,
                (str(tenant_id),),
            ).fetchall()
        return [_row_to_history_entry(row) for row in rows]

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS team_members (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    user_oid TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'member', 'viewer')),
                    display_name TEXT,
                    email TEXT,
                    added_at TEXT NOT NULL,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_team_members_tenant_id
                    ON team_members (tenant_id);

                CREATE TABLE IF NOT EXISTS service_registrations (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subscription_id TEXT NOT NULL,
                    resource_group TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    added_by TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
                    UNIQUE (tenant_id, subscription_id, resource_group, service_name)
                );

                CREATE INDEX IF NOT EXISTS idx_service_registrations_tenant_id
                    ON service_registrations (tenant_id);

                CREATE TABLE IF NOT EXISTS analysis_history (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subscription_id TEXT NOT NULL,
                    resource_group TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    analyzed_by TEXT NOT NULL,
                    analyzed_at TEXT NOT NULL,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_analysis_history_tenant_id
                    ON analysis_history (tenant_id, analyzed_at DESC);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path, uri=self._is_uri)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        return connection


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(str(value))


def _row_to_tenant(row: sqlite3.Row) -> Tenant:
    return Tenant(
        id=UUID(row["id"]),
        name=str(row["name"]),
        created_at=_parse_datetime(row["created_at"]) or _utcnow(),
    )


def _row_to_member(row: sqlite3.Row) -> TeamMember:
    return TeamMember(
        id=UUID(row["id"]),
        tenant_id=UUID(row["tenant_id"]),
        user_oid=str(row["user_oid"]),
        role=str(row["role"]),  # type: ignore[arg-type]
        display_name=str(row["display_name"]) if row["display_name"] is not None else None,
        email=str(row["email"]) if row["email"] is not None else None,
        added_at=_parse_datetime(row["added_at"]),
    )


def _row_to_service(row: sqlite3.Row) -> ServiceRegistration:
    return ServiceRegistration(
        id=UUID(row["id"]),
        tenant_id=UUID(row["tenant_id"]),
        subscription_id=str(row["subscription_id"]),
        resource_group=str(row["resource_group"]),
        service_name=str(row["service_name"]),
        added_by=str(row["added_by"]),
        added_at=_parse_datetime(row["added_at"]) or _utcnow(),
    )


def _row_to_history_entry(row: sqlite3.Row) -> AnalysisHistoryEntry:
    return AnalysisHistoryEntry(
        id=UUID(row["id"]),
        tenant_id=UUID(row["tenant_id"]),
        subscription_id=str(row["subscription_id"]),
        resource_group=str(row["resource_group"]),
        service_name=str(row["service_name"]),
        analyzed_by=str(row["analyzed_by"]),
        analyzed_at=_parse_datetime(row["analyzed_at"]) or _utcnow(),
    )
