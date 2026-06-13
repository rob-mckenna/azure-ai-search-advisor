"""Core tenant and team scoping models."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TYPE_CHECKING
from uuid import UUID

from azure_ai_search_advisor.api.auth import CurrentUser

if TYPE_CHECKING:
    from azure_ai_search_advisor.repositories.tenant_db import TenantDbRepository

TenantRole = Literal["admin", "member", "viewer"]

LOCAL_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
LOCAL_TENANT_NAME = "local"

ROLE_PERMISSIONS: dict[TenantRole, frozenset[str]] = {
    "admin": frozenset({"members:manage", "services:manage", "services:view", "services:analyze", "history:view"}),
    "member": frozenset({"services:view", "services:analyze", "history:view"}),
    "viewer": frozenset({"services:view", "history:view"}),
}


@dataclass(frozen=True, slots=True)
class Tenant:
    """Tenant or organization boundary."""

    id: UUID
    name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class TeamMember:
    """Team membership within a tenant."""

    id: UUID
    tenant_id: UUID
    user_oid: str
    role: TenantRole
    display_name: str | None = None
    email: str | None = None
    added_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ServiceRegistration:
    """Tenant-scoped Azure AI Search service registration."""

    id: UUID
    tenant_id: UUID
    subscription_id: str
    resource_group: str
    service_name: str
    added_by: str
    added_at: datetime


@dataclass(frozen=True, slots=True)
class AnalysisHistoryEntry:
    """Recorded live analysis execution for a tenant."""

    id: UUID
    tenant_id: UUID
    subscription_id: str
    resource_group: str
    service_name: str
    analyzed_by: str
    analyzed_at: datetime


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Resolved tenant context for the current request."""

    current_tenant: Tenant
    current_user: CurrentUser
    permissions: frozenset[str]
    membership: TeamMember | None = None

    @property
    def role(self) -> TenantRole:
        """Return the effective tenant role for the current user."""

        return self.membership.role if self.membership is not None else "admin"

    def can(self, permission: str) -> bool:
        """Return whether the current user may perform the named action."""

        return permission in self.permissions


def get_tenant_context(
    user: CurrentUser,
    tenant_db: TenantDbRepository | None = None,
    *,
    allow_local_fallback: bool | None = None,
) -> TenantContext:
    """Resolve the request tenant context from the current user."""

    if tenant_db is None:
        from azure_ai_search_advisor.repositories.tenant_db import TenantDbRepository

        tenant_db = TenantDbRepository(os.environ.get("TENANT_DB_PATH", "data/tenants.db"))

    if allow_local_fallback is None:
        allow_local_fallback = os.environ.get("AUTH_ENABLED", "false").strip().lower() != "true"

    user_oid = user.oid or user.sub
    membership = tenant_db.get_member_for_user(user_oid)
    if membership is not None:
        tenant = tenant_db.get_tenant(membership.tenant_id)
        if tenant is None:
            raise LookupError(f"Tenant '{membership.tenant_id}' is missing for user '{user_oid}'.")
        return TenantContext(
            current_tenant=tenant,
            current_user=user,
            permissions=ROLE_PERMISSIONS[membership.role],
            membership=membership,
        )

    if allow_local_fallback:
        return TenantContext(
            current_tenant=tenant_db.ensure_local_tenant(),
            current_user=user,
            permissions=ROLE_PERMISSIONS["admin"],
        )

    raise LookupError(f"No tenant membership exists for user '{user_oid}'.")
