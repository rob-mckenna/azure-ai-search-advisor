"""Ingestion domain package."""

from azure_ai_search_advisor.ingestion.live_ingestion_service import LiveIngestionService
from azure_ai_search_advisor.ingestion.service import IngestionService

__all__ = ["IngestionService", "LiveIngestionService"]
