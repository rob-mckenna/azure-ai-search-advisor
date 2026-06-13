# Using the Chat UI

This page walks you through the chat interface step by step.

## Overview

The Azure AI Search Advisor UI is a single-page chat application. You describe your search service (or use quick actions), and the advisor responds with analysis, recommendations, or cost simulations.

![Chat UI Layout](img/chat-ui-layout.png)

*Layout: header with mode/auth indicators, chat area with messages, and input bar at the bottom.*

## Interface elements

### Header bar

| Element | Purpose |
|---------|---------|
| **Mode chip** | Shows "Local API mode" or "Foundry mode" — indicates which backend is active |
| **Auth chip** | Shows authentication status (no auth, browser auth, or signed-in user) |
| **Sign in/out button** | Appears in Foundry mode with Static Web Apps auth |

### Chat area

The main conversation area shows:

- **Assistant messages** — analysis results, recommendations, and explanations
- **User messages** — your questions and requests
- **Loading indicator** — animated dots while the advisor processes your request

### Quick actions

![Quick Actions](img/quick-actions.png)

*Quick action buttons appear in Local API mode for common operations.*

In Local API mode, three quick action buttons appear:

| Button | What it does |
|--------|--------------|
| **Analyze sample service** | Sends a pre-built service configuration for analysis |
| **Get recommendations** | Generates optimization recommendations from the sample |
| **Cost simulation** | Runs a what-if cost scenario on the sample service |

## Step-by-step: Your first analysis

### Step 1: Start the services

```bash
# Terminal 1 — API
python -m uvicorn azure_ai_search_advisor.main:app --reload

# Terminal 2 — UI
cd ui && npm run dev
```

### Step 2: Open the UI

Navigate to `http://localhost:5173`. You'll see the welcome message:

![Welcome Screen](img/welcome-screen.png)

*The advisor greets you and shows available quick actions.*

### Step 3: Run an analysis

**Option A — Quick action:** Click "Analyze sample service"

**Option B — Type a request:** Enter something like:
> Analyze my search service: Standard SKU, 3 replicas, 2 partitions, 1.2M documents, 40 QPS average

The advisor processes your request and returns findings:

![Analysis Results](img/analysis-results.png)

*Example analysis showing a medium-severity finding about replica over-provisioning.*

### Step 4: Get recommendations

After analysis, click "Get recommendations" or type:
> What should I do to reduce costs?

The advisor returns prioritized recommendations:

![Recommendations](img/recommendations.png)

*Recommendations include estimated savings, effort level, and step-by-step remediation.*

### Step 5: Simulate a change

Before implementing a recommendation, simulate it:
> What if I reduce to 2 replicas?

The simulation shows projected cost changes:

![Cost Simulation](img/cost-simulation.png)

*Simulation comparing current cost vs. projected cost after the change.*

## Conversation tips

| What to say | What happens |
|-------------|--------------|
| "Analyze my service with 4 replicas and Standard S2 SKU" | Runs provisioning + SKU + feature analysis |
| "Is my service over-provisioned?" | Focuses on capacity utilization |
| "How much would I save dropping to Basic?" | Runs a SKU downgrade simulation |
| "What alerts should I set up?" | Returns Azure Monitor alert recommendations |
| "Show my analysis history" | Displays past analysis results and trends |

## Switching modes

### Local API mode (development)

Best for: testing, development, offline use

```env
VITE_MODE=local
VITE_API_URL=http://127.0.0.1:8000
```

Features: Quick actions, full API access, no auth required.

### Foundry mode (production)

Best for: deployed environments, conversational AI experience

```env
VITE_MODE=foundry
VITE_FOUNDRY_ENDPOINT=https://your-project.services.ai.azure.com
VITE_AZURE_CLIENT_ID=<your-app-registration>
```

Features: Natural language understanding, Azure identity, multi-turn conversations.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Something went wrong while contacting the advisor" | Check that the API is running on port 8000 |
| No quick action buttons | Verify `VITE_MODE=local` in `ui/.env` |
| "Unable to load Azure Static Web Apps session" | Expected in local dev — switch to local mode |
| Responses are slow | First request warms up models; subsequent requests are faster |

---

**Next:** [Understanding Results →](understanding-results.md)
