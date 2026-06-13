# API Reference Overview

## Base URL

Local development uses `http://127.0.0.1:8000` by default.

## Available endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/analyze` | Analyze a submitted Azure AI Search configuration and metrics snapshot |
| `POST` | `/recommend` | Generate prioritized optimization guidance |
| `POST` | `/simulate` | Compare current and proposed cost scenarios |
| `GET` | `/discover` | Enumerate live Azure AI Search services visible to your credentials |
| `POST` | `/discover/{service_name}/analyze` | Discover and analyze a live Azure AI Search service |
| `GET` | `/history/{service_name}` | List stored runs for a service |
| `GET` | `/history/{service_name}/trends` | Return finding-count and cost trends |
| `GET` | `/health` | Readiness and diagnostics probe |

## Authentication

All functional endpoints depend on `get_current_user()`.

- **Default local behavior:** `AUTH_ENABLED=false` means no bearer token is required.
- **Protected behavior:** when `AUTH_ENABLED=true`, send `Authorization: Bearer <token>` and configure `AZURE_TENANT_ID` plus `AZURE_CLIENT_ID`.
- **Live discovery:** even when API auth is disabled, `/discover` still needs Azure credentials resolvable by `DefaultAzureCredential`.

## Common headers

```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer <token>   # only when auth is enabled
```

## Error format

Validation and HTTP errors use a shared envelope:

```json
{
  "error_code": "validation_error",
  "message": "The request payload failed schema validation.",
  "status_code": 422,
  "details": [
    {
      "path": ["body", "configuration", "capacity", "replica_count"],
      "message": "Input should be greater than or equal to 0",
      "error_type": "greater_than_equal"
    }
  ],
  "correlation_id": "f6b0c720-b97a-4e8e-9ed9-ded4952df2ae"
}
```

## Operational behavior

### Correlation IDs

Each request is wrapped by correlation-ID middleware so API logs can be matched to client activity.

### Rate limiting

`/analyze`, `/recommend`, `/simulate`, and `/history` include rate-limit checks. The limiter is disabled by default and becomes active only when:

- `RATE_LIMIT_ENABLED=true`
- `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` are set to positive values

### Caching

`/analyze` can emit these response headers when caching is enabled:

- `X-Cache-Key`
- `X-Cache: HIT|MISS`

### Interactive docs

When the service is running, use:

- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Endpoint detail pages

- [Analyze](analyze.md)
- [Recommend](recommend.md)
- [Simulate](simulate.md)
- [Discover](discover.md)
- [History](history.md)

