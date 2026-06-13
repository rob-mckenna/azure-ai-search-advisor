# Starter Scenarios

These are ready-to-use configurations representing common Azure AI Search workloads. Copy a scenario, modify it to match your service, and submit it to the advisor.

Each scenario includes:

- **When to use** — the workload pattern it represents
- **Key characteristics** — what makes this configuration notable
- **Expected findings** — what the advisor typically detects
- **Customization tips** — how to adapt it to your real service

---

## Scenario 1: E-commerce Product Catalog

**When to use:** Online retail with product search, faceted navigation, and autocomplete.

**Key characteristics:**
- High query volume, moderate document count
- Semantic ranker for natural-language product search
- Multiple replicas for availability during peak shopping

??? example "Full JSON payload (click to expand)"

    ```json
    {
      "configuration": {
        "service_name": "contoso-shop-search",
        "region": "eastus",
        "capacity": {
          "pricing_model": "dedicated",
          "sku": "standard",
          "replica_count": 3,
          "partition_count": 1,
          "zone_redundancy_enabled": true
        },
        "features": {
          "semantic_ranker_enabled": true,
          "vector_search_enabled": false,
          "ai_enrichment_enabled": false,
          "knowledge_store_enabled": false
        },
        "index_topology": {
          "index_count": 2,
          "indexer_count": 1,
          "skillset_count": 0,
          "total_document_count": 500000,
          "total_index_size_gb": 12.5,
          "vector_index_size_gb": 0
        },
        "security": {
          "api_keys_enabled": false,
          "managed_identity_enabled": true,
          "private_endpoint_enabled": false,
          "customer_managed_keys_enabled": false
        },
        "notes": ["Holiday season peaks at 3x normal traffic"]
      },
      "metrics": {
        "observation_window_days": 30,
        "query": {
          "average_queries_per_second": 85.0,
          "peak_queries_per_second": 250.0,
          "monthly_query_volume": 22000000,
          "p95_query_latency_ms": 45.0,
          "cache_hit_ratio": 0.65
        },
        "indexing": {
          "daily_document_updates": 50000,
          "full_rebuilds_per_month": 4,
          "average_indexing_latency_minutes": 8.0
        },
        "utilization": {
          "replica_utilization_percent": 72.0,
          "partition_utilization_percent": 40.0,
          "storage_utilization_percent": 50.0,
          "semantic_queries_per_day": 180000,
          "vector_queries_per_day": 0
        }
      },
      "include_cost_signals": true,
      "include_feature_assessment": true
    }
    ```

**Expected findings:**

- ✅ Replicas well-utilized for query volume — likely no over-provisioning
- 🟡 Single partition at 50% storage — monitor growth
- ℹ️ Semantic ranker actively used — good feature-to-cost ratio

**Customization tips:**

- Adjust `replica_count` based on your actual peak QPS
- Set `zone_redundancy_enabled: false` for non-production environments
- Add `vector_search_enabled: true` if you're implementing hybrid search

---

## Scenario 2: Enterprise Knowledge Base (RAG)

**When to use:** Internal document search powering a Retrieval-Augmented Generation (RAG) application — corporate wikis, policy docs, technical manuals.

**Key characteristics:**
- Vector search for semantic retrieval
- AI enrichment for document cracking and embedding
- Lower query volume, larger documents

??? example "Full JSON payload (click to expand)"

    ```json
    {
      "configuration": {
        "service_name": "woodgrove-knowledge-search",
        "region": "westus2",
        "capacity": {
          "pricing_model": "dedicated",
          "sku": "standard2",
          "replica_count": 2,
          "partition_count": 2,
          "zone_redundancy_enabled": false
        },
        "features": {
          "semantic_ranker_enabled": true,
          "vector_search_enabled": true,
          "ai_enrichment_enabled": true,
          "knowledge_store_enabled": true
        },
        "index_topology": {
          "index_count": 5,
          "indexer_count": 5,
          "skillset_count": 3,
          "total_document_count": 2000000,
          "total_index_size_gb": 95.0,
          "vector_index_size_gb": 38.0
        },
        "security": {
          "api_keys_enabled": false,
          "managed_identity_enabled": true,
          "private_endpoint_enabled": true,
          "customer_managed_keys_enabled": true
        },
        "notes": ["RAG pipeline queries ~5 chunks per user question", "Documents re-indexed nightly"]
      },
      "metrics": {
        "observation_window_days": 30,
        "query": {
          "average_queries_per_second": 12.0,
          "peak_queries_per_second": 45.0,
          "monthly_query_volume": 3100000,
          "p95_query_latency_ms": 120.0,
          "cache_hit_ratio": 0.28
        },
        "indexing": {
          "daily_document_updates": 15000,
          "full_rebuilds_per_month": 1,
          "average_indexing_latency_minutes": 45.0
        },
        "utilization": {
          "replica_utilization_percent": 55.0,
          "partition_utilization_percent": 47.5,
          "storage_utilization_percent": 66.0,
          "semantic_queries_per_day": 250000,
          "vector_queries_per_day": 250000
        }
      },
      "include_cost_signals": true,
      "include_feature_assessment": true
    }
    ```

