# Discovery API

The discovery API works against live Azure resources instead of a manually submitted payload.

## Routes covered

### `GET /discover`

List Azure AI Search services visible to the active Azure credential.

### `POST /discover/{service_name}/analyze`

Resolve one discovered service, ingest its live configuration, and return the same analysis shape used by `POST /analyze`.

## Auth requirements

There are two separate auth concerns:

1. **API auth**  
   Controlled by `AUTH_ENABLED`, exactly like the rest of the API.
2. **Azure resource access**  
   `LiveIngestionService` uses `DefaultAzureCredential`. You must be signed in with `az login`, managed identity, workload identity, or equivalent credentials that can query Azure Resource Graph and the Search management plane.

If Azure credentials are unavailable, the API returns `503 Service Unavailable`.

## Query parameters

Both routes support these optional query parameters:

| Parameter | Type | Purpose |
| --- | --- | --- |
| `subscription_id` | string | Restrict discovery to one subscription; otherwise the API uses `AZURE_SUBSCRIPTION_ID` when set |
| `resource_group` | string | Restrict discovery or analysis to one resource group |

## List discovered services

### Curl example

```bash
curl "http://127.0.0.1:8000/discover?subscription_id=<subscription-id>&resource_group=<resource-group>"
```

### Response example

```json
{
  "services": [
    {
      "name": "contoso-search-prod",
      "resource_group": "rg-contoso-search",
      "subscription_id": "00000000-0000-0000-0000-000000000000",
      "location": "eastus2",
      "sku": "standard",
      "replica_count": 3,
      "partition_count": 2
    }
  ],
  "notes": []
}
```

## Analyze a discovered service

### Curl example

```bash
curl -X POST   "http://127.0.0.1:8000/discover/contoso-search-prod/analyze?subscription_id=<subscription-id>&resource_group=<resource-group>"
```

### Response example

The response model is the same as [`POST /analyze`](analyze.md). The API may also append live-ingestion notes to the `notes` array.

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
  ],
  "notes": [
    "Results combine the current analysis service plus lightweight API-to-domain normalization."
  ]
}
```

## Failure modes

| Status | When it happens |
| --- | --- |
| `404` | The named Azure AI Search service cannot be resolved |
| `409` | Multiple services match the same name and you did not disambiguate with subscription + resource group |
| `502` | Azure Resource Graph or management-plane ingestion fails upstream |
| `503` | Azure credentials are unavailable for discovery |
