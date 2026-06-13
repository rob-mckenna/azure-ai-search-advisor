"""Application configuration."""

import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime configuration for service integrations."""

    azure_ai_foundry_endpoint: str = Field(
        default_factory=lambda: os.environ.get(
            "AZURE_AI_FOUNDRY_ENDPOINT", "https://your-project.services.ai.azure.com/"
        ),
        description="Microsoft Foundry project endpoint (set via AZURE_AI_FOUNDRY_ENDPOINT env var).",
    )
    azure_ai_foundry_model: str = Field(
        default_factory=lambda: os.environ.get("AZURE_AI_FOUNDRY_MODEL", "gpt-4o"),
        description="Model deployment name within the Foundry project (set via AZURE_AI_FOUNDRY_MODEL env var).",
    )
    auth_enabled: bool = Field(
        default_factory=lambda: os.environ.get("AUTH_ENABLED", "true").lower() == "true",
        description="Whether to enforce Entra ID authentication on protected endpoints.",
    )
