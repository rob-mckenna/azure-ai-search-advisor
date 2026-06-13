# UI Development

The `ui/` folder contains a Vite + React + TypeScript prototype for the Azure AI Search Advisor experience.

## What the UI can do

- send chat-style requests to Microsoft Foundry
- fall back to the local API for analyze, recommend, simulate, and health scenarios
- authenticate locally with `InteractiveBrowserCredential`
- integrate with Azure Static Web Apps auth in deployed environments

## Prerequisites

- Node.js 18+
- npm

## Install and run

```bash
cd ui
cp .env.example .env
npm install
npm run dev
```

The Vite dev server usually starts on `http://localhost:5173`.

## Environment variables

### Base example file

`ui/.env.example` includes:

```bash
VITE_MODE=foundry
VITE_FOUNDRY_ENDPOINT=https://your-project.services.ai.azure.com
VITE_AZURE_CLIENT_ID=00000000-0000-0000-0000-000000000000
```

### Supported variables

| Variable | Purpose |
| --- | --- |
| `VITE_MODE` | `foundry` for direct Foundry chat, `local` for local API workflows |
| `VITE_FOUNDRY_ENDPOINT` | Foundry endpoint or production proxy path |
| `VITE_AZURE_CLIENT_ID` | Azure AD app registration used by `InteractiveBrowserCredential` |
| `VITE_API_URL` | Local API base URL; when present, the UI switches to local mode |

## Local API mode

If you want the UI to call the FastAPI service instead of the Foundry agent endpoint, set:

```bash
VITE_MODE=local
VITE_API_URL=http://127.0.0.1:8000
VITE_FOUNDRY_ENDPOINT=https://your-project.services.ai.azure.com
VITE_AZURE_CLIENT_ID=<your-client-id>
```

The local UI path uses the sample payloads defined in `ui/src/services/apiClient.ts` for analyze, recommend, and simulate requests.

## Authentication modes

### Local development

`ui/src/services/auth.ts` uses `InteractiveBrowserCredential` and requests the scope:

```text
https://ai.azure.com/.default
```

### Static Web Apps

In deployed environments, the UI checks `/.auth/me` and sends users to `/.auth/login/aad` when required.

`ui/staticwebapp.config.json` protects:

- `/api/foundry/*`

and rewrites `/chat` to the SPA entry point.

## Build for production

```bash
cd ui
npm run build
```

This runs TypeScript type checking (`tsc --noEmit`) and then builds with Vite.

## Deploy to Azure Static Web Apps

The checked-in workflow `.github/workflows/deploy-ui.yml` deploys `ui/` and expects:

- `secrets.AZURE_STATIC_WEB_APPS_API_TOKEN`
- `vars.VITE_FOUNDRY_ENDPOINT`
- `vars.VITE_AZURE_CLIENT_ID`

Recommended production shape:

1. Deploy the app from `ui/`.
2. Configure Azure AD as the Static Web Apps identity provider.
3. Point `VITE_FOUNDRY_ENDPOINT` at a same-origin proxy such as `/api/foundry`.
4. Back that route with an authenticated proxy or linked API that forwards requests to Microsoft Foundry.
