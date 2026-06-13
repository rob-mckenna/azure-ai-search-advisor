# Azure AI Search Advisor – Squad Bootstrap

## Context

We are building a tool called **Azure AI Search Advisor**.

This tool helps customers:
- Understand Azure AI Search configurations
- Optimize cost (Search Units, replicas, partitions, serverless vs dedicated)
- Choose the right features (semantic ranker, vector search, AI enrichment)
- Identify inefficiencies and over-provisioning
- Generate actionable recommendations and optional remediation steps

The tool should be modular, extensible, and production-ready.

---

## Mission

Design and scaffold a complete project that includes:

1. A multi-agent system for analysis and recommendation
2. API surface for interacting with the system
3. A clean project structure for iterative development
4. Mock data inputs and sample outputs
5. Clear TODO markers for further implementation

DO NOT implement full logic — focus on high-quality scaffolding.

---

## Team (Agents)

### 1. Architect Agent
- Define overall system architecture
- Select technology stack
- Ensure modular design

### 2. Data & Ingestion Agent
- Define input schema for Azure AI Search configuration and metrics
- Create mock datasets (JSON)

### 3. Analysis Agent
- Define logic for identifying inefficiencies:
  - Over-provisioned replicas/partitions
  - Incorrect SKU
  - Misused features

### 4. Cost Modeling Agent
- Model cost drivers:
  - Search Units (replicas × partitions)
  - Serverless compute units
  - Feature-level costs (semantic, enrichment, vector)

### 5. Recommendation Agent
- Generate:
  - Right-sizing recommendations
  - Feature usage guidance
  - Pricing model suggestions (Dedicated vs Serverless)

### 6. API & Integration Agent
- Define endpoints:
  - `/analyze`
  - `/recommend`
  - `/simulate`
- Ensure clean API contracts

### 7. Developer Experience Agent
- Create README
- Define repo structure
- Provide run instructions

---

## Architecture Guidelines

- Backend: Python (FastAPI) or .NET Web API
- Agent orchestration: Microsoft Agent Framework
- AI platform: Microsoft Foundry (project-based model access)
- Authentication: DefaultAzureCredential (no API keys permitted)
- UI: React (TypeScript, Vite) — deployable as Azure Static Web App
- Data: JSON (initial), extensible later
- Deployment: Docker-ready, GitHub Actions CI/CD

---

## Platform & Security Directives

These are organizational mandates. Agents must follow these from the start — do not deviate.

| Directive | Use | Do NOT Use |
|-----------|-----|------------|
| Orchestration | Microsoft Agent Framework | Semantic Kernel, LangChain, or other frameworks |
| AI Platform | Microsoft Foundry (flat project architecture) | Direct Azure OpenAI endpoints, Azure AI Studio |
| Authentication | `DefaultAzureCredential` (managed identity, az login, workload identity) | API keys, connection strings with embedded secrets |
| Terminology | "Microsoft Foundry" | "Azure AI Foundry", "Azure AI Studio", "Foundry Hub" |

### Why these matter

- **Microsoft Agent Framework** is the standard for multi-agent orchestration in this org.
- **Microsoft Foundry** provides unified project management for model deployments, prompt flows, and agent configuration — one endpoint, one RBAC model.
- **DefaultAzureCredential** ensures zero secrets in code, config, or environment variables. RBAC roles (e.g., `Cognitive Services OpenAI User`) control access.

---

## Infrastructure as Code

Provision the Microsoft Foundry backend and hosting infrastructure automatically. Bicep, Terraform, and Azure Developer CLI (`azd`) deployment options must be provided.

### Directory structure

```
azure.yaml                  # Azure Developer CLI project manifest
infra/
├── README.md               # Overview, comparison table, deploy instructions for all options
├── main.bicep              # azd entry point (subscription-scoped, creates RG + all resources)
├── main.parameters.json    # azd parameters (injected by azd)
├── bicep/                  # Standalone Azure Bicep templates
│   ├── main.bicep          # Resource-group-scoped standalone deployment
│   ├── main.bicepparam
│   └── modules/            # Shared Bicep modules (used by both azd and standalone)
│       ├── ai-foundry.bicep
│       ├── role-assignment.bicep
│       ├── container-registry.bicep
│       ├── container-apps-environment.bicep
│       ├── container-app.bicep
│       └── static-web-app.bicep
└── terraform/              # Terraform configuration
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    └── terraform.tfvars.example
```

