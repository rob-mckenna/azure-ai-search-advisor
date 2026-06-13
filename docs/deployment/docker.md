# Local Docker Development

The repository includes a simple Docker path for running the API locally.

## What is included

`docker-compose.yml` currently defines one service:

- `api` built from the repository root
- port mapping `8000:8000`
- environment variables for `AZURE_AI_FOUNDRY_ENDPOINT`, `AZURE_AI_FOUNDRY_MODEL`, and `AUTH_ENABLED`

## Start the API

```bash
cp .env.example .env
docker compose up --build
```

## Verify the container

```bash
curl http://127.0.0.1:8000/health
```

## Override defaults

The compose file passes through these variables if present in your shell or `.env`:

```bash
AZURE_AI_FOUNDRY_ENDPOINT=https://your-project.services.ai.azure.com/
AZURE_AI_FOUNDRY_MODEL=gpt-4o
AUTH_ENABLED=false
```

## Run the UI alongside Docker

The compose file does **not** currently include the React UI. Run it separately if needed:

```bash
cd ui
cp .env.example .env
npm install
npm run dev
```

If you want the UI to call the local API instead of Foundry, add these lines to `ui/.env`:

```bash
VITE_MODE=local
VITE_API_URL=http://127.0.0.1:8000
```

## Rebuild tips

- Use `docker compose up --build` after Python dependency changes.
- Use `docker compose down` to stop the local container.
- The image uses the repository `Dockerfile`, so API-only container verification matches the CI container smoke test pattern.
