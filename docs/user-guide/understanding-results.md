# Understanding Results

This page explains how to read and act on the advisor's output.

## Analysis response structure

Every analysis response contains:

```json
{
  "request_id": "anl_abc123",
  "status": "completed",
  "summary": { ... },
  "findings": [ ... ],
  "cost_signals": { ... },
  "feature_assessment": { ... }
}
```

### Summary

The summary gives you the big picture at a glance:

| Field | Meaning |
|-------|---------|
| `finding_count` | Total optimization opportunities detected |
| `highest_severity` | Most critical finding level (critical > high > medium > low > info) |
| `optimization_themes` | Categories of findings (capacity, features, sku, cost) |
| `overall_assessment` | Human-readable one-line summary |

### Findings

Each finding is a specific optimization opportunity:

```json
{
  "finding_id": "provisioning-1",
  "title": "Review dedicated replica count",
  "severity": "medium",
  "category": "capacity",
  "description": "Current QPS of 18.2 with 3 replicas gives ~6 QPS/replica. Consider reducing to 2 replicas.",
  "evidence": {
    "current_replicas": 3,
    "qps_per_replica": 6.07,
    "threshold": 5.0
  },
  "recommendation": "Reduce replica count from 3 to 2 during off-peak hours"
}
```

## Severity levels

![Severity Scale](img/severity-scale.png)

*Findings are color-coded by severity in the UI.*

| Level | Icon | Meaning | Action |
|-------|------|---------|--------|
| **Critical** | 🔴 | Service at risk or major waste | Act immediately |
| **High** | 🟠 | Significant savings or performance issue | Plan for this sprint |
| **Medium** | 🟡 | Notable optimization opportunity | Schedule within 30 days |
| **Low** | 🟢 | Minor improvement possible | Consider during next review |
| **Info** | ℹ️ | Observation, no action needed | Awareness only |

## Analysis categories

### Provisioning analysis

Detects over- or under-provisioned resources:

| Finding | What it means |
|---------|---------------|
| "Replica count may be excessive" | QPS per replica is below threshold — you're paying for unused capacity |
| "Partition count exceeds data needs" | Your index fits in fewer partitions than allocated |
| "Service appears idle" | Very low QPS suggests the service isn't actively used |
| "Consider adding replicas" | High QPS per replica indicates potential latency risk |

### Feature analysis

Identifies enabled features that aren't being used:

| Finding | What it means |
|---------|---------------|
| "Semantic ranker enabled but unused" | Feature is on but no semantic queries detected |
| "Vector search enabled, low utilization" | Vector indexes exist but queries are rare |
| "AI enrichment enabled, no skillsets" | Enrichment pipeline configured but not used |

### SKU analysis

Evaluates whether your current SKU matches workload needs:

| Finding | What it means |
|---------|---------------|
| "Service may fit in a lower SKU" | Data volume and QPS fit a cheaper tier |
| "SKU storage limit approaching" | You're nearing capacity — plan to scale |
| "Consider S2/S3 for dataset size" | Data exceeds current SKU partition limits |

## Recommendations

Recommendations are generated from findings and include actionable steps:

```json
{
  "recommendation_id": "rec_001",
  "title": "Reduce replica count to 2",
  "priority": "medium",
  "estimated_monthly_savings_usd": 450.00,
  "effort": "low",
  "risk": "low",
  "steps": [
    "Verify peak QPS stays under 50 with 2 replicas",
    "Use az search service update --replica-count 2",
    "Monitor p95 latency for 48 hours after change"
  ],
  "rollback": "az search service update --replica-count 3"
}
```

### Priority matrix

| Priority | Savings potential | Typical effort |
|----------|-----------------|----------------|
| **Critical** | >$1,000/month | Varies |
| **High** | $500–$1,000/month | Low–Medium |
| **Medium** | $100–$500/month | Low |
| **Low** | <$100/month | Minimal |

## Cost signals

When `include_cost_signals: true`, you get pricing context:

```json
{
  "current_monthly_estimate_usd": 2847.00,
  "breakdown": {
    "base_sku": 1200.00,
    "replicas": 1200.00,
    "partitions": 447.00
  }
}
```

## Alerting recommendations

Alert suggestions include ready-to-use Azure CLI commands:

```json
{
  "alert_name": "High Query Latency",
  "metric": "SearchLatency",
  "condition": "Average > 500ms over 5 minutes",
  "severity": 2,
  "remediation_cli": "az monitor metrics alert create --name 'search-latency-high' ..."
}
```

## Reading results in the UI vs. API

| Aspect | Chat UI | API |
|--------|---------|-----|
| Format | Natural language summary with highlights | Full JSON with all fields |
| Interaction | Ask follow-up questions | Parse and process programmatically |
| Best for | Exploration, understanding | Automation, CI/CD, dashboards |

## What to do next

1. **Start with the highest severity findings** — these have the biggest impact
2. **Use simulations** before making changes — model the cost impact first
3. **Set up alerts** for the metrics that matter most to your workload
4. **Re-analyze monthly** — workloads change, and so should your configuration

---

**Next:** [Starter Scenarios →](scenarios.md)
