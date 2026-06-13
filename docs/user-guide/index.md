# User Guide

Welcome to the Azure AI Search Advisor — a tool that analyzes your Azure AI Search service configurations, identifies optimization opportunities, and provides actionable recommendations to reduce costs and improve performance.

## Who is this for?

- **Cloud architects** evaluating search service sizing
- **Platform engineers** managing multiple search services across subscriptions
- **Developers** building search applications who want cost-efficient configurations
- **FinOps teams** looking for Azure cost optimization opportunities

## What can it do?

| Capability | Description |
|-----------|-------------|
| **Analyze** | Evaluate provisioning, features, and SKU fit for a search service |
| **Recommend** | Generate prioritized actions with estimated savings |
| **Simulate** | Model "what-if" scenarios (SKU changes, replica scaling) |
| **Discover** | Auto-detect search services across your Azure subscriptions |
| **Track** | Store analysis history and show optimization trends over time |
| **Alert** | Suggest Azure Monitor alert rules for proactive monitoring |

## Two ways to use it

### 1. Chat UI (recommended for exploration)

The React-based chat interface lets you interact conversationally:

![Chat UI Overview](img/chat-ui-overview.png)

*The chat interface with quick actions for common workflows.*

### 2. REST API (recommended for automation)

Call the API directly for CI/CD pipelines, scripts, or custom integrations:

```bash
curl -X POST http://localhost:8000/analyze \
  -H 'Content-Type: application/json' \
  -d @scenarios/ecommerce-production.json
```

## Quick start (5 minutes)

1. **Start the API:**
   ```bash
   python -m uvicorn azure_ai_search_advisor.main:app --reload
   ```

2. **Open the UI:**
   ```bash
   cd ui && npm install && npm run dev
   ```
   Navigate to `http://localhost:5173`

3. **Click "Analyze sample service"** — the UI sends a pre-built payload and shows findings immediately.

4. **Try a starter scenario** — copy one from the [Scenarios](scenarios.md) page and paste the JSON into the API, or describe your service in the chat.

## Guide sections

| Page | What you'll learn |
|------|-------------------|
| [Using the Chat UI](chat-ui.md) | Step-by-step walkthrough of the chat interface |
| [Understanding Results](understanding-results.md) | How to read findings, severity levels, and recommendations |
| [Starter Scenarios](scenarios.md) | 6 ready-to-use configurations for common workloads |
| [Automation & Scripting](automation.md) | Integrate the advisor into your pipelines |

---

!!! tip "New to Azure AI Search?"
    If you're not sure what SKU or replica count you need, start with the [E-commerce Catalog](#) or [Internal Knowledge Base](#) scenario — they represent the most common starting points.
