from __future__ import annotations

from azure_ai_search_advisor.recommendations.feature_guidance import (
    generate_feature_guidance_recommendations,
)
from azure_ai_search_advisor.recommendations.pricing_advisor import (
    generate_pricing_model_recommendations,
)
from azure_ai_search_advisor.recommendations.rightsizing import (
    generate_rightsizing_recommendations,
)



def test_generate_rightsizing_recommendations_for_replica_overprovisioning() -> None:
    recommendations = generate_rightsizing_recommendations(
        {
            "topology": {
                "replica_overprovisioned": True,
                "suggested_replicas": 2,
                "estimated_monthly_savings": 500,
            },
            "service": {"replicas": 3},
        },
        {},
    )

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.title == "Reduce replicas from 3 to 2"
    assert recommendation.priority == "high"
    assert recommendation.impact_estimate == "Lower monthly capacity spend by about $500."



def test_generate_rightsizing_recommendations_for_partition_overprovisioning() -> None:
    recommendations = generate_rightsizing_recommendations(
        {
            "topology": {
                "partition_overprovisioned": True,
                "suggested_partitions": 2,
                "estimated_partition_savings": 300,
            },
            "service": {"partitions": 3},
        },
        {},
    )

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.title == "Reduce partitions from 3 to 2"
    assert recommendation.effort == "medium"
    assert recommendation.impact_estimate == "Reduce monthly search unit cost by about $300."



def test_generate_rightsizing_recommendations_for_sku_downgrade() -> None:
    recommendations = generate_rightsizing_recommendations(
        {
            "topology": {
                "sku_downgrade_candidate": True,
                "suggested_sku": "s1",
                "estimated_sku_savings": 750,
            },
            "service": {"sku": "s2"},
        },
        {},
    )

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.title == "Downgrade SKU from s2 to s1"
    assert recommendation.priority == "medium"
    assert recommendation.impact_estimate == "Capture an estimated $750 in monthly savings."



def test_generate_feature_guidance_recommendations_for_low_semantic_usage() -> None:
    recommendations = generate_feature_guidance_recommendations(
        {
            "features": {
                "semantic_ranker_enabled": True,
                "semantic_query_ratio": 0.05,
                "estimated_semantic_monthly_cost": 120,
            }
        },
        {},
    )

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.title == "Disable semantic ranker on underused workloads"
    assert recommendation.effort == "low"
    assert recommendation.impact_estimate == "Avoid roughly $120 in monthly feature spend."



def test_generate_feature_guidance_recommendations_for_semantic_quality_gap() -> None:
    recommendations = generate_feature_guidance_recommendations(
        {
            "features": {
                "semantic_ranker_enabled": False,
                "semantic_quality_gap": True,
            }
        },
        {},
    )

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.title == "Enable semantic ranker for relevance-sensitive queries"
    assert recommendation.priority == "medium"
    assert recommendation.impact_estimate == (
        "Improve top-result relevance and reduce zero-click search sessions."
    )



def test_generate_pricing_model_recommendations_for_serverless_candidate() -> None:
    recommendations = generate_pricing_model_recommendations(
        {
            "pricing": {"switch_to_serverless_candidate": True},
            "service": {"hosting_mode": "dedicated"},
        },
        {"scenario_comparison": {"serverless_monthly_savings": 220}},
    )

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.title == "Move bursty development workloads to serverless"
    assert recommendation.category == "pricing_model"
    assert recommendation.impact_estimate == (
        "Cut monthly spend by about $220 if burst patterns hold."
    )



def test_generate_pricing_model_recommendations_for_dedicated_candidate() -> None:
    recommendations = generate_pricing_model_recommendations(
        {
            "pricing": {"switch_to_dedicated_candidate": True},
            "service": {"hosting_mode": "serverless"},
        },
        {"scenario_comparison": {"dedicated_monthly_savings": 1800}},
    )

    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation.title == "Move sustained production traffic to dedicated pricing"
    assert recommendation.priority == "high"
    assert recommendation.impact_estimate == "Reduce monthly operating cost by roughly $1,800."



def test_empty_findings_produce_no_recommendations() -> None:
    assert generate_rightsizing_recommendations({}, {}) == []
    assert generate_feature_guidance_recommendations({}, {}) == []
    assert generate_pricing_model_recommendations({}, {}) == []
