# History API

The history API exposes stored run summaries and trend data for a search service.

## Routes covered

### `GET /history/{service_name}`

Return historical run summaries for a single Azure AI Search service.

### `GET /history/{service_name}/trends`

Return time-series data for finding counts and cost comparisons.

## Auth requirements

- No bearer token is required when `AUTH_ENABLED=false`.
- When `AUTH_ENABLED=true`, send a Microsoft Entra bearer token.

## Query parameters

### `GET /history/{service_name}`

| Parameter | Type | Default | Notes |
| --- | --- | --- | --- |
| `days` | integer | `30` | Minimum `1`, maximum `3650` |
| `limit` | integer | `50` | Minimum `1`, maximum `500` |

### `GET /history/{service_name}/trends`

| Parameter | Type | Default | Notes |
| --- | --- | --- | --- |
| `days` | integer | `90` | Minimum `1`, maximum `3650` |
| `limit` | integer | `50` | Minimum `1`, maximum `500` |

## Storage model

History is backed by SQLite through `HistoryDatabase`, which defaults to:

```text
data/history.db
```

The service stores:

- run metadata
- finding summaries
- cost snapshots
- recommendation summaries

## List stored runs

### Curl example

```bash
curl "http://127.0.0.1:8000/history/contoso-search-prod?days=30&limit=10"
```

### Response example

```json
{
  "service_name": "contoso-search-prod",
  "days": 30,
  "limit": 50,
  "runs": [
    {
      "id": "8bc69b0c-57bd-45e5-bc26-3b3f97aaf372",
      "service_name": "contoso-search-prod",
      "subscription_id": "api-submitted",
      "resource_group": "contoso-search-prod-rg",
      "run_at": "2026-06-13T06:31:47.243533Z",
      "finding_count": 1,
      "highest_severity": "medium",
      "configuration_hash": "aaeb35b2b0204cdf2eeaf6ac96cf1daeadca413197f98f467b88e2615fa2a13f",
      "dedicated_monthly_usd": 2705.04,
      "serverless_monthly_usd": 1979.04,
      "lower_cost_option": "serverless",
      "recommendation_count": 3
    }
  ]
}
```

## Get trend data

### Curl example

```bash
curl "http://127.0.0.1:8000/history/contoso-search-prod/trends?days=90&limit=20"
```

### Response example

```json
{
  "service_name": "contoso-search-prod",
  "days": 90,
  "limit": 50,
  "finding_count_over_time": [
    {
      "run_at": "2026-06-13T06:31:47.243533Z",
      "finding_count": 1
    }
  ],
  "cost_over_time": [
    {
      "run_at": "2026-06-13T06:31:47.243533Z",
      "dedicated_monthly_usd": 2705.04,
      "serverless_monthly_usd": 1979.04,
      "lower_cost_option": "serverless"
    }
  ]
}
```

## Where history comes from

- `/analyze` records summary-only runs in the background.
- `/recommend` records end-to-end runs when raw configuration and metrics are supplied.
- Consumers can point storage elsewhere with the `HISTORY_DB_PATH` environment variable.

## Common behaviors

- If no rows exist for a service, the API returns an empty `runs` or trend array.
- History endpoints reuse the same rate-limiting dependency as the core POST routes.

