"""Live Azure AI Search ingestion using the management API and RBAC-authenticated data-plane calls."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
from azure.identity import CredentialUnavailableError, DefaultAzureCredential
from azure.mgmt.search import SearchManagementClient
from azure.mgmt.search.models import SearchService

from azure_ai_search_advisor.ingestion.live_exceptions import (
    AzureCredentialsUnavailableError,
    AzureSearchManagementError,
    AzureSearchServiceNotFoundError,
)
from azure_ai_search_advisor.models import AzureSearchServiceConfiguration, AzureSearchServiceSnapshot
from azure_ai_search_advisor.models.configuration import (
    AIEnrichmentConfiguration,
    DeploymentMode,
    SearchFeature,
    SearchSku,
    SemanticRankerConfiguration,
    VectorSearchAlgorithm,
    VectorSearchConfiguration,
    VectorizerType,
)

SEARCH_DATA_API_VERSION = "2023-11-01"
SEARCH_DATA_SCOPE = "https://search.azure.com/.default"

SKU_NAME_TO_MODEL: dict[str, SearchSku] = {
    "free": SearchSku.FREE,
    "basic": SearchSku.BASIC,
    "standard": SearchSku.S1,
    "standard1": SearchSku.S1,
    "s1": SearchSku.S1,
    "standard2": SearchSku.S2,
    "s2": SearchSku.S2,
    "standard3": SearchSku.S3,
    "s3": SearchSku.S3,
    "standard3_highdensity": SearchSku.S3_HD,
    "s3_hd": SearchSku.S3_HD,
    "storage_optimized_l1": SearchSku.L1,
    "l1": SearchSku.L1,
    "storage_optimized_l2": SearchSku.L2,
    "l2": SearchSku.L2,
}


@dataclass(frozen=True, slots=True)
class AzureSearchManagementSnapshot:
    """Management-plane snapshot before conversion into the public domain model."""

    configuration: AzureSearchServiceConfiguration
    metrics_available: bool
    notes: tuple[str, ...]


class AzureSearchManagementClientAdapter:
    """Loads live Azure AI Search configuration from Azure management endpoints."""

    def __init__(
        self,
        credential: DefaultAzureCredential | None = None,
        *,
        data_api_version: str = SEARCH_DATA_API_VERSION,
    ) -> None:
        self._credential = credential or DefaultAzureCredential()
        self._data_api_version = data_api_version

    def ingest_service(
        self,
        *,
        subscription_id: str,
        resource_group: str,
        service_name: str,
    ) -> AzureSearchServiceSnapshot:
        """Fetch a live Azure AI Search service and convert it into the snapshot model."""

        management_snapshot = self.get_service_snapshot(
            subscription_id=subscription_id,
            resource_group=resource_group,
            service_name=service_name,
        )
        notes = list(management_snapshot.notes)
        if not management_snapshot.metrics_available:
            notes.append(
                "Azure Monitor-style workload metrics were not available from the live ingestion path, "
                "so the snapshot omits metrics and analysis findings may be limited."
            )
        return AzureSearchServiceSnapshot(
            collected_at=datetime.now(timezone.utc),
            configuration=management_snapshot.configuration,
            metrics=None,
            notes=notes,
        )

    def get_service_snapshot(
        self,
        *,
        subscription_id: str,
        resource_group: str,
        service_name: str,
    ) -> AzureSearchManagementSnapshot:
        """Fetch a live search service and convert it into our configuration model."""

        service = self._get_service(subscription_id, resource_group, service_name)
        notes: list[str] = []

        indexes = self._list_search_collection(service.endpoint, "indexes", notes)
        indexers = self._list_search_collection(service.endpoint, "indexers", notes)
        data_sources = self._list_search_collection(service.endpoint, "datasources", notes)
        skillsets = self._list_search_collection(service.endpoint, "skillsets", notes)
        service_stats = self._get_search_document(service.endpoint, "servicestats", notes)
        index_statistics = [
            self._get_search_document(
                service.endpoint,
                f"indexes/{quote(index_name, safe='')}/stats",
                notes,
                note_context=f"index '{index_name}' statistics",
            )
            for index_name in self._extract_index_names(indexes)
        ]

        configuration = self._build_configuration(
            service=service,
            subscription_id=subscription_id,
            resource_group=resource_group,
            indexes=indexes,
            indexers=indexers,
            data_sources=data_sources,
            skillsets=skillsets,
        )

        if service_stats is not None:
            notes.append("Fetched live service statistics via RBAC-authenticated Search REST API.")
        if any(stat is not None for stat in index_statistics):
            notes.append("Fetched per-index statistics via RBAC-authenticated Search REST API.")

        return AzureSearchManagementSnapshot(
            configuration=configuration,
            metrics_available=False,
            notes=tuple(dict.fromkeys(notes)),
        )

    def _get_service(
        self,
        subscription_id: str,
        resource_group: str,
        service_name: str,
    ) -> SearchService:
        try:
            with SearchManagementClient(self._credential, subscription_id) as client:
                return client.services.get(resource_group, service_name)
        except (CredentialUnavailableError, ClientAuthenticationError) as exc:
            raise AzureCredentialsUnavailableError(
                "Azure credentials are unavailable. Configure DefaultAzureCredential "
                "via az login, managed identity, or service principal environment variables."
            ) from exc
        except HttpResponseError as exc:
            if getattr(exc, "status_code", None) == 404:
                raise AzureSearchServiceNotFoundError(
                    f"Azure AI Search service '{service_name}' was not found in "
                    f"resource group '{resource_group}'."
                ) from exc
            raise AzureSearchManagementError(
                f"Azure Search management request failed: {exc.message or exc!s}"
            ) from exc

    def _build_configuration(
        self,
        *,
        service: SearchService,
        subscription_id: str,
        resource_group: str,
        indexes: list[Mapping[str, Any]],
        indexers: list[Mapping[str, Any]],
        data_sources: list[Mapping[str, Any]],
        skillsets: list[Mapping[str, Any]],
    ) -> AzureSearchServiceConfiguration:
        semantic_enabled, semantic_default_name, semantic_prioritized_fields = (
            self._detect_semantic_configuration(indexes, service)
        )
        vector_enabled, vector_algorithm, vector_profile_count, vectorizer, vector_index_count = (
            self._detect_vector_configuration(indexes)
        )
        ai_enrichment_enabled = bool(skillsets)
        knowledge_store_enabled = any(self._has_key(item, "knowledgeStore") for item in skillsets)
        cognitive_services_attached = any(self._has_key(item, "cognitiveServices") for item in skillsets)
        image_extraction_enabled = any(self._contains_text(item, "image") for item in skillsets)
        custom_skill_count = sum(
            1
            for skillset in skillsets
            for skill in self._iter_skillset_skills(skillset)
            if "webapi" in str(skill.get("@odata.type", "")).lower()
        )
        private_endpoint_enabled = bool(getattr(service, "private_endpoint_connections", None))
        managed_identity_enabled = getattr(service, "identity", None) is not None
        availability_zones_enabled = self._has_key(self._to_mapping(service.network_rule_set), "availabilityZones")
        public_network_access_enabled = (
            str(getattr(service, "public_network_access", "enabled")).lower() != "disabled"
        )
        deployment_mode = (
            DeploymentMode.DEDICATED
            if getattr(service, "replica_count", None) is not None
            and getattr(service, "partition_count", None) is not None
            else DeploymentMode.SERVERLESS
        )
        sku = self._map_search_sku(service.sku.name if getattr(service, "sku", None) else None)
        high_density = (
            str(getattr(service, "hosting_mode", "")).lower() == "highdensity" or sku == SearchSku.S3_HD
        )

        features_enabled: list[SearchFeature] = []
        if semantic_enabled:
            features_enabled.append(SearchFeature.SEMANTIC_RANKER)
        if vector_enabled:
            features_enabled.append(SearchFeature.VECTOR_SEARCH)
        if ai_enrichment_enabled:
            features_enabled.append(SearchFeature.AI_ENRICHMENT)
        if knowledge_store_enabled:
            features_enabled.append(SearchFeature.KNOWLEDGE_STORE)
        if indexers:
            features_enabled.append(SearchFeature.INDEXERS)
        if managed_identity_enabled:
            features_enabled.append(SearchFeature.MANAGED_IDENTITY)
        if private_endpoint_enabled:
            features_enabled.append(SearchFeature.PRIVATE_ENDPOINTS)
        if availability_zones_enabled:
            features_enabled.append(SearchFeature.AVAILABILITY_ZONES)

        return AzureSearchServiceConfiguration(
            service_name=str(service.name),
            subscription_id=subscription_id,
            resource_group=resource_group,
            location=str(service.location),
            deployment_mode=deployment_mode,
            sku=sku,
            replicas=getattr(service, "replica_count", None),
            partitions=getattr(service, "partition_count", None),
            high_density=high_density,
            availability_zones_enabled=availability_zones_enabled,
            private_endpoint_enabled=private_endpoint_enabled,
            public_network_access_enabled=public_network_access_enabled,
            managed_identity_enabled=managed_identity_enabled,
            index_count=len(indexes),
            indexer_count=len(indexers),
            data_source_count=len(data_sources),
            skillset_count=len(skillsets),
            features_enabled=features_enabled,
            semantic_ranker=SemanticRankerConfiguration(
                enabled=semantic_enabled,
                default_configuration_name=semantic_default_name,
                query_cap_per_month=None,
                prioritized_fields_configured=semantic_prioritized_fields,
            ),
            vector_search=VectorSearchConfiguration(
                enabled=vector_enabled,
                algorithm=vector_algorithm,
                profile_count=vector_profile_count if vector_enabled else 0,
                vectorizer=vectorizer if vector_enabled else VectorizerType.NONE,
                integrated_vectorization_enabled=vectorizer != VectorizerType.NONE,
                vector_index_count=vector_index_count if vector_enabled else 0,
            ),
            ai_enrichment=AIEnrichmentConfiguration(
                enabled=ai_enrichment_enabled,
                skillset_count=max(len(skillsets), 1) if ai_enrichment_enabled else 0,
                knowledge_store_enabled=knowledge_store_enabled,
                cognitive_services_attached=cognitive_services_attached,
                image_extraction_enabled=image_extraction_enabled,
                custom_skill_count=custom_skill_count if ai_enrichment_enabled else 0,
            ),
        )

    def _list_search_collection(
        self,
        endpoint: str | None,
        collection_name: str,
        notes: list[str],
    ) -> list[Mapping[str, Any]]:
        payload = self._get_search_document(
            endpoint,
            collection_name,
            notes,
            note_context=f"{collection_name} collection",
        )
        if isinstance(payload, Mapping) and isinstance(payload.get("value"), list):
            return [item for item in payload["value"] if isinstance(item, Mapping)]
        return []

    def _get_search_document(
        self,
        endpoint: str | None,
        path: str,
        notes: list[str],
        *,
        note_context: str | None = None,
    ) -> Mapping[str, Any] | None:
        if not endpoint:
            return None

        url = f"{endpoint.rstrip('/')}/{path}?api-version={self._data_api_version}"
        try:
            token = self._credential.get_token(SEARCH_DATA_SCOPE).token
            request = Request(
                url,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                method="GET",
            )
            with urlopen(request, timeout=10) as response:  # noqa: S310 - Azure service endpoint
                payload = response.read().decode("utf-8")
        except (CredentialUnavailableError, ClientAuthenticationError) as exc:
            notes.append(
                "Azure Search data-plane RBAC access was unavailable while fetching "
                f"{note_context or path}: {exc!s}"
            )
            return None
        except HTTPError as exc:
            notes.append(
                f"Azure Search data-plane request for {note_context or path} returned HTTP {exc.code}."
            )
            return None
        except (URLError, TimeoutError, json.JSONDecodeError):
            notes.append(f"Azure Search data-plane request for {note_context or path} did not return JSON.")
            return None

        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            notes.append(f"Azure Search data-plane request for {note_context or path} did not return JSON.")
            return None
        return decoded if isinstance(decoded, Mapping) else None

    def _detect_semantic_configuration(
        self,
        indexes: Iterable[Mapping[str, Any]],
        service: SearchService,
    ) -> tuple[bool, str | None, bool]:
        default_configuration_name: str | None = None
        prioritized_fields_configured = False

        for index in indexes:
            semantic = index.get("semantic")
            if not isinstance(semantic, Mapping):
                continue
            configurations = semantic.get("configurations")
            if isinstance(configurations, list) and configurations:
                configuration = configurations[0]
                if isinstance(configuration, Mapping):
                    default_configuration_name = self._optional_str(configuration.get("name"))
                    prioritized_fields_configured = self._has_key(
                        configuration,
                        "prioritizedFields",
                    )
                    return True, default_configuration_name, prioritized_fields_configured

        service_semantic = getattr(service, "semantic_search", None)
        service_semantic_enabled = bool(service_semantic) and str(service_semantic).lower() != "disabled"
        return service_semantic_enabled, default_configuration_name, prioritized_fields_configured

    def _detect_vector_configuration(
        self,
        indexes: Iterable[Mapping[str, Any]],
    ) -> tuple[bool, VectorSearchAlgorithm | None, int, VectorizerType, int]:
        vector_index_count = 0
        vector_profile_count = 0
        algorithm: VectorSearchAlgorithm | None = None
        vectorizer = VectorizerType.NONE

        for index in indexes:
            fields = index.get("fields")
            if isinstance(fields, list) and any(
                isinstance(field, Mapping)
                and (
                    field.get("vectorSearchDimensions") is not None
                    or field.get("dimensions") is not None
                    or field.get("vectorSearchProfile") is not None
                )
                for field in fields
            ):
                vector_index_count += 1

            vector_search = index.get("vectorSearch")
            if not isinstance(vector_search, Mapping):
                continue

            profiles = vector_search.get("profiles")
            if isinstance(profiles, list):
                vector_profile_count += len(profiles)

            algorithms = vector_search.get("algorithms")
            if algorithm is None and isinstance(algorithms, list):
                for candidate in algorithms:
                    kind = str(candidate.get("kind", "")).lower() if isinstance(candidate, Mapping) else ""
                    if kind == "hnsw":
                        algorithm = VectorSearchAlgorithm.HNSW
                        break
                    if kind in {"exhaustiveknn", "exhaustive_knn"}:
                        algorithm = VectorSearchAlgorithm.EXHAUSTIVE_KNN
                        break

            vectorizers = vector_search.get("vectorizers")
            if vectorizer == VectorizerType.NONE and isinstance(vectorizers, list):
                for candidate in vectorizers:
                    if not isinstance(candidate, Mapping):
                        continue
                    kind = str(candidate.get("kind", "")).lower()
                    if kind == "azureopenai":
                        vectorizer = VectorizerType.AZURE_OPENAI
                        break
                    if kind == "customwebapi":
                        vectorizer = VectorizerType.CUSTOM_WEB_API
                        break

        enabled = vector_index_count > 0 or vector_profile_count > 0 or algorithm is not None
        if enabled and algorithm is None:
            algorithm = VectorSearchAlgorithm.HNSW
        return enabled, algorithm, vector_profile_count, vectorizer, vector_index_count

    @staticmethod
    def _extract_index_names(indexes: Iterable[Mapping[str, Any]]) -> list[str]:
        return [str(index["name"]) for index in indexes if index.get("name")]

    @staticmethod
    def _iter_skillset_skills(skillset: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
        skills = skillset.get("skills")
        if isinstance(skills, list):
            for item in skills:
                if isinstance(item, Mapping):
                    yield item

    @staticmethod
    def _has_key(payload: Mapping[str, Any] | None, key_name: str) -> bool:
        if payload is None:
            return False
        if key_name in payload and payload[key_name] is not None:
            return True
        return any(
            AzureSearchManagementClientAdapter._has_key(value, key_name)
            for value in payload.values()
            if isinstance(value, Mapping)
        )

    @staticmethod
    def _contains_text(payload: Any, text: str) -> bool:
        if isinstance(payload, Mapping):
            return any(
                AzureSearchManagementClientAdapter._contains_text(key, text)
                or AzureSearchManagementClientAdapter._contains_text(value, text)
                for key, value in payload.items()
            )
        if isinstance(payload, list):
            return any(AzureSearchManagementClientAdapter._contains_text(item, text) for item in payload)
        return text.lower() in str(payload).lower()

    @staticmethod
    def _to_mapping(value: Any) -> Mapping[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, Mapping):
            return value
        as_dict = getattr(value, "as_dict", None)
        if callable(as_dict):
            result = as_dict()
            return result if isinstance(result, Mapping) else None
        return None

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _map_search_sku(self, sku_name: str | None) -> SearchSku:
        normalized = (sku_name or "").strip().lower()
        if normalized not in SKU_NAME_TO_MODEL:
            raise AzureSearchManagementError(f"Unsupported or missing Azure AI Search SKU '{sku_name}'.")
        return SKU_NAME_TO_MODEL[normalized]
