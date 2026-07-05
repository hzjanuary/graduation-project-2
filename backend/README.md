# Enterprise Multi-Agent OS Backend

FastAPI backend foundation for Enterprise Multi-Agent OS.

This skeleton belongs to `SPEC-001` / `TASK 001.1` and intentionally contains
only the base project structure. Database models, authentication, workflow
runtime, agents, storage clients, health endpoints, and Docker setup are
implemented by later tasks.

## Requirements

- Python 3.12
- Poetry

## Install

```bash
poetry install
```

## Run Locally

```bash
poetry run uvicorn app.main:app --reload
```

The OpenAPI documentation will be available at:

```text
http://127.0.0.1:8000/docs
```

## Test And Check

```bash
poetry run pytest
poetry run ruff check .
poetry run black --check .
poetry run mypy app
```
