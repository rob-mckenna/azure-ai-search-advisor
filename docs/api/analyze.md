# `POST /analyze`

Analyze an Azure AI Search workload from a submitted configuration and metrics snapshot.

## Method and path

- **Method:** `POST`
- **Path:** `/analyze`

## Auth requirements

- No bearer token is required when `AUTH_ENABLED=false`.
- When `AUTH_ENABLED=true`, send a Microsoft Entra bearer token.

## Query parameters

None.

## Request body

Top-level fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `configuration` | object | Yes | Current search service configuration |
| `metrics` | object | Yes | Observed workload and utilization metrics |
| `include_cost_signals` | boolean | No | Defaults to `true` |
| `include_feature_assessment` | boolean | No | Defaults to `true` |

### Curl example

```bash
curl -X POST http://127.0.0.1:8000/analyze   -H 'Content-Type: application/json'   -d '{
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
      "notes": ["Replica utilization is believed to be low overnight."]
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
    "include_cost_signals": true,
    "include_feature_assessment": true
  }'
```

## Response example

The example below is from the current implementation path in this repository. `request_id` and `generated_at` are generated per request.

```json
{
  "request_id": "anl_81dfca2f9bd64bb6a49e12b3864ef2fa",
  "status": "completed",
  "generated_at": "2026-06-13T06:27:09.740251Z",
  "summary": {
    "finding_count": 1,
    "highest_severity": "medium",
    "optimization_themes": ["capacity"],
    "overall_assessment": "Detected 1 optimization opportunity(ies) across the submitted workload."
  },
  "findings": [
    {
      "finding_id": "provisioning-1",
      "category": "capacity",
      "severity": "medium",
      "title": "Review dedicated replica count",
      "description": "Replica capacity appears oversized for the observed query demand and CPU load.",
      "evidence": [
        {
          "metric": "avg_cpu_utilization_pct",
          "observed_value": 41.0,
          "expected_range": "35-70% for steady dedicated production workloads",
          "explanation": "Unused replicas increase ongoing dedicated capacity spend."
        }
      ],
      "impacted_resources": ["capacity", "monthly_cost"],
      "potential_monthly_cost_impact_usd": 500.0,
      "recommendation_hint": "Reduce replicas by one and validate p95 latency before rollout."
    }
  ],
  "notes": [
    "Results combine the current analysis service plus lightweight API-to-domain normalization."
  ]
}
```

## Response headers

`/analyze` also sets:

- `X-Cache-Key`: SHA-256 hash of the normalized request payload
- `X-Cache`: `HIT` or `MISS` when caching is enabled with `CACHE_ENABLED=true`

## Persistence behavior

The route records summarized runs through `HistoryService` in the background. That stored data later appears in `/history/{service_name}`.

## Common error cases

| Status | When it happens |
| --- | --- |
| `422` | Payload fails schema validation or ingestion normalization |
| `429` | Rate limiting is enabled and the client exceeds the configured window |
| `500` | Unexpected failure inside ingestion or analysis services |

