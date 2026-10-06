# Petstore Workshop Backend

FastAPI starter project for the workshop backend.

## Requirements

- Python 3.12+
- `uv` (recommended) or `pip`

## Quick start

### With uv

```bash
uv venv
source .venv/bin/activate
uv sync --all-groups
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### With pip

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
pip install -e ."[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## Common commands

```bash
make test
make lint
make format
make typecheck
```

## Project layout

- `app/main.py`: FastAPI app entrypoint.
- `app/api/routes/`: API route modules.
- `app/core/config.py`: environment-backed settings.
- `lambdas/login/handler.py`: login Lambda entrypoint scaffold.
- `lambdas/authorizer/handler.py`: HTTP API authorizer entrypoint scaffold.
- `tests/`: test suite.
- `docs/workshop.md`: copied workshop brief.

## Lambda development

The Lambda entrypoints are intentionally unimplemented for the workshop. Implement each handler
in its function directory; the execution roles provide AWS permissions at runtime.

Build deployment archives from the repository root:

```bash
make package-login
make package-authorizer
```

The archives are written to `dist/`. Each archive contains `handler.py` at its root; configure the
Lambda handler as `handler.handler`.
