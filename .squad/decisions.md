# Squad Decisions

## Active Decisions

No decisions recorded yet.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction


## 2026-06-12 Bootstrap Decisions

### 2026-06-12T15:25:12-04:00: Project structure decision
**By:** Thrawn (Lead / Architect)
**What:** Chose a src-based Python/FastAPI layout centered on domain packages (`ingestion`, `analysis`, `cost_modeling`, `recommendations`), an `api` layer with dedicated route modules for `/analyze`, `/recommend`, and `/simulate`, an `orchestration` package for Semantic Kernel coordination, `integrations/azure_openai` for external AI clients, `repositories` for JSON-backed persistence, and `core`/`models` for shared configuration and contracts. Added Docker and compose scaffolding to keep local and container execution aligned from the start.
**Why:** This keeps business capabilities isolated, gives the future agent workflow a clear orchestration boundary, and avoids coupling API handlers directly to Azure or persistence concerns. The src layout, package placeholders, and container scaffolding make the project extensible, testable, and production-ready while still staying within the bootstrap constraint of scaffolding only.

# 2026-06-12T15:25:12-04:00: Data contract and mock dataset shape
**By:** Boba (Data & Ingestion)
**What:** Defined a schema-first Azure AI Search snapshot contract using Pydantic models under `src/azure_ai_search_advisor/models/`. The contract centers on a top-level `AzureSearchServiceSnapshot` with nested `configuration` and `metrics` models, including explicit feature configuration objects for semantic ranker, vector search, and AI enrichment. Added an ingestion scaffold that loads JSON snapshots, validates them at the boundary, and leaves TODO hooks for future normalization and enrichment.

**Why:** Downstream analysis, cost modeling, and recommendation work need a stable, explicit input contract before business logic is added. Using a single snapshot shape for both mock data and future real ingestions keeps the pipeline consistent, enforces quality early, and makes scenario fixtures realistic enough to support later rule development.

**Data scenarios added:**
- `over_provisioned.json` for oversized dedicated capacity relative to traffic and storage
- `underutilized_features.json` for premium features enabled with very low observed usage
- `well_optimized.json` for a healthy dedicated deployment aligned to workload
- `serverless_candidate.json` for a low-volume dedicated workload that should likely move to serverless

### 2026-06-12T15:27:59-04:00: Analysis scaffolding design
**By:** Ahsoka (Analysis)
**What:** Structured the analysis domain around three focused analyzers (`ProvisioningAnalyzer`, `SkuAnalyzer`, `FeatureAnalyzer`) plus an `AnalysisService` orchestrator. Added a shared `AnalysisFinding` model with structured evidence so each analyzer can emit normalized findings while retaining analyzer-specific result envelopes.
**Why:** This keeps inefficiency detection logic decoupled by concern, gives downstream recommendation/cost components a consistent finding contract, and leaves clean TODO seams for plugging in concrete configuration and metrics models once the ingestion/data-model work lands.

### 2026-06-12T15:25:12-04:00: Cost modeling scaffold decision
**By:** Lando (Cost Modeling)
**What:** Added a dedicated `cost_modeling` scaffold with separate modules for Search Unit pricing, serverless query pricing, feature-level add-on pricing, reference pricing data, and an orchestration service. Added shared `models/cost_models.py` contracts so cost estimates, comparisons, pricing tiers, and feature line items have explicit request/response shapes.
**Why:** Cost drivers differ enough that each needs an isolated module and contract, while the service layer should still assemble a single breakdown and comparison output. Approximate Azure AI Search pricing constants are intentionally embedded and clearly labeled so the scaffold can demonstrate realistic economics now without pretending to be production billing logic.

### 2026-06-12T15:27:59-04:00: Recommendations scaffolding decision
**By:** Mace (Recommendations)
**What:** Standardized recommendation generation around shared `Recommendation` and `RecommendationReport` models in `models/recommendations.py`, then split generation into dedicated `rightsizing`, `feature_guidance`, and `pricing_advisor` modules orchestrated by `RecommendationService`.
**Why:** This keeps recommendation synthesis decoupled from analysis and cost modeling, makes each recommendation family easy to extend independently, and gives the API a single ranked report shape to return. The generators currently rely on explicit analysis findings plus cost inputs with TODO markers where deeper heuristics will be added later, which matches the bootstrap goal of realistic scaffolding without full business logic.

### 2026-06-12T15:25:12-04:00: API contract scaffolding for FastAPI surface
**By:** Mando (API & Integration)
**What:** Defined a contract-first API layer under `src/azure_ai_search_advisor/api/` with dedicated routers for `/analyze`, `/recommend`, `/simulate`, and `/health`; centralized all HTTP-layer Pydantic schemas in `api/schemas.py`; added documented request examples, shared error envelopes, dependency provider stubs, and router registration in `main.py`.
**Why:** Keeping API schemas separate from domain models makes the external contract explicit and stable while the analysis, recommendation, and cost engines are still scaffold-only. Standardized error responses and rich OpenAPI examples let downstream clients integrate now, even before business services are implemented.

### 2026-06-12T15:27:59-04:00: Documentation and onboarding decision
**By:** Wedge (Developer Experience)
**What:** Created a root `README.md`, `CONTRIBUTING.md`, and `.env.example` that document the scaffold as a FastAPI-based Azure AI Search Advisor. The README now explains the project purpose, package architecture, extension points, quick-start flow, `/analyze` `/recommend` `/simulate` endpoint usage, environment variables, Azure AI Foundry setup expectations, and bootstrap follow-on enhancements. I also pointed `pyproject.toml` package metadata at `README.md` so published/project metadata resolves to the real front-door documentation.
**Why:** The repository now has enough structure that onboarding quality depends more on clarity than code volume. A developer should be able to understand the scaffold, run the service, and see where to add analyzers or recommendation logic without opening every file. The docs intentionally describe the current state as scaffolded so expectations stay accurate while still presenting the project professionally.