**Expected findings:**

- 🟡 2 replicas with 12 QPS — may be slightly over-provisioned for non-peak
- ✅ All features actively used — good alignment
- ℹ️ Knowledge store enabled — verify downstream consumers exist
- ✅ Security posture strong (private endpoint + CMK + managed identity)

**Customization tips:**

- Increase `partition_count` if your vector index exceeds 50GB per partition
- Set `zone_redundancy_enabled: true` for production RAG applications
- Remove `knowledge_store_enabled` if nothing reads from the knowledge store

---

## Scenario 3: Multi-tenant SaaS Platform

**When to use:** A platform serving multiple customers from a shared search service — each tenant has isolated indexes.

**Key characteristics:**
- High index count (one per tenant)
- Standard S3 for large scale
- High replica count for SLA guarantees

??? example "Full JSON payload (click to expand)"

    ```json
    {
      "configuration": {
        "service_name": "fabrikam-saas-search",
        "region": "centralus",
        "capacity": {
          "pricing_model": "dedicated",
          "sku": "standard3",
          "replica_count": 6,
          "partition_count": 3,
          "zone_redundancy_enabled": true
        },
        "features": {
          "semantic_ranker_enabled": true,
          "vector_search_enabled": true,
          "ai_enrichment_enabled": false,
          "knowledge_store_enabled": false
        },
        "index_topology": {
          "index_count": 150,
          "indexer_count": 150,
          "skillset_count": 0,
          "total_document_count": 45000000,
          "total_index_size_gb": 520.0,
          "vector_index_size_gb": 180.0
        },
        "security": {
          "api_keys_enabled": false,
          "managed_identity_enabled": true,
          "private_endpoint_enabled": true,
          "customer_managed_keys_enabled": false
        },
        "notes": [
          "150 tenants, isolated indexes per tenant",
          "Batch indexing window: 2AM-6AM UTC",
          "SLA requires 99.99% uptime"
        ]
      },
      "metrics": {
        "observation_window_days": 30,
        "query": {
          "average_queries_per_second": 320.0,
          "peak_queries_per_second": 800.0,
          "monthly_query_volume": 82000000,
          "p95_query_latency_ms": 65.0,
          "cache_hit_ratio": 0.45
        },
        "indexing": {
          "daily_document_updates": 2000000,
          "full_rebuilds_per_month": 0,
          "average_indexing_latency_minutes": 12.0
        },
        "utilization": {
          "replica_utilization_percent": 68.0,
          "partition_utilization_percent": 87.0,
          "storage_utilization_percent": 86.7,
          "semantic_queries_per_day": 500000,
          "vector_queries_per_day": 1200000
        }
      },
      "include_cost_signals": true,
      "include_feature_assessment": true
    }
    ```

**Expected findings:**

- ✅ Replicas well-utilized given 320 QPS and SLA requirement
- 🟠 Storage at 87% — plan capacity expansion
- 🟡 Consider S3HD for high index count workloads (200+ indexes)
- ✅ Features actively used, good cost alignment

**Customization tips:**

- If you have >200 indexes, consider switching to S3HD (1000 index limit)
- Reduce `replica_count` to 4 if SLA allows 99.9% (non-zone-redundant pair)
- Add `customer_managed_keys_enabled: true` for regulated industries

---

## Scenario 4: Small Catalog / Starter App

**When to use:** Small application just getting started — product prototypes, internal tools, small document sets.

**Key characteristics:**
- Basic SKU
- Minimal features
- Low utilization (common for new or dev services)

