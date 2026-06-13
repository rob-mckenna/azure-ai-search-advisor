# Automation & Scripting

Integrate the Azure AI Search Advisor into your workflows, pipelines, and scripts.

## API-first design

Every capability available in the chat UI is also available as a REST endpoint. This means you can:

- Run analyses in CI/CD pipelines
- Schedule periodic cost reviews
- Build custom dashboards
- Trigger alerts based on findings

## Authentication

### Local development (no auth)

```bash
# AUTH_ENABLED=false (default)
curl http://localhost:8000/analyze -H 'Content-Type: application/json' -d @payload.json
```

### Production (Entra ID bearer token)

```bash
# Get a token for your app registration
TOKEN=$(az account get-access-token \
  --resource api://YOUR_CLIENT_ID \
  --query accessToken -o tsv)

curl http://localhost:8000/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d @payload.json
```

## Common automation patterns

### Pattern 1: Nightly cost review

Run analysis across all services every night and flag new findings:

```bash
#!/bin/bash
# nightly-review.sh — Run via cron or GitHub Actions schedule

API_URL="${ADVISOR_API_URL:-http://localhost:8000}"

# Discover all services in the subscription
SERVICES=$(curl -s "$API_URL/discover/services?subscription_id=$AZURE_SUBSCRIPTION_ID")

# Analyze each service
echo "$SERVICES" | jq -c '.services[]' | while read -r service; do
  SERVICE_NAME=$(echo "$service" | jq -r '.service_name')
  echo "Analyzing: $SERVICE_NAME"

  RESULT=$(curl -s -X POST "$API_URL/analyze" \
    -H 'Content-Type: application/json' \
    -d "{\"configuration\": $service, \"include_cost_signals\": true}")

  # Check for high/critical findings
  CRITICAL=$(echo "$RESULT" | jq '[.findings[] | select(.severity == "critical" or .severity == "high")] | length')

  if [ "$CRITICAL" -gt 0 ]; then
    echo "⚠️  $SERVICE_NAME has $CRITICAL critical/high findings"
    # Send notification (Teams, Slack, email, etc.)
  fi
done
```

### Pattern 2: Pre-deployment validation

Check proposed changes before applying them:

```bash
#!/bin/bash
# validate-search-config.sh — Run in CI before Bicep/Terraform deploy

# Extract proposed config from IaC parameters
PROPOSED_SKU=$(jq -r '.parameters.searchSku.value' infra/parameters.json)
PROPOSED_REPLICAS=$(jq -r '.parameters.replicaCount.value' infra/parameters.json)

# Simulate the proposed configuration
SIMULATION=$(curl -s -X POST "$API_URL/simulate" \
  -H 'Content-Type: application/json' \
  -d "{
    \"current_configuration\": $(cat current-service-config.json),
    \"proposed_changes\": {
      \"sku\": \"$PROPOSED_SKU\",
      \"replica_count\": $PROPOSED_REPLICAS
    }
  }")

# Fail the pipeline if costs increase unexpectedly
COST_INCREASE=$(echo "$SIMULATION" | jq '.cost_delta_percent')
if (( $(echo "$COST_INCREASE > 50" | bc -l) )); then
  echo "❌ Proposed change increases costs by ${COST_INCREASE}% — review required"
  exit 1
fi
```

### Pattern 3: GitHub Actions integration

```yaml
# .github/workflows/search-review.yml
name: Weekly Search Service Review

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9am
  workflow_dispatch:

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
      issues: write

    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Start advisor
        run: |
          pip install -e .
          uvicorn azure_ai_search_advisor.main:app --host 0.0.0.0 --port 8000 &
          sleep 5

      - name: Discover and analyze
        run: |
          RESULTS=$(curl -s http://localhost:8000/discover/services?subscription_id=${{ secrets.AZURE_SUBSCRIPTION_ID }})
          echo "$RESULTS" | jq -c '.services[]' | while read -r svc; do
            curl -s -X POST http://localhost:8000/analyze \
              -H 'Content-Type: application/json' \
              -d "{\"configuration\": $svc, \"include_cost_signals\": true}" \
              >> results.json
          done

      - name: Create issue if findings exist
        if: success()
        run: |
          FINDINGS=$(cat results.json | jq '[.findings[] | select(.severity == "high" or .severity == "critical")] | length')
          if [ "$FINDINGS" -gt 0 ]; then
            gh issue create \
              --title "🔍 Search Advisor: $FINDINGS high-priority findings" \
              --body "$(cat results.json | jq -r '.findings[] | select(.severity == "high" or .severity == "critical") | "- **\(.title)** (\(.severity)): \(.description)"')" \
              --label "cost-optimization"
          fi
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Pattern 4: Python scripting

```python
"""analyze_all_services.py — Programmatic access to the advisor."""
import httpx
import json
from pathlib import Path

API_URL = "http://localhost:8000"

def analyze_service(config: dict) -> dict:
    """Submit a service configuration for analysis."""
    response = httpx.post(
        f"{API_URL}/analyze",
        json={
            "configuration": config,
            "include_cost_signals": True,
            "include_feature_assessment": True,
        },
    )
    response.raise_for_status()
    return response.json()

def get_recommendations(findings: list[dict]) -> dict:
    """Generate recommendations from analysis findings."""
    response = httpx.post(
        f"{API_URL}/recommend",
        json={"findings": findings},
    )
    response.raise_for_status()
    return response.json()

# Load scenarios
scenarios_dir = Path("docs/user-guide/scenarios")
for scenario_file in scenarios_dir.glob("*.json"):
    config = json.loads(scenario_file.read_text())
    print(f"\n{'='*60}")
    print(f"Analyzing: {config['configuration']['service_name']}")
    print(f"{'='*60}")

    result = analyze_service(config["configuration"])

    print(f"  Findings: {result['summary']['finding_count']}")
    print(f"  Highest severity: {result['summary']['highest_severity']}")

    if result["summary"]["finding_count"] > 0:
        recs = get_recommendations(result["findings"])
        for rec in recs.get("recommendations", []):
            savings = rec.get("estimated_monthly_savings_usd", 0)
            print(f"  💡 {rec['title']} (saves ~${savings}/mo)")
```

### Pattern 5: Track optimization over time

```bash
#!/bin/bash
# track-progress.sh — Record analysis results for trending

SERVICE_NAME="contoso-search-prod"
API_URL="http://localhost:8000"

# Run analysis (automatically recorded to history)
curl -s -X POST "$API_URL/analyze" \
  -H 'Content-Type: application/json' \
  -d @"configs/${SERVICE_NAME}.json"

# Check trends
echo "\n📊 Optimization trends for $SERVICE_NAME:"
curl -s "$API_URL/history/${SERVICE_NAME}/trends" | jq '.trends'
```

## Response codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Parse response normally |
| 400 | Invalid payload | Check JSON structure against examples |
| 401 | Unauthorized | Verify bearer token |
| 429 | Rate limited | Back off and retry (check `Retry-After` header) |
| 503 | Circuit breaker open | Azure API temporarily unavailable; retry after 30s |

## Tips for production automation

1. **Always check `status` field** — responses include `"status": "completed"` or `"status": "error"`
2. **Use correlation IDs** — pass `X-Correlation-ID` header for tracing across systems
3. **Handle rate limits gracefully** — the API returns `429` with `Retry-After` when limits are hit
4. **Cache repeated analyses** — the API caches identical payloads (when `CACHE_ENABLED=true`)
5. **Use `/health` for readiness checks** — returns `{"status": "healthy"}` when the service is ready

---

**← Back to:** [Starter Scenarios](scenarios.md) | [User Guide Home](index.md)