### Requirements

| Requirement | Detail |
|-------------|--------|
| Architecture | Microsoft Foundry **flat project** only — do NOT create a Hub (`kind: Hub`) resource |
| Resources | Azure AI Services account → Model deployment → Foundry Project (`kind: Project`) → AAD connection |
| Hosting | Container Apps (API) + Static Web Apps (UI) + Container Registry |
| Auth | `disableLocalAuth: true` on AI Services — no API keys provisioned |
| RBAC | Assign `Cognitive Services OpenAI User` to the deploying principal and container app managed identity |
| Default model | Deploy `gpt-4o` as the default model |
| Terraform provider | Use `azapi` for the Foundry project resource (flat model may not be in `azurerm` yet) |
| azd support | `azure.yaml` at project root; `azd up` provisions everything and deploys API + UI |
| Idempotent | Safe to re-run without errors |

### What NOT to create

- ❌ AI Hub (`Microsoft.MachineLearningServices/workspaces` with `kind: Hub`)
- ❌ Storage Account (Hub dependency — not needed for flat project)
- ❌ Key Vault (Hub dependency — not needed for flat project)
- ❌ Any `hubResourceId` reference on the project

---

## Multi-Agent Orchestration

The system must be structured as a multi-agent architecture using Microsoft Agent Framework, deployable as a Microsoft Foundry Hosted Agent.

### Agent architecture

```
Orchestrator Agent (entry point — Foundry Hosted Agent)
├── Ingestion Agent (tool: fetch/validate Azure AI Search config)
├── Analysis Agent (tool: detect inefficiencies)
├── Cost Agent (tool: model pricing scenarios)
└── Recommendation Agent (tool: generate actionable guidance)
```

### Directory structure

```
src/{project}/orchestration/
├── agents/
│   ├── orchestrator.py          # Entry point — deployed as Foundry Hosted Agent
│   ├── ingestion_agent.py       # Wraps ingestion service
│   ├── analysis_agent.py        # Wraps analysis service
│   ├── cost_agent.py            # Wraps cost modeling service
│   └── recommendation_agent.py  # Wraps recommendation service
├── tools/
│   ├── ingestion_tools.py       # Tool functions for ingestion
│   ├── analysis_tools.py        # Tool functions for analysis
│   ├── cost_tools.py            # Tool functions for cost modeling
│   └── recommendation_tools.py  # Tool functions for recommendations
├── config.py                    # System prompts, model config, tool bindings
├── registry.py                  # Builds and wires the full agent graph
└── deploy.py                    # Registers with Foundry as Hosted Agent
```

### Requirements

| Requirement | Detail |
|-------------|--------|
| Framework | Microsoft Agent Framework |
| Deployment | Microsoft Foundry Hosted Agent |
| Tool pattern | Plain Python functions with type hints + docstrings (docstring = tool description) |
| Agent prompts | Each specialist has a focused system prompt defining expertise and constraints |
| Orchestrator | Decomposes user queries, delegates to specialists, assembles responses |
| Dual interface | FastAPI API layer remains as secondary interface (both call same services) |
| No logic duplication | Tools call into domain services — don't rewrite business logic |

### What the Orchestrator does

- Receives natural language queries ("Why is my cost high?", "Analyze my search service")
- Decomposes into sub-tasks based on intent
- Delegates to specialist agents via tool calls
- Assembles and formats the final response

---

## User Interface (React)

A React frontend must be included. It must run locally for development and deploy to Azure Static Web Apps for production.

### Directory structure

```
ui/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── .env.example
├── staticwebapp.config.json
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/       # Chat UI components
│   ├── services/
│   │   ├── auth.ts       # Azure browser auth
│   │   └── foundryClient.ts  # Microsoft Foundry agent client
│   ├── types/
│   └── styles/
└── README.md
```

### Requirements

