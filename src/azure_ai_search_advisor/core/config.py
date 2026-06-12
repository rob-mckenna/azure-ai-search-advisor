"""Application configuration scaffold."""

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime configuration for service integrations."""

    azure_ai_foundry_endpoint: str = Field(
        default="https://your-project.services.ai.azure.com/",
        description="TODO: Replace with environment-backed Microsoft Foundry project endpoint.",
    )
    azure_ai_foundry_model: str = Field(
        default="gpt-4o",
        description="TODO: Replace with environment-backed model deployment name.",
    )
