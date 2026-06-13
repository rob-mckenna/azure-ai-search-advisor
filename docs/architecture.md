# Architecture

Azure AI Search Advisor is built as a thin HTTP layer over reusable service components, with optional caching, SQLite-backed history, and a multi-agent orchestration layer for Microsoft Foundry scenarios.

## System diagram

```mermaid
flowchart TD
    Client[API client or React UI] --> FastAPI[FastAPI application]
    FastAPI --> Middleware[Correlation ID + CORS + optional rate limiting]
    Middleware --> Analyze[/POST /analyze]
    Middleware --> Recommend[/POST /recommend]
    Middleware --> Simulate[/POST /simulate]
    Middleware --> Discover[/GET /discover]
    Middleware --> History[/GET /history/{service_name}]
    Middleware --> Health[/GET /health]

    Analyze --> Cache[Optional response cache]
    Analyze --> Ingestion[IngestionService]
    Ingestion --> Analysis[AnalysisService]
    Analyze --> HistoryWriter[HistoryService]

    Recommend --> Ingestion
    Recommend --> Analysis
    Recommend --> Cost[CostModelingService]
    Recommend --> Guidance[RecommendationService]
    Recommend --> HistoryWriter

    Simulate --> Cost

    Discover --> Live[LiveIngestionService]
    Live --> ARG[Azure Resource Graph]
    Live --> ARM[Azure Search management API]
    Live --> Analysis

    History --> HistoryReader[HistoryService]
    HistoryReader --> SQLite[(SQLite history.db)]

    Guidance --> Orchestrator[Optional Agent Orchestrator]
    Orchestrator --> Specialists[Ingestion, Analysis, Cost, Recommendation agents]
    Orchestrator --> Foundry[Microsoft Foundry / Agent Framework]

    Ingestion --> Models[Shared Pydantic models]
    Analysis --> Models
    Cost --> Models
    Guidance --> Models
    Models --> Repo[JSON repository seam in data/]
```

## Main runtime pieces

### API layer

`src/azure_ai_search_advisor/main.py` creates the FastAPI app and registers:

- `/analyze`
- `/recommend`
- `/simulate`
- `/discover`
- `/history`
- `/health`

The app also standardizes validation and HTTP error responses through `ErrorResponse`.

### Shared middleware and operational concerns

- **Correlation IDs:** `CorrelationIdMiddleware` annotates requests and logs.
- **CORS:** Origins come from `CORS_ALLOWED_ORIGINS`.
- **Authentication:** `get_current_user()` enforces Microsoft Entra bearer validation only when `AUTH_ENABLED=true`.
- **Rate limiting:** `check_rate_limit()` applies an in-memory sliding window when enabled.
- **Caching:** `/analyze` can return cached responses when `CACHE_ENABLED=true`.

## Data flow

The core advisor flow is intentionally layered:

1. **Ingest**  
   API payloads are normalized into internal snapshot models by `IngestionService` or `LiveIngestionService`.
2. **Analyze**  
   `AnalysisService` combines provisioning, SKU, and feature analyzers with heuristic findings.
3. **Cost model**  
   `CostModelingService` estimates dedicated, serverless, and feature add-on costs.
4. **Recommend**  
   `RecommendationService` ranks remediation actions such as replica reductions, partition reductions, or pricing-model changes.
5. **Persist history**  
   `HistoryService` writes summarized runs and trend points into the local SQLite store.

That ingest -> analyze -> cost -> recommend chain appears directly inside the `/recommend` route when clients submit raw configuration plus metrics.

## Multi-agent orchestration

The orchestration package supports two modes controlled by `ORCHESTRATION_MODE`:

### `local`

The default. Requests are handled through deterministic service chaining inside the process:

- ingestion agent validates or loads the workload snapshot
- analysis agent runs inefficiency detection
- cost agent builds pricing scenarios
- recommendation agent synthesizes guidance

### `framework`

When Microsoft Agent Framework support is available, `AgentFrameworkOrchestrator` registers specialist agents and exposes their tool bindings to a hosted agent runtime. The local orchestration logic still provides the execution plan and fallback behavior.

## Live Azure discovery path

`LiveIngestionService` uses `DefaultAzureCredential` and two Azure-facing clients:

- **Azure Resource Graph** to enumerate visible search services
- **Azure Search management APIs** to ingest a single service into an advisor snapshot

This design keeps Azure-specific concerns isolated from the normal JSON payload flow.

## Persistence model

The repository now uses two persistence seams:

- **`JsonRepository`** for JSON-backed artifacts under `data/`
- **`HistoryDatabase`** for SQLite-backed analysis history, defaulting to `data/history.db`

`HistoryService` stores:

- run summaries
- finding summaries
- cost snapshots
- recommendation summaries

Those records drive the `/history/{service_name}` and `/history/{service_name}/trends` endpoints.

## Technology stack

| Layer | Technology |
| --- | --- |
| API | FastAPI |
| Models | Pydantic v2 |
| Auth | `python-jose` + Microsoft Entra JWKS validation |
| Azure identity | `azure-identity` with `DefaultAzureCredential` |
| Azure discovery | `azure-mgmt-resourcegraph`, `azure-mgmt-search` |
| AI integration | `azure-ai-projects`, `openai`, Microsoft Foundry |
| UI | React 18 + Vite + TypeScript |
| Persistence | SQLite + JSON files |
| Hosting | Azure Container Apps + Azure Static Web Apps |
| IaC | Azure Developer CLI, Bicep, Terraform |

## Design principles

- Keep route handlers thin.
- Keep Azure-specific integrations behind dedicated adapters and services.
- Use shared Pydantic contracts instead of ad hoc dictionaries at the HTTP boundary.
- Allow the same business services to power direct API calls, local orchestration, and future Foundry-hosted agent flows.

