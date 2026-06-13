# `POST /recommend`

Generate optimization guidance for an Azure AI Search workload.

## Method and path

- **Method:** `POST`
- **Path:** `/recommend`

## Auth requirements

- No bearer token is required when `AUTH_ENABLED=false`.
- When `AUTH_ENABLED=true`, send a Microsoft Entra bearer token.

## Query parameters

None.

## Supported request modes

### 1. Analysis-driven recommendations

Send an `analysis` object from a previous `/analyze` call.

### 2. End-to-end recommendations

Send raw `configuration` plus `metrics`; the API will run ingestion, analysis, cost modeling, and recommendation synthesis in one request.

## Request body

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `analysis` | object | Conditionally | Required when raw inputs are omitted |
| `configuration` | object | Conditionally | Must be paired with `metrics` |
| `metrics` | object | Conditionally | Must be paired with `configuration` |
| `preferences` | object | No | Ranking and output-detail preferences |

### Curl example

```bash
curl -X POST http://127.0.0.1:8000/recommend   -H 'Content-Type: application/json'   -d '{
    "configuration": {
      "service_name": "contoso-search-prod",
      "region": "eastus2",
      "capacity": {
        "pricing_model": "dedicated",
        "sku": "standard",
        "replica_count": 3,
        "partition_count": 2,
        "zone_redundancy_enabled": true
      },
      "features": {
        "semantic_ranker_enabled": true,
        "vector_search_enabled": true,
        "ai_enrichment_enabled": false,
        "knowledge_store_enabled": false
      },
      "index_topology": {
        "index_count": 6,
        "indexer_count": 3,
        "skillset_count": 0,
        "total_document_count": 1200000,
        "total_index_size_gb": 185.4,
        "vector_index_size_gb": 42.0
      },
      "security": {
        "api_keys_enabled": true,
        "managed_identity_enabled": true,
        "private_endpoint_enabled": true,
        "customer_managed_keys_enabled": false
      },
      "notes": []
    },
    "metrics": {
      "observation_window_days": 30,
      "query": {
        "average_queries_per_second": 18.2,
        "peak_queries_per_second": 74.0,
        "monthly_query_volume": 4300000,
        "p95_query_latency_ms": 185.0,
        "cache_hit_ratio": 0.32
      },
      "indexing": {
        "daily_document_updates": 250000,
        "full_rebuilds_per_month": 2,
        "average_indexing_latency_minutes": 24.5
      },
      "utilization": {
        "replica_utilization_percent": 41.0,
        "partition_utilization_percent": 58.0,
        "storage_utilization_percent": 61.0,
        "semantic_queries_per_day": 40000,
        "vector_queries_per_day": 12000
      }
    },
    "preferences": {
      "max_recommendations": 5,
      "prioritize_for": ["cost", "performance"],
      "include_remediation_steps": true
    }
  }'
```

## Response example

```json
{
  "request_id": "rec_9171e20284be409386fb3542b18a3c96",
  "status": "completed",
  "generated_at": "2026-06-13T06:27:09.748845Z",
  "source": "end_to_end",
  "recommendations": [
    {
      "recommendation_id": "rec_01_reduce-replicas-from-3-to-2",
      "priority": "high",
      "title": "Reduce replicas from 3 to 2",
      "summary": "Replica capacity is higher than current query concurrency and availability requirements demand.",
      "rationale": "Lower monthly capacity spend by about $726.",
      "projected_impact": {
        "monthly_cost_delta_usd": -726.0,
        "performance_impact": "Low implementation effort; validate latency and relevance after rollout.",
        "risk_reduction": "Addresses a cost or configuration inefficiency surfaced by the advisor."
      },
      "remediation_steps": [
        {
          "step_number": 1,
          "action": "Validate the minimum replica count needed for SLA and query concurrency.",
          "detail": "Validate the minimum replica count needed for SLA and query concurrency.",
          "owner_hint": "search-platform"
        }
      ],
      "prerequisites": [],
      "tradeoffs": ["Estimated effort: low."]
    }
  ],
  "summary": "Generated 2 recommendations, including 2 high-priority actions and 1 quick wins.",
  "notes": [
    "Estimated monthly savings: $726.00.",
    "Savings confidence: approximate",
    "Built from raw configuration and metrics."
  ]
}
```

## Response notes

- `source` is `analysis_input` when you submit a previous `/analyze` result.
- `source` is `end_to_end` when the API performs analysis and cost modeling internally.
- Recommendation ranking is influenced by `max_recommendations`, `prioritize_for`, and `include_remediation_steps`.

## Common error cases

| Status | When it happens |
| --- | --- |
| `422` | Neither `analysis` nor `configuration`+`metrics` is provided |
| `429` | Rate limiting is enabled and the client exceeds the configured window |
| `500` | Upstream analysis, cost modeling, or recommendation generation fails |
