from __future__ import annotations

from azure_ai_search_advisor.analysis.feature_analyzer import FeatureAnalysisInput, FeatureAnalyzer
from azure_ai_search_advisor.models import SearchFeature, VectorSearchAlgorithm, VectorizerType


def test_low_feature_adoption_is_detected(sample_snapshot) -> None:
    configuration = sample_snapshot.configuration.model_copy(
        update={
            "skillset_count": 1,
            "features_enabled": [
                *sample_snapshot.configuration.features_enabled,
                SearchFeature.SEMANTIC_RANKER,
                SearchFeature.VECTOR_SEARCH,
                SearchFeature.AI_ENRICHMENT,
            ],
            "semantic_ranker": sample_snapshot.configuration.semantic_ranker.model_copy(
                update={
                    "enabled": True,
                    "default_configuration_name": "default",
                    "query_cap_per_month": sample_snapshot.metrics.query_volume.monthly_queries,
                    "prioritized_fields_configured": True,
                }
            ),
            "vector_search": sample_snapshot.configuration.vector_search.model_copy(
                update={
                    "enabled": True,
                    "algorithm": VectorSearchAlgorithm.HNSW,
                    "profile_count": 1,
                    "vectorizer": VectorizerType.NONE,
                    "integrated_vectorization_enabled": False,
                    "vector_index_count": 1,
                }
            ),
            "ai_enrichment": sample_snapshot.configuration.ai_enrichment.model_copy(
                update={
                    "enabled": True,
                    "skillset_count": 1,
                    "knowledge_store_enabled": False,
                    "cognitive_services_attached": True,
                    "image_extraction_enabled": False,
                    "custom_skill_count": 0,
                }
            ),
        }
    )
    metrics = sample_snapshot.metrics.model_copy(
        update={
            "feature_usage": sample_snapshot.metrics.feature_usage.model_copy(
                update={
                    "semantic_query_percentage": 4.5,
                    "vector_query_percentage": 2.0,
                    "ai_enrichment_runs_per_day": 0,
                    "indexer_runs_per_day": 4.0,
                    "skill_invocations_per_day": 0,
                    "integrated_vectorization_calls_per_day": 3,
                }
            )
        }
    )

    result = FeatureAnalyzer().analyze(
        FeatureAnalysisInput(configuration=configuration, metrics=metrics)
    )

    assert {finding.title for finding in result.findings} == {
        "Semantic ranker is enabled but lightly adopted",
        "Vector search is enabled but rarely queried",
        "AI enrichment is enabled but inactive",
    }


def test_healthy_feature_adoption_avoids_findings(sample_snapshot) -> None:
    configuration = sample_snapshot.configuration.model_copy(
        update={
            "skillset_count": 1,
            "features_enabled": [
                *sample_snapshot.configuration.features_enabled,
                SearchFeature.SEMANTIC_RANKER,
                SearchFeature.VECTOR_SEARCH,
                SearchFeature.AI_ENRICHMENT,
            ],
            "semantic_ranker": sample_snapshot.configuration.semantic_ranker.model_copy(
                update={
                    "enabled": True,
                    "default_configuration_name": "default",
                    "query_cap_per_month": sample_snapshot.metrics.query_volume.monthly_queries,
                    "prioritized_fields_configured": True,
                }
            ),
            "vector_search": sample_snapshot.configuration.vector_search.model_copy(
                update={
                    "enabled": True,
                    "algorithm": VectorSearchAlgorithm.HNSW,
                    "profile_count": 1,
                    "vectorizer": VectorizerType.NONE,
                    "integrated_vectorization_enabled": False,
                    "vector_index_count": 1,
                }
            ),
            "ai_enrichment": sample_snapshot.configuration.ai_enrichment.model_copy(
                update={
                    "enabled": True,
                    "skillset_count": 1,
                    "knowledge_store_enabled": False,
                    "cognitive_services_attached": True,
                    "image_extraction_enabled": False,
                    "custom_skill_count": 0,
                }
            ),
        }
    )
    metrics = sample_snapshot.metrics.model_copy(
        update={
            "feature_usage": sample_snapshot.metrics.feature_usage.model_copy(
                update={
                    "semantic_query_percentage": 18.0,
                    "vector_query_percentage": 8.0,
                    "ai_enrichment_runs_per_day": 2,
                    "indexer_runs_per_day": 4.0,
                    "skill_invocations_per_day": 500,
                    "integrated_vectorization_calls_per_day": 120,
                }
            )
        }
    )

    result = FeatureAnalyzer().analyze(
        FeatureAnalysisInput(configuration=configuration, metrics=metrics)
    )

    assert result.findings == []
