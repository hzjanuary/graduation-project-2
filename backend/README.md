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

## Health Endpoints

The backend exposes lightweight service endpoints:

```text
GET /       service metadata and endpoint links
GET /health overall application health
GET /ready  readiness with lightweight placeholder checks
GET /live   liveness status
```

Readiness does not perform database, Redis, Qdrant, or MinIO checks yet. Those
clients are introduced by later SPEC-001 tasks.

## Settings

Application settings live in `app/config/settings.py` and are loaded with
Pydantic v2 through `pydantic-settings`.

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Supported environments are:

```text
development
testing
production
```

Settings can be overridden with environment variables such as:

```bash
APP_ENV=testing
DEBUG=false
LOG_LEVEL=DEBUG
```

Do not commit real API keys, database credentials, or object storage secrets.

## Docker

Build and run the backend plus Phase 1 infrastructure services from the
repository root:

```bash
docker compose config
docker compose up --build backend
```

The Compose stack includes:

```text
backend   FastAPI API on http://localhost:8000
postgres  PostgreSQL on localhost:5432
redis     Redis on localhost:6379
qdrant    Qdrant on http://localhost:6333
minio     MinIO API on http://localhost:9000 and console on http://localhost:9001
```

After the backend starts, verify:

```bash
curl http://localhost:8000/health
```

The Docker Compose file uses development defaults only. Do not reuse demo
passwords or API keys for production deployments.

## Logging And Middleware

`app/main.py` wires the core middleware foundation:

- `RequestIdMiddleware` attaches a request ID to every request.
- If `X-Request-ID` is provided, the same value is reused.
- If `X-Request-ID` is missing, a UUID request ID is generated.
- Every response includes `X-Request-ID`.
- `RequestLoggingMiddleware` emits JSON-compatible request logs with
  `request_id`, `method`, `path`, `status_code`, and `duration_ms`.
- CORS origins are loaded from `BACKEND_CORS_ORIGINS`.
- GZip response compression is enabled.
- The global exception handler returns the standard JSON error envelope.

## Test And Check

```bash
poetry run pytest
poetry run ruff check .
poetry run black --check .
poetry run mypy app
```
