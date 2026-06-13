# Contributing

Thanks for contributing to Azure AI Search Advisor.

## Local contributor setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp .env.example .env
python -m uvicorn azure_ai_search_advisor.main:app --reload
```

If you are working on the UI too:

```bash
cd ui
cp .env.example .env
npm install
npm run dev
```

## Development expectations

- Keep route handlers thin and push logic into domain services.
- Keep Azure-specific integrations inside `src/azure_ai_search_advisor/integrations/` or dedicated ingestion adapters.
- Prefer explicit Pydantic contracts over unstructured dictionaries.
- Preserve the current scaffold-friendly package boundaries unless there is a strong reason to change them.
- Update docs when setup, runtime behavior, or architecture changes.

## Verification

### Quick Python verification

```bash
python3 -m compileall src
```

### CI checks already used by the repository

The GitHub Actions workflow in `.github/workflows/ci.yml` runs:

- `ruff check src/ tests/`
- `mypy src/ --ignore-missing-imports || true`
- `pytest tests/ --cov=src/azure_ai_search_advisor --cov-report=xml -q`
- `docker build -t azure-ai-search-advisor:ci .`
- container startup verification with `curl http://localhost:8000/health`

## Pull request guidance

- Keep changes focused.
- Include documentation updates for user-visible or operator-visible changes.
- Add tests when implementing concrete new behavior.
- Prefer small, reviewable increments over broad refactors.