??? example "Full JSON payload (click to expand)"

    ```json
    {
      "configuration": {
        "service_name": "tailwind-dev-search",
        "region": "eastus2",
        "capacity": {
          "pricing_model": "dedicated",
          "sku": "basic",
          "replica_count": 1,
          "partition_count": 1,
          "zone_redundancy_enabled": false
        },
        "features": {
          "semantic_ranker_enabled": false,
          "vector_search_enabled": false,
          "ai_enrichment_enabled": false,
          "knowledge_store_enabled": false
        },
        "index_topology": {
          "index_count": 1,
          "indexer_count": 1,
          "skillset_count": 0,
          "total_document_count": 25000,
          "total_index_size_gb": 0.8,
          "vector_index_size_gb": 0
        },
        "security": {
          "api_keys_enabled": true,
          "managed_identity_enabled": false,
          "private_endpoint_enabled": false,
          "customer_managed_keys_enabled": false
        },
        "notes": ["Development environment, exploring search capabilities"]
      },
      "metrics": {
        "observation_window_days": 14,
        "query": {
          "average_queries_per_second": 0.3,
          "peak_queries_per_second": 5.0,
          "monthly_query_volume": 8000,
          "p95_query_latency_ms": 25.0,
          "cache_hit_ratio": 0.10
        },
        "indexing": {
          "daily_document_updates": 500,
          "full_rebuilds_per_month": 8,
          "average_indexing_latency_minutes": 2.0
        },
        "utilization": {
          "replica_utilization_percent": 5.0,
          "partition_utilization_percent": 40.0,
          "storage_utilization_percent": 40.0,
          "semantic_queries_per_day": 0,
          "vector_queries_per_day": 0
        }
      },
      "include_cost_signals": true,
      "include_feature_assessment": true
    }
    ```

**Expected findings:**

- 🟡 Service appears idle (QPS < 1) — confirm it's intentionally running
- ℹ️ Consider the Free tier for development workloads
- 🟡 API keys enabled without managed identity — security improvement available
- ✅ Appropriately sized for current workload

**Customization tips:**

- Switch to Free tier if this is purely for development/testing
- Enable `managed_identity_enabled` and disable `api_keys_enabled` for better security
- When ready for production, start with Standard + 2 replicas for HA

---

## Scenario 5: Media & Content Platform

**When to use:** News sites, content management systems, media libraries with large document corpora and frequent updates.

**Key characteristics:**
- High indexing throughput (real-time content publishing)
- Moderate query volume
- AI enrichment for image/video metadata extraction

??? example "Full JSON payload (click to expand)"

    ```json
    {
      "configuration": {
        "service_name": "litware-media-search",
        "region": "westeurope",
        "capacity": {
          "pricing_model": "dedicated",
          "sku": "standard2",
          "replica_count": 3,
          "partition_count": 4,
          "zone_redundancy_enabled": true
        },
        "features": {
          "semantic_ranker_enabled": true,
          "vector_search_enabled": true,
          "ai_enrichment_enabled": true,
          "knowledge_store_enabled": false
        },
        "index_topology": {
          "index_count": 8,
          "indexer_count": 6,
          "skillset_count": 4,
          "total_document_count": 8000000,
          "total_index_size_gb": 280.0,
          "vector_index_size_gb": 95.0
        },
        "security": {
          "api_keys_enabled": false,
          "managed_identity_enabled": true,
          "private_endpoint_enabled": true,
          "customer_managed_keys_enabled": false
        },
        "notes": [
          "Real-time content publishing pipeline",
          "AI enrichment extracts entities, sentiment, and image tags",
          "Multi-language content (EN, DE, FR, ES)"
        ]
      },
      "metrics": {
        "observation_window_days": 30,
        "query": {
          "average_queries_per_second": 55.0,
          "peak_queries_per_second": 180.0,
          "monthly_query_volume": 14200000,
          "p95_query_latency_ms": 95.0,
          "cache_hit_ratio": 0.52
        },
        "indexing": {
          "daily_document_updates": 500000,
          "full_rebuilds_per_month": 1,
          "average_indexing_latency_minutes": 18.0
        },
        "utilization": {
          "replica_utilization_percent": 62.0,
          "partition_utilization_percent": 70.0,
          "storage_utilization_percent": 70.0,
          "semantic_queries_per_day": 320000,
          "vector_queries_per_day": 180000
        }
      },
      "include_cost_signals": true,
      "include_feature_assessment": true
    }
    ```

**Expected findings:**

- ✅ Well-balanced configuration for workload
- ℹ️ Storage at 70% with high indexing rate — monitor growth trajectory
- 🟡 4 partitions with S2 (400GB capacity) — may approach limits within 6 months
- ✅ AI enrichment actively used with skillsets — good alignment

**Customization tips:**

