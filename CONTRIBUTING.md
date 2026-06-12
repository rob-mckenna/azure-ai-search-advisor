# Contributing

Thanks for contributing to Azure AI Search Advisor.

## Getting started

1. Create a virtual environment and install the project:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -e .
   ```
2. If `python3 -m venv` is unavailable on Debian/Ubuntu, install the `python3-venv` package first.
3. Copy `.env.example` to `.env` if you plan to wire in Azure-backed integrations.
4. Run the API locally:
   ```bash
   python -m uvicorn azure_ai_search_advisor.main:app --reload
   ```

## Before you open a pull request

- Keep changes focused and small.
- Update documentation when behavior, setup, or structure changes.
- Run the available verification step:
  ```bash
  python3 -m compileall src
  ```
- Add tests under `tests/` when implementing real behavior.

## Development expectations

- Keep route handlers thin and business logic in domain services.
- Isolate Azure-specific code in `src/azure_ai_search_advisor/integrations/`.
- Prefer explicit Pydantic models over unstructured dictionaries as contracts become concrete.
- Preserve the scaffold-friendly structure unless there is a strong architectural reason to change it.
