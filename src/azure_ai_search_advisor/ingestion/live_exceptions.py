"""Exceptions used by live Azure ingestion clients."""

from __future__ import annotations


class AzureLiveIngestionError(RuntimeError):
    """Base error for live Azure ingestion failures."""


class AzureCredentialsUnavailableError(AzureLiveIngestionError):
    """Raised when DefaultAzureCredential cannot authenticate to Azure."""


class AzureResourceDiscoveryError(AzureLiveIngestionError):
    """Raised when Azure Resource Graph discovery fails."""


class AzureSearchManagementError(AzureLiveIngestionError):
    """Raised when management API ingestion fails."""


class AzureSearchServiceNotFoundError(AzureSearchManagementError):
    """Raised when a requested Azure AI Search service cannot be found."""
