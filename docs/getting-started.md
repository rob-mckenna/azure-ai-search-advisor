# Getting Started

This guide gets the API running locally and walks through the first useful request.

## Prerequisites

### Required

- Python 3.11+
- `pip`

### Optional but recommended

- Docker and Docker Compose for local container runs
- Node.js 18+ if you also want to run the UI in `ui/`
- Azure CLI (`az`) if you plan to use live discovery or Azure deployment flows
- Azure Developer CLI (`azd`) for full-stack Azure provisioning

## Clone and install

```bash
git clone https://github.com/rob-mckenna/azure-ai-search-advisor.git
cd azure-ai-search-advisor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

> On Debian or Ubuntu, install `python3-venv` first if `python3 -m venv` is unavailable.

## Configure environment variables

Create a local environment file from the example:

```bash
cp .env.example .env
```

Key settings from `.env.example`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AZURE_AI_FOUNDRY_ENDPOINT` | placeholder URL | Microsoft Foundry project endpoint |
| `AZURE_AI_FOUNDRY_MODEL` | `gpt-4o` | Foundry model deployment name |
| `ORCHESTRATION_MODE` | `local` | `local` service chaining or `framework` agent orchestration |
| `AUTH_ENABLED` | `false` | Disable or enforce Microsoft Entra bearer auth |
| `AZURE_SUBSCRIPTION_ID` | unset | Optional default subscription for live discovery |
| `CORS_ALLOWED_ORIGINS` | localhost dev origins | Browser clients allowed to call the API |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `LOG_FORMAT` | `text` | `text` locally or `json` for structured production logs |
| `RATE_LIMIT_ENABLED` | `false` | Toggle in-memory rate limiting |
| `RATE_LIMIT_REQUESTS` | `60` | Request count in the window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Sliding window duration |

### Authentication behavior

- With `AUTH_ENABLED=false`, protected endpoints use a mock local user and you can call the API directly.
- With `AUTH_ENABLED=true`, set `AZURE_TENANT_ID` and `AZURE_CLIENT_ID`, then send a bearer token whose audience matches `AZURE_CLIENT_ID`.

## Run the API locally

```bash
python -m uvicorn azure_ai_search_advisor.main:app --reload
```

Available URLs:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## First API call

Start with a quick health check:

```bash
curl http://127.0.0.1:8000/health
```

Then submit a real analysis request:

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

Example response shape:

```json
{
  "request_id": "anl_...",
  "status": "completed",
  "summary": {
    "finding_count": 1,
    "highest_severity": "medium",
    "optimization_themes": ["capacity"],
    "overall_assessment": "Detected 1 optimization opportunity(ies) across the submitted workload."
  },
  "findings": [
    {
      "finding_id": "provisioning-1",
      "title": "Review dedicated replica count",
      "severity": "medium"
    }
  ]
}
```

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

The checked-in `docker-compose.yml` currently runs the API service on port `8000`.

## Next steps

- Read the [Architecture](architecture.md) guide.
- Explore endpoint details in the [API Reference](api/index.md).
- If you want the frontend, continue to [UI Development](ui/index.md).
