# UI Prototype

This folder contains a Vite + React + TypeScript prototype for the Azure AI Search Advisor chat experience.

## What is included

- React chat UI with message list, composer, loading state, and findings sidebar
- Local browser authentication with `InteractiveBrowserCredential`
- Azure Static Web Apps auth hooks for deployed usage via `/.auth/`
- Foundry chat client scaffold that posts to `{endpoint}/agents/advisor-agent/chat/completions`
- `staticwebapp.config.json` and a GitHub Actions deployment workflow scaffold

## Local development

1. Copy the example environment file:
   ```bash
   cp ui/.env.example ui/.env
   ```
2. Set `VITE_FOUNDRY_ENDPOINT` to your Microsoft Foundry project endpoint.
3. Set `VITE_AZURE_CLIENT_ID` to the app registration used by `InteractiveBrowserCredential`.
4. Install dependencies and start the Vite dev server:
   ```bash
   cd ui
   npm install
   npm run dev
   ```
5. Open the printed local URL (typically `http://localhost:5173`).

The local client acquires a bearer token for `https://ai.azure.com/.default` and sends chat requests directly to the Foundry agent endpoint.

## Expected Foundry endpoint

The client assumes the advisor agent is exposed at:

```text
{VITE_FOUNDRY_ENDPOINT}/agents/advisor-agent/chat/completions
```

If your agent name differs, update `DEFAULT_AGENT_NAME` in `src/services/foundryClient.ts`.

## Azure Static Web Apps deployment

This scaffold supports Azure Static Web Apps sign-in and protects `/api/foundry/*` routes via `staticwebapp.config.json`.

Recommended production setup:

1. Deploy the Vite app from `ui/`.
2. Configure Azure AD as the Static Web Apps identity provider.
3. Point the production `VITE_FOUNDRY_ENDPOINT` build variable at a same-origin proxy such as `/api/foundry`.
4. Back that route with a linked API, reverse proxy, or managed-identity-enabled backend that forwards authenticated requests to Microsoft Foundry.
5. Add the required GitHub secrets/variables used by `.github/workflows/deploy-ui.yml`.

Because Static Web Apps auth establishes the user session at `/.auth/`, the prototype checks `/.auth/me` before sending production requests and expects the same-origin `/api/foundry` route to enforce auth and reach Foundry.

## Deploy workflow variables

- `secrets.AZURE_STATIC_WEB_APPS_API_TOKEN` — deployment token for the Static Web App
- `vars.VITE_FOUNDRY_ENDPOINT` — production endpoint or proxy path (for example `/api/foundry`)
- `vars.VITE_AZURE_CLIENT_ID` — Azure AD client ID exposed at build time
