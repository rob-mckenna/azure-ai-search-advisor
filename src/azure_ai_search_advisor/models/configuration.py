"""Pydantic models for Azure AI Search service configuration."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, root_validator, validator

from azure_ai_search_advisor.models.base import AdvisorModel


class DeploymentMode(StrEnum):
    """Search service deployment modes."""

    DEDICATED = "dedicated"
    SERVERLESS = "serverless"


class SearchSku(StrEnum):
    """Supported Azure AI Search SKUs."""

    FREE = "free"
    BASIC = "basic"
    S1 = "s1"
    S2 = "s2"
    S3 = "s3"
    S3_HD = "s3_hd"
    L1 = "l1"
    L2 = "l2"


class SearchFeature(StrEnum):
    """Customer-visible Azure AI Search features."""

    AI_ENRICHMENT = "ai_enrichment"
    AVAILABILITY_ZONES = "availability_zones"
    INDEXERS = "indexers"
    KNOWLEDGE_STORE = "knowledge_store"
    MANAGED_IDENTITY = "managed_identity"
    PRIVATE_ENDPOINTS = "private_endpoints"
    SEMANTIC_RANKER = "semantic_ranker"
    VECTOR_SEARCH = "vector_search"


class VectorSearchAlgorithm(StrEnum):
    """Vector search algorithms used by Azure AI Search."""

    EXHAUSTIVE_KNN = "exhaustive_knn"
    HNSW = "hnsw"


class VectorizerType(StrEnum):
    """Vectorizer types used for integrated vectorization."""

    NONE = "none"
    AZURE_OPENAI = "azure_openai"
    CUSTOM_WEB_API = "custom_web_api"


class SemanticRankerConfiguration(AdvisorModel):
    """Semantic ranker configuration."""

    enabled: bool = False
    default_configuration_name: str | None = Field(
        default=None,
        description="Default semantic configuration applied to queries.",
    )
    query_cap_per_month: int | None = Field(
        default=None,
        ge=0,
        description="Expected monthly query allowance for semantic ranking.",
    )
    prioritized_fields_configured: bool = False

    @root_validator(skip_on_failure=True)
    def validate_enabled_state(cls, values: dict) -> dict:
        """Ensure semantic details are only set when enabled."""
        if not values.get("enabled") and (
            values.get("default_configuration_name") is not None
            or values.get("query_cap_per_month") is not None
            or values.get("prioritized_fields_configured")
        ):
            raise ValueError(
                "Semantic ranker details can only be set when semantic ranker is enabled."
            )
        return values


class VectorSearchConfiguration(AdvisorModel):
    """Vector search configuration."""

    enabled: bool = False
    algorithm: VectorSearchAlgorithm | None = None
    profile_count: int = Field(default=0, ge=0)
    vectorizer: VectorizerType = VectorizerType.NONE
    integrated_vectorization_enabled: bool = False
    vector_index_count: int = Field(default=0, ge=0)

    @root_validator(skip_on_failure=True)
    def validate_enabled_state(cls, values: dict) -> dict:
        """Ensure vector details are internally consistent."""
        if not values.get("enabled"):
            if (
                values.get("algorithm") is not None
                or values.get("profile_count") != 0
                or values.get("vectorizer") != VectorizerType.NONE
                or values.get("integrated_vectorization_enabled")
                or values.get("vector_index_count") != 0
            ):
                raise ValueError(
                    "Vector search details can only be set when vector search is enabled."
                )
            return values

        if values.get("algorithm") is None:
            raise ValueError("Vector search algorithm is required when vector search is enabled.")
        if values.get("integrated_vectorization_enabled") and (
            values.get("vectorizer") == VectorizerType.NONE
        ):
            raise ValueError(
                "A vectorizer type is required when integrated vectorization is enabled."
            )
        return values


class AIEnrichmentConfiguration(AdvisorModel):
    """AI enrichment configuration."""

    enabled: bool = False
    skillset_count: int = Field(default=0, ge=0)
    knowledge_store_enabled: bool = False
    cognitive_services_attached: bool = False
    image_extraction_enabled: bool = False
    custom_skill_count: int = Field(default=0, ge=0)

    @root_validator(skip_on_failure=True)
    def validate_enabled_state(cls, values: dict) -> dict:
        """Ensure enrichment details are only set when enabled."""
        if not values.get("enabled"):
            if (
                values.get("skillset_count") != 0
                or values.get("knowledge_store_enabled")
                or values.get("cognitive_services_attached")
                or values.get("image_extraction_enabled")
                or values.get("custom_skill_count") != 0
            ):
                raise ValueError(
                    "AI enrichment details can only be set when AI enrichment is enabled."
                )
            return values

        if values.get("skillset_count") == 0:
            raise ValueError("AI enrichment requires at least one skillset.")
        return values


class AzureSearchServiceConfiguration(AdvisorModel):
    """Azure AI Search service configuration contract."""

    service_name: str
    subscription_id: str
    resource_group: str
    location: str
    deployment_mode: DeploymentMode = DeploymentMode.DEDICATED
    sku: SearchSku
    replicas: int | None = Field(default=None, ge=1)
    partitions: int | None = Field(default=None, ge=1)
    high_density: bool = False
    availability_zones_enabled: bool = False
    private_endpoint_enabled: bool = False
    public_network_access_enabled: bool = True
    managed_identity_enabled: bool = True
    index_count: int = Field(default=0, ge=0)
    indexer_count: int = Field(default=0, ge=0)
    data_source_count: int = Field(default=0, ge=0)
    skillset_count: int = Field(default=0, ge=0)
    features_enabled: list[SearchFeature] = Field(default_factory=list)
    semantic_ranker: SemanticRankerConfiguration = Field(
        default_factory=SemanticRankerConfiguration
    )
    vector_search: VectorSearchConfiguration = Field(default_factory=VectorSearchConfiguration)
    ai_enrichment: AIEnrichmentConfiguration = Field(default_factory=AIEnrichmentConfiguration)

    @validator("features_enabled")
    def validate_unique_features(cls, features: list[SearchFeature]) -> list[SearchFeature]:
        """Prevent duplicate feature flags."""
        if len(features) != len(set(features)):
            raise ValueError("features_enabled must not contain duplicates.")
        return features

    @property
    def search_units(self) -> int | None:
        """Dedicated service search units."""
        if self.replicas is None or self.partitions is None:
            return None
        return self.replicas * self.partitions

    @root_validator(skip_on_failure=True)
    def validate_configuration(cls, values: dict) -> dict:
        """Validate configuration coherence across related fields."""
        enabled_features = set(values.get("features_enabled", []))
        deployment_mode = values.get("deployment_mode")
        replicas = values.get("replicas")
        partitions = values.get("partitions")
        high_density = values.get("high_density")
        sku = values.get("sku")
        semantic_ranker = values.get("semantic_ranker")
        vector_search = values.get("vector_search")
        ai_enrichment = values.get("ai_enrichment")
        indexer_count = values.get("indexer_count", 0)
        skillset_count = values.get("skillset_count", 0)
        private_endpoint_enabled = values.get("private_endpoint_enabled")
        availability_zones_enabled = values.get("availability_zones_enabled")

        if deployment_mode == DeploymentMode.DEDICATED:
            if replicas is None or partitions is None:
                raise ValueError(
                    "Dedicated services must declare replica and partition counts."
                )
        elif replicas is not None or partitions is not None:
            raise ValueError(
                "Serverless services should not declare replica or partition counts."
            )

        if high_density and sku != SearchSku.S3_HD:
            raise ValueError("High-density hosting is only valid for the s3_hd SKU.")

        feature_expectations = {
            SearchFeature.SEMANTIC_RANKER: semantic_ranker.enabled,
            SearchFeature.VECTOR_SEARCH: vector_search.enabled,
            SearchFeature.AI_ENRICHMENT: ai_enrichment.enabled,
        }
        for feature, enabled in feature_expectations.items():
            if enabled and feature not in enabled_features:
                raise ValueError(f"{feature.value} must be listed in features_enabled.")
            if not enabled and feature in enabled_features:
                raise ValueError(
                    f"{feature.value} is listed in features_enabled but its configuration is disabled."
                )

        if ai_enrichment.skillset_count > skillset_count:
            raise ValueError(
                "ai_enrichment.skillset_count cannot exceed the service-level skillset_count."
            )

        if indexer_count > 0 and SearchFeature.INDEXERS not in enabled_features:
            raise ValueError("Indexers must be listed in features_enabled when indexer_count > 0.")

        if ai_enrichment.knowledge_store_enabled and (
            SearchFeature.KNOWLEDGE_STORE not in enabled_features
        ):
            raise ValueError(
                "knowledge_store must be listed in features_enabled when knowledge store is enabled."
            )

        if private_endpoint_enabled and (
            SearchFeature.PRIVATE_ENDPOINTS not in enabled_features
        ):
            raise ValueError(
                "private_endpoints must be listed in features_enabled when private endpoints are enabled."
            )

        if availability_zones_enabled and (
            SearchFeature.AVAILABILITY_ZONES not in enabled_features
        ):
            raise ValueError(
                "availability_zones must be listed in features_enabled when availability zones are enabled."
            )

        return values