| Requirement | Detail |
|-------------|--------|
| Framework | React + TypeScript + Vite |
| Local auth | `InteractiveBrowserCredential` from `@azure/identity` |
| Deployed auth | Azure Static Web Apps built-in auth (`.auth/`) |
| Agent connection | Chat with Microsoft Foundry agent endpoint via authenticated fetch |
| UI pattern | Chat interface (message list, input, loading state) |
| Deployment | Azure Static Web Apps with `staticwebapp.config.json` |
| No API keys | All auth via DefaultAzureCredential / browser credential |

---

## CI/CD (GitHub Actions)

All components must have GitHub Actions workflows for automated build, test, and deployment.

### Required workflows

```
.github/workflows/
├── ci.yml              # Lint, test, build the backend (Python)
├── deploy-api.yml      # Deploy backend to Azure Container Apps
├── deploy-infra.yml    # Provision Microsoft Foundry (Bicep or Terraform)
└── deploy-ui.yml       # Deploy React UI to Azure Static Web Apps
```

### Requirements

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `ci.yml` | Push/PR to main (Python files) | Lint (ruff), type check (mypy), test (pytest), Docker build + health check |
| `deploy-api.yml` | Push to main (src/Dockerfile) | Build image → push to ACR → deploy to Container Apps |
| `deploy-infra.yml` | Push to main (infra/) + manual dispatch | Validate + deploy Bicep; Terraform option via workflow_dispatch |
| `deploy-ui.yml` | Push to main (ui/) | Build React app → deploy to Azure Static Web Apps |

### Constraints

- All workflows use `azure/login@v2` with workload identity federation (`id-token: write`)
- No secrets or API keys in workflow definitions
- Infrastructure workflow validates templates before deploying
- CI runs on Python 3.11 + 3.12 matrix

---

## Execution Plan

Follow these steps in order:

1. Define the project structure:
   - folders, modules, and services

2. Create core data models:
   - Azure AI Search configuration
   - Metrics (queries, index size, feature usage)

3. Scaffold agent components:
   - ingestion
   - analysis
   - cost modeling
   - recommendations

4. Define API layer:
   - endpoints
   - request/response contracts
   - Wire endpoints to domain services (functional, not just stubs)

5. Create multi-agent orchestration:
   - Orchestrator agent (entry point)
   - Specialist agents (ingestion, analysis, cost, recommendation)
   - Tool functions wrapping domain services
   - Agent registry and deployment script
   - System prompts and config for each agent

6. Add mock data:
   - realistic Azure AI Search scenarios

7. Generate sample outputs:
   - analysis results
   - cost insights
   - recommendations

8. Create Infrastructure as Code:
   - `infra/bicep/` — Bicep templates with modules
   - `infra/terraform/` — Terraform config with azapi provider
   - `azure.yaml` + `infra/main.bicep` — Azure Developer CLI (`azd up`) support
   - Hosting modules: Container Registry, Container Apps, Static Web Apps
   - `infra/README.md` — comparison and deploy instructions for all options
   - Microsoft Foundry flat project only (no Hub)

9. Create React UI:
   - Chat interface connected to Microsoft Foundry agent
   - Azure browser auth (InteractiveBrowserCredential)
   - Azure Static Web Apps config for deployment
   - Local dev with `npm run dev`

10. Create GitHub Actions workflows:
    - `ci.yml` — lint, test, Docker build
    - `deploy-api.yml` — deploy backend to Container Apps
    - `deploy-infra.yml` — provision Microsoft Foundry (Bicep + Terraform)
    - `deploy-ui.yml` — deploy React UI to Static Web Apps

11. Create README:
    - overview
    - setup instructions
    - infrastructure provisioning reference
    - UI development guide
    - future enhancements

---

## Constraints

- No full implementations — scaffolding only
- Use TODO placeholders for logic
- Keep components decoupled
- Keep naming consistent and clear

---

## Nice-to-Have Extensions

- Natural language interface ("Why is my cost high?")
- Integration with Azure Cost Management
- Integration with Azure Monitor metrics
- Export recommendations as JSON or Markdown reports

---

## Final Goal

Produce a scaffold that:
- Works seamlessly with GitHub Copilot
- Enables rapid feature iteration
- Can be demonstrated to customers as a working prototype

### Platform Integration Agent (future)
- Expose APIs via APIM MCP Server
- Enable agent-to-agent (A2A) scenarios
- Extend Microsoft Foundry integration (evaluations, prompt management, tracing)