# `POST /simulate`

Compare current and proposed Azure AI Search cost scenarios.

## Method and path

- **Method:** `POST`
- **Path:** `/simulate`

## Auth requirements

- No bearer token is required when `AUTH_ENABLED=false`.
- When `AUTH_ENABLED=true`, send a Microsoft Entra bearer token.

## Query parameters

None.

## Supported request modes

### Configuration-diff mode

Send:

- `current_configuration`
- optional `current_metrics`
- one or more `proposed_changes`

### Direct cost-model mode

Send `cost_model_request` when you want a pure dedicated-versus-serverless comparison without a configuration diff.

## Curl example

```bash
curl -X POST http://127.0.0.1:8000/simulate   -H 'Content-Type: application/json'   -d '{
    "current_configuration": {
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
    "proposed_changes": [
      {
        "change_id": "reduce-replicas",
        "target": "capacity",
        "attribute": "replica_count",
        "current_value": 3,
        "proposed_value": 2,
        "rationale": "Observed replica utilization is below 50% during sustained traffic."
      }
    ],
    "assumptions": {
      "pricing_horizon_days": 30,
      "currency": "USD",
      "notes": ["Illustrative comparison without reserved capacity discounts."]
    }
  }'
```

## Response example

```json
{
  "request_id": "sim_845337501b3c48f491a1fc47af2c2870",
  "status": "completed",
  "generated_at": "2026-06-13T06:27:09.754227Z",
  "comparison": {
    "current_estimate": {
      "currency": "USD",
      "monthly_total": 1505.04,
      "compute_monthly": 1500.0,
      "semantic_monthly": 0.0,
      "vector_monthly": 5.04,
      "enrichment_monthly": 0.0
    },
    "proposed_estimate": {
      "currency": "USD",
      "monthly_total": 1005.04,
      "compute_monthly": 1000.0,
      "semantic_monthly": 0.0,
      "vector_monthly": 5.04,
      "enrichment_monthly": 0.0
    },
    "monthly_delta": -500.0,
    "monthly_savings_percent": 33.22
  },
  "projected_impact": {
    "capacity_risk": "Lower capacity can increase latency or indexing backlog during bursts; validate before rollout.",
    "latency_expectation": "Expect unchanged baseline latency if headroom remains, but peak latency could rise under load spikes.",
    "operational_notes": [
      "Observed replica utilization is below 50% during sustained traffic."
    ]
  },
  "notes": [
    "Illustrative comparison without reserved capacity discounts.",
    "Processed 1 proposed change(s)."
  ]
}
```

## Direct cost-model example

```bash
curl -X POST http://127.0.0.1:8000/simulate   -H 'Content-Type: application/json'   -d '{
    "cost_model_request": {
      "dedicated_search": {
        "tier": "s1",
        "replicas": 3,
        "partitions": 2,
        "months": 1.0
      },
      "serverless_search": {
        "monthly_queries": 4300000,
        "average_billable_compute_units_per_query": 1.25,
        "months": 1.0
      },
      "feature_costs": {
        "semantic_queries_per_month": 1200000,
        "enrichment_transactions_per_month": 0,
        "vector_index_storage_gb": 42.0,
        "months": 1.0
      }
    },
    "assumptions": {
      "currency": "USD"
    }
  }'
```

## Common error cases

| Status | When it happens |
| --- | --- |
| `422` | No `cost_model_request` and no `current_configuration`, or no `proposed_changes` in diff mode |
| `429` | Rate limiting is enabled and the client exceeds the configured window |
| `500` | Cost modeling fails unexpectedly |
