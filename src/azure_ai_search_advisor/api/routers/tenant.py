"""Tenant management endpoints."""

from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status

from azure_ai_search_advisor.api.auth import CurrentUser, get_current_user
from azure_ai_search_advisor.api.dependencies import get_tenant, get_tenant_db
from azure_ai_search_advisor.api.schemas import (
    CreateTenantRequest,
    ErrorResponse,
    ServiceRegistrationRequest,
    ServiceRegistrationResponse,
    TenantContextResponse,
    TenantMemberRequest,
    TenantMemberResponse,
    TenantMembersResponse,
    TenantRole,
    TenantServicesResponse,
    TenantSummary,
)
from azure_ai_search_advisor.core.tenancy import ServiceRegistration, TeamMember, TenantContext
from azure_ai_search_advisor.repositories.tenant_db import TenantDbRepository

router = APIRouter(prefix="/tenant", tags=["tenancy"])


@router.post(
    "",
    response_model=TenantContextResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tenant",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "The current user already belongs to a tenant.",
        }
    },
)
def create_tenant(
    request: CreateTenantRequest,
    current_user: CurrentUser = Depends(get_current_user),
    tenant_db: TenantDbRepository = Depends(get_tenant_db),
) -> TenantContextResponse:
    """Create a new tenant and assign the caller as an admin."""

    user_oid = current_user.oid or current_user.sub
    if tenant_db.get_tenant_for_user(user_oid) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The current user already belongs to a tenant.",
        )

    try:
        tenant = tenant_db.create_tenant(request.name)
        membership = tenant_db.add_member(
            tenant.id,
            user_oid=user_oid,
            role="admin",
            display_name=current_user.name,
            email=current_user.email,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The current user already belongs to a tenant.",
        ) from exc

    return _to_tenant_context_response(
        TenantContext(
            current_tenant=tenant,
            current_user=current_user,
            permissions=frozenset({"members:manage", "services:manage", "services:view", "services:analyze", "history:view"}),
            membership=membership,
        )
    )


@router.get(
    "",
    response_model=TenantContextResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the current tenant",
)
def get_current_tenant(
    tenant_context: TenantContext = Depends(get_tenant),
) -> TenantContextResponse:
    """Return the current tenant context."""

    return _to_tenant_context_response(tenant_context)


@router.post(
    "/members",
    response_model=TenantMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to the current tenant",
    responses={
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "Only tenant admins can add members.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "The requested user already belongs to a tenant.",
        },
    },
)
def add_tenant_member(
    request: TenantMemberRequest,
    tenant_context: TenantContext = Depends(get_tenant),
    tenant_db: TenantDbRepository = Depends(get_tenant_db),
) -> TenantMemberResponse:
    """Add a member to the current tenant."""

    _require_permission(tenant_context, "members:manage", "Only tenant admins can add members.")
    try:
        member = tenant_db.add_member(
            tenant_context.current_tenant.id,
            user_oid=request.user_oid,
            role=request.role.value,
            display_name=request.display_name,
            email=request.email,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested user already belongs to a tenant.",
        ) from exc
    return _to_member_response(member)


@router.get(
    "/members",
    response_model=TenantMembersResponse,
    status_code=status.HTTP_200_OK,
    summary="List tenant members",
)
def list_tenant_members(
    tenant_context: TenantContext = Depends(get_tenant),
    tenant_db: TenantDbRepository = Depends(get_tenant_db),
) -> TenantMembersResponse:
    """List members for the current tenant."""

    return TenantMembersResponse(
        members=[_to_member_response(member) for member in tenant_db.list_members(tenant_context.current_tenant.id)]
    )


@router.post(
    "/services",
    response_model=ServiceRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a search service for the current tenant",
    responses={
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "Only tenant admins can register services.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "The service is already registered for the tenant.",
        },
    },
)
def register_tenant_service(
    request: ServiceRegistrationRequest,
    tenant_context: TenantContext = Depends(get_tenant),
    tenant_db: TenantDbRepository = Depends(get_tenant_db),
) -> ServiceRegistrationResponse:
    """Register an Azure AI Search service for tenant-scoped discovery."""

    _require_permission(tenant_context, "services:manage", "Only tenant admins can register services.")
    try:
        registration = tenant_db.register_service(
            tenant_context.current_tenant.id,
            subscription_id=request.subscription_id,
            resource_group=request.resource_group,
            service_name=request.service_name,
            added_by=tenant_context.current_user.oid or tenant_context.current_user.sub,
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The service is already registered for the tenant.",
        ) from exc
    return _to_service_response(registration)


@router.get(
    "/services",
    response_model=TenantServicesResponse,
    status_code=status.HTTP_200_OK,
    summary="List registered tenant services",
)
def list_tenant_services(
    tenant_context: TenantContext = Depends(get_tenant),
    tenant_db: TenantDbRepository = Depends(get_tenant_db),
) -> TenantServicesResponse:
    """List Azure AI Search services registered for the current tenant."""

    return TenantServicesResponse(
        services=[_to_service_response(service) for service in tenant_db.list_services(tenant_context.current_tenant.id)]
    )


@router.delete(
    "/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a registered tenant service",
    responses={
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "Only tenant admins can unregister services.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "The requested service registration was not found.",
        },
    },
)
def delete_tenant_service(
    service_id: Annotated[str, Path(description="Tenant service registration identifier.")],
    tenant_context: TenantContext = Depends(get_tenant),
    tenant_db: TenantDbRepository = Depends(get_tenant_db),
) -> Response:
    """Unregister a tenant-scoped search service."""

    _require_permission(tenant_context, "services:manage", "Only tenant admins can unregister services.")
    if not tenant_db.remove_service(tenant_context.current_tenant.id, service_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested service registration was not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _require_permission(tenant_context: TenantContext, permission: str, detail: str) -> None:
    if not tenant_context.can(permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _to_tenant_context_response(tenant_context: TenantContext) -> TenantContextResponse:
    return TenantContextResponse(
        tenant=TenantSummary(
            id=tenant_context.current_tenant.id,
            name=tenant_context.current_tenant.name,
            created_at=tenant_context.current_tenant.created_at,
        ),
        current_user_oid=tenant_context.current_user.oid,
        role=TenantRole(tenant_context.role),
        permissions=sorted(tenant_context.permissions),
    )


def _to_member_response(member: TeamMember) -> TenantMemberResponse:
    return TenantMemberResponse(
        id=member.id,
        tenant_id=member.tenant_id,
        user_oid=member.user_oid,
        role=TenantRole(member.role),
        display_name=member.display_name,
        email=member.email,
        added_at=member.added_at,
    )


def _to_service_response(registration: ServiceRegistration) -> ServiceRegistrationResponse:
    return ServiceRegistrationResponse(
        id=registration.id,
        tenant_id=registration.tenant_id,
        subscription_id=registration.subscription_id,
        resource_group=registration.resource_group,
        service_name=registration.service_name,
        added_by=registration.added_by,
        added_at=registration.added_at,
    )