- Plan for S3 if storage growth continues at current rate
- Consider reducing `full_rebuilds_per_month` if incremental indexing covers all changes
- Add `knowledge_store_enabled` if you need to feed enriched data to a data lake

---

## Scenario 6: Idle/Forgotten Service (Cost Recovery)

**When to use:** Services that appear in your subscription but may be forgotten, abandoned, or left running after a project ended.

**Key characteristics:**
- Near-zero query traffic
- No recent indexing activity
- Often the result of POCs or decommissioned apps

??? example "Full JSON payload (click to expand)"

    ```json
    {
      "configuration": {
        "service_name": "adventure-works-poc-search",
        "region": "southcentralus",
        "capacity": {
          "pricing_model": "dedicated",
          "sku": "standard",
          "replica_count": 2,
          "partition_count": 1,
          "zone_redundancy_enabled": false
        },
        "features": {
          "semantic_ranker_enabled": true,
          "vector_search_enabled": true,
          "ai_enrichment_enabled": true,
          "knowledge_store_enabled": true
        },
        "index_topology": {
          "index_count": 3,
          "indexer_count": 2,
          "skillset_count": 2,
          "total_document_count": 150000,
          "total_index_size_gb": 4.2,
          "vector_index_size_gb": 1.8
        },
        "security": {
          "api_keys_enabled": true,
          "managed_identity_enabled": false,
          "private_endpoint_enabled": false,
          "customer_managed_keys_enabled": false
        },
        "notes": ["POC from Q1 2024, unclear if still needed"]
      },
      "metrics": {
        "observation_window_days": 30,
        "query": {
          "average_queries_per_second": 0.02,
          "peak_queries_per_second": 0.5,
          "monthly_query_volume": 52,
          "p95_query_latency_ms": 15.0,
          "cache_hit_ratio": 0.0
        },
        "indexing": {
          "daily_document_updates": 0,
          "full_rebuilds_per_month": 0,
          "average_indexing_latency_minutes": 0
        },
        "utilization": {
          "replica_utilization_percent": 0.5,
          "partition_utilization_percent": 21.0,
          "storage_utilization_percent": 16.8,
          "semantic_queries_per_day": 0,
          "vector_queries_per_day": 0
        }
      },
      "include_cost_signals": true,
      "include_feature_assessment": true
    }
    ```

**Expected findings:**

- 🔴 Service appears idle — 52 queries/month, no indexing activity
- 🟠 All premium features enabled but unused — immediate cost savings available
- 🟠 2 replicas for near-zero traffic — reduce to 1 or decommission
- 🟡 API keys enabled, no managed identity — security gap on an unmonitored service
- 💰 Estimated waste: ~$800+/month

**Customization tips:**

- If the service IS needed: reduce to 1 replica, disable unused features, downgrade to Basic
- If the service is NOT needed: export index definitions, then delete
- Use the `discover` endpoint to find all services like this across your subscription

---

## Using scenarios with the API

### Submit via curl

```bash
# Save a scenario to a file
curl -X POST http://localhost:8000/analyze \
  -H 'Content-Type: application/json' \
  -d @docs/user-guide/scenarios/ecommerce-production.json
```

### Submit via the chat UI

1. Open the UI at `http://localhost:5173`
2. Type: "Analyze this configuration:" and paste the JSON
3. Or describe it naturally: "I have a Standard S2 with 3 replicas, 4 partitions, 8 million documents, and heavy AI enrichment usage"

### Batch multiple services

```bash
# Analyze all your services in sequence
for scenario in scenarios/*.json; do
  echo "=== Analyzing: $scenario ==="
  curl -s -X POST http://localhost:8000/analyze \
    -H 'Content-Type: application/json' \
    -d @"$scenario" | python -m json.tool
done
```

---

## Building your own scenario

Start from the closest matching scenario above and modify these fields:

1. **`capacity`** — Match your actual SKU, replica count, and partition count
2. **`index_topology`** — Use Azure Portal → Search Service → Overview for real numbers
3. **`metrics.query`** — Check Azure Monitor metrics for your service
4. **`metrics.utilization`** — Available in the Azure Portal Monitoring tab
5. **`notes`** — Add context the advisor can use (traffic patterns, SLA requirements)

!!! tip "Use live discovery instead"
    If your services are in Azure, skip manual JSON entirely:
    ```bash
    curl http://localhost:8000/discover/services?subscription_id=YOUR_SUB_ID
    ```
    This auto-detects services and returns configurations ready for analysis.

---

**Next:** [Automation & Scripting →](automation.md)
