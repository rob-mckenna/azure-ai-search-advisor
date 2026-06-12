"""Base model definitions for shared contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AdvisorModel(BaseModel):
    """Shared base model for validated Azure AI Search contracts."""

    class Config:
        """Compatibility settings shared across Pydantic versions."""

        anystr_strip_whitespace = True
        allow_population_by_field_name = True
        extra = "forbid"
        validate_assignment = True

    @classmethod
    def model_validate(cls, obj: Any) -> "AdvisorModel":
        """Provide a version-agnostic validation entrypoint."""
        base_validate = getattr(BaseModel, "model_validate", None)
        if callable(base_validate):
            return base_validate.__get__(cls, cls)(obj)
        return cls.parse_obj(obj)
