"""Persistence abstractions for advisor data."""

from azure_ai_search_advisor.repositories.json_repository import JsonRepository
from azure_ai_search_advisor.repositories.tenant_db import TenantDbRepository

__all__ = ["JsonRepository", "TenantDbRepository"]
