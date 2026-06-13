# Azure AI Search Advisor

Azure AI Search Advisor is a FastAPI service for analyzing Azure AI Search workloads, estimating cost trade-offs, generating optimization guidance, and retaining historical run data for trend review.

## What this project does

The current codebase gives you a working API surface and supporting service layers for:

- analyzing search capacity, SKU fit, and premium feature usage
- comparing dedicated and serverless pricing scenarios
- generating prioritized right-sizing recommendations
- discovering live Azure AI Search services through Azure credentials
- reviewing stored history and cost trends for a service
- prototyping a React chat UI and Microsoft Foundry-backed multi-agent experience

!!! info "Current state"
    The repository is no longer just a placeholder API. `/analyze`, `/recommend`, `/simulate`, `/discover`, `/history`, and `/health` are wired into concrete request and response contracts. The orchestration layer remains intentionally extensible as the Microsoft Agent Framework integration matures.

## Quick links

- [Getting Started](getting-started.md)
- [Architecture](architecture.md)
- [API Reference](api/index.md)
- [Deployment Guide](deployment/index.md)
- [UI Development](ui/index.md)
- [Contributing](contributing.md)

## Runtime surface

| Area | What is included |
| --- | --- |
| API | FastAPI app in `src/azure_ai_search_advisor/main.py` |
| Analysis | Provisioning, SKU, and feature analyzers |
| Cost modeling | Dedicated, serverless, and feature cost estimation |
| Recommendations | Right-sizing, pricing, and feature guidance synthesis |
| Discovery | Azure Resource Graph + management-plane live inspection |
| History | SQLite-backed run summaries and trend endpoints |
| UI | React + Vite prototype in `ui/` |
| Infrastructure | `azd`, standalone Bicep, and Terraform options in `infra/` |

## Fast local start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp .env.example .env
python -m uvicorn azure_ai_search_advisor.main:app --reload
```

Then open:

- API root: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Typical workflow

1. Submit a configuration and metrics snapshot to [`POST /analyze`](api/analyze.md).
2. Feed the analysis output or raw inputs into [`POST /recommend`](api/recommend.md).
3. Compare proposed changes with [`POST /simulate`](api/simulate.md).
4. If you have Azure credentials, enumerate real services with [`GET /discover`](api/discover.md).
5. Review accumulated runs with [`GET /history/{service_name}`](api/history.md).

## Deployment options

- [`deployment/azd.md`](deployment/azd.md): full stack with Azure Container Apps + Static Web Apps
- [`deployment/bicep.md`](deployment/bicep.md): standalone Bicep for the Foundry backend
- [`deployment/terraform.md`](deployment/terraform.md): Terraform equivalent of the Foundry resources
- [`deployment/docker.md`](deployment/docker.md): local containerized API development

