# SPEC-008 Tasks - Event Streaming

## TASK 008.1 - Event Stream Schemas and Publisher Contracts

### Objective

Define typed event stream message schemas and implementation-agnostic publisher
contracts for workflow event delivery.

### Scope

- Add event streaming package/module structure if useful.
- Define Pydantic v2 stream message schemas.
- Define publisher/subscriber protocol or abstract base class.
- Define channel naming helpers for workflow-scoped streams.
- Define stream exceptions if useful.
- Add tests for schema validation, payload bounds, and protocol imports.

### Deliverables

- `backend/app/events/__init__.py`
- `backend/app/events/schemas.py`
- `backend/app/events/publisher.py`
- `backend/app/events/exceptions.py` if useful
- `backend/app/tests/test_event_stream_schemas.py`
- README notes if useful.

### Acceptance Criteria

- Stream schemas can be imported.
- Stream messages validate workflow id, event id, event type, status, stage,
  timestamp, message, and sanitized payload fields.
- Schemas reject invalid message types or invalid bounded fields where
  practical.
- Publisher contract can be imported.
- Channel naming is deterministic and workflow-scoped.
- No Redis implementation, WebSocket route, runtime behavior change, SSE,
  frontend, migrations, or model changes are implemented.

### Out-of-scope

- Redis pub/sub implementation.
- Workflow event publish integration.
- WebSocket endpoint.
- Event append API.
- `/resume`.
- Frontend.
- Real LLM/Agent/RAG streaming.

### Validation Commands

```bash
git status --short
docker-compose config
docker-compose build backend-test
docker-compose run --rm backend-test pytest
docker-compose run --rm backend-test ruff check .
docker-compose run --rm backend-test black --check .
docker-compose run --rm backend-test mypy app
git diff --check
```

## TASK 008.2 - Redis Pub/Sub Event Publisher

### Objective

Implement the Redis-backed event publisher/subscriber using existing Redis
settings.

### Scope

- Add Redis event publisher implementation.
- Use existing `REDIS_URL` settings.
- Support publishing stream messages to workflow-scoped channels.
- Support subscribing/listening to workflow-scoped channels.
- Add close/cleanup behavior.
- Wrap Redis failures in stream exceptions.
- Add tests for publish/subscribe behavior against Compose Redis where
  practical.

### Deliverables

- `backend/app/events/redis.py`
- `backend/app/core/dependencies.py` updated only if provider wiring belongs
  there
- `backend/app/tests/test_redis_event_publisher.py`
- README notes if useful.

### Acceptance Criteria

- Redis event publisher can be imported.
- Publisher uses `REDIS_URL` from settings.
- Published messages are JSON-compatible and workflow-scoped.
- Subscriber receives messages for the expected workflow channel.
- Redis resources are closed cleanly.
- Redis failures are wrapped consistently.
- No WebSocket route, event append integration, SSE, frontend, migrations, or
  model changes are implemented.

### Out-of-scope

- WebSocket endpoint.
- WorkflowEventService integration.
- Multi-workflow fanout.
- Durable queue semantics.
- Production retry scheduler.
- Real LLM/Agent/RAG streaming.

### Validation Commands

```bash
git status --short
docker-compose config
docker-compose up -d redis
docker-compose build backend-test
docker-compose run --rm backend-test pytest
docker-compose run --rm backend-test ruff check .
docker-compose run --rm backend-test black --check .
docker-compose run --rm backend-test mypy app
git diff --check
```

## TASK 008.3 - WorkflowEvent Publish Integration

### Objective

Publish workflow event notifications after persisted workflow event append
behavior.

### Scope

- Integrate optional event publisher wiring into `WorkflowEventService` or an
  adjacent helper.
- Preserve `WorkflowEvent` as the source of truth.
- Ensure persistence/flush happens before publish where practical.
- Keep transactions caller-owned and do not introduce commits inside services.
- Convert `WorkflowEventRead` into stream message payloads.
- Add tests for append-event publish behavior, no-publisher behavior, publish
  failure behavior, and transaction boundary behavior.

### Deliverables

- `backend/app/workflows/events.py` updated only for bounded publish integration
- `backend/app/events/schemas.py` updated if message conversion belongs there
- `backend/app/core/dependencies.py` updated if dependency wiring belongs there
- `backend/app/tests/test_workflow_event_publish_integration.py`
- README notes if useful.

### Acceptance Criteria

- Appending a workflow event still persists and returns `WorkflowEventRead`.
- Publish is triggered only after the persisted event exists and has been
  flushed where practical.
- Publish payloads are bounded and sanitized.
- Service does not call `commit()`.
- Existing runtime and workflow event tests continue to pass.
- Publish failure behavior is explicit and test-covered without silently
  replacing persistence.
- No WebSocket endpoint, SSE, frontend, migrations, model changes, new runtime
  stages, or lifecycle rule changes are implemented.

### Out-of-scope

- WebSocket stream route.
- Event append API endpoint.
- Workflow runtime business logic changes beyond dependency wiring.
- `/resume`.
- Frontend.
- Real LLM/Agent/RAG streaming.

### Validation Commands

```bash
git status --short
docker-compose config
docker-compose up -d postgres redis
docker-compose run --rm backend-test alembic upgrade head
docker-compose build backend-test
docker-compose run --rm backend-test pytest
docker-compose run --rm backend-test ruff check .
docker-compose run --rm backend-test black --check .
docker-compose run --rm backend-test mypy app
git diff --check
```

## TASK 008.4 - WebSocket Stream Endpoint

### Objective

Expose `WS /api/v1/workflows/{workflow_id}/stream` for workflow event delivery.

### Scope

- Add WebSocket route under the existing workflow API router.
- Authenticate WebSocket connections using existing auth behavior adapted to
  WebSocket constraints.
- Apply workflow read/events RBAC.
- Verify workflow existence.
- Send recent persisted events on connect.
- Subscribe to Redis workflow event notifications and forward typed messages.
- Handle client disconnect and cleanup.
- Add WebSocket API tests for success, backlog delivery, new event delivery,
  missing workflow, and disconnect behavior.

### Deliverables

- `backend/app/api/v1/workflows.py` updated with stream route
- `backend/app/core/dependencies.py` updated only if stream dependencies belong
  there
- `backend/app/tests/test_workflow_event_stream_api.py`
- README notes if useful.

### Acceptance Criteria

- `WS /api/v1/workflows/{workflow_id}/stream` exists.
- Authorized workflow readers can connect.
- On connect, recent persisted workflow events are sent.
- Newly published workflow events are delivered to connected clients.
- Missing workflows are rejected or closed safely.
- Disconnect closes Redis subscription resources.
- Stream route does not start, run, resume, approve, or mutate workflows.
- No SSE endpoint, event append API, frontend, migrations, or model changes are
  implemented.

### Out-of-scope

- Server-sent events.
- Event append endpoint.
- `/resume`.
- Workflow runtime execution changes.
- Frontend live UI.
- Real LLM token streaming or Agent thought streaming.
- Multi-workflow dashboard fanout.

### Validation Commands

```bash
git status --short
docker-compose config
docker-compose up -d postgres redis
docker-compose run --rm backend-test alembic upgrade head
docker-compose build backend-test
docker-compose run --rm backend-test pytest
docker-compose run --rm backend-test ruff check .
docker-compose run --rm backend-test black --check .
docker-compose run --rm backend-test mypy app
git diff --check
```

## TASK 008.5 - Stream Auth/RBAC and Recovery Tests

### Objective

Harden stream authentication, authorization, recovery, and regression coverage.

### Scope

- Add or strengthen tests for unauthenticated WebSocket rejection.
- Add or strengthen tests for all allowed workflow read roles.
- Add or strengthen tests for authenticated users without required role.
- Add or strengthen tests for backlog/recovery behavior using persisted events.
- Add or strengthen tests that messages do not expose ORM internals, secrets,
  raw provider payloads, hidden reasoning, or unbounded request payloads.
- Add or strengthen tests for absence of SSE, `/resume`, event append API, and
  frontend/runtime side effects.
- Fix small SPEC-008 bugs found by tests.

### Deliverables

- `backend/app/tests/test_workflow_event_stream_auth.py` or updates to stream
  API tests
- `backend/app/tests/test_workflow_event_stream_recovery.py` if useful
- Small bug fixes limited to SPEC-008
- README cleanup if useful.

### Acceptance Criteria

- Admin, Manager, Sales, Legal, Finance, and Viewer can connect.
- Unauthenticated clients are rejected.
- Authenticated users without a required role are rejected.
- Backlog/recovery behavior uses persisted events.
- Stream messages remain schema-safe and bounded.
- Deferred endpoints/features remain absent.
- Quality gate passes.

### Out-of-scope

- New stream transports.
- Multi-workflow fanout.
- Production replay cursor storage.
- Frontend.
- Real LLM/Agent/RAG streaming.
- Migrations or model changes.

### Validation Commands

```bash
git status --short
docker-compose config
docker-compose up -d postgres redis
docker-compose run --rm backend-test alembic upgrade head
docker-compose build backend-test
docker-compose run --rm backend-test pytest
docker-compose run --rm backend-test ruff check .
docker-compose run --rm backend-test black --check .
docker-compose run --rm backend-test mypy app
git diff --check
```

## TASK 008.6 - Event Streaming Hardening and SPEC-008 Final Review

### Objective

Verify SPEC-008 is complete, bounded, tested, and ready to close.

### Scope

- Review stream schemas, publisher contracts, Redis pub/sub implementation,
  workflow event publish integration, WebSocket route, auth/RBAC behavior,
  recovery behavior, tests, docs, and out-of-scope boundaries.
- Confirm validation proof.
- Confirm no conflicting changes to SPEC-005, SPEC-006, or SPEC-007 behavior.
- Confirm no migrations or model changes were introduced.
- Record Harness evidence.

### Deliverables

- SPEC-008 final review result.
- Harness durable story/trace evidence when available.
- Recommendation for the next SPEC.

### Acceptance Criteria

- `WorkflowEvent` remains the source of truth.
- WebSocket stream endpoint delivers persisted backlog events and new
  workflow-scoped notifications.
- Redis pub/sub publisher works with existing settings.
- Stream auth/RBAC matches SPEC-007 workflow event read behavior.
- Stream messages are typed, bounded, and safe.
- No SSE, frontend, `/resume`, event append API, real LLM/Agent/RAG streaming,
  migrations, or model changes are added.
- Quality gate passes.

### Out-of-scope

- Application code changes during final review except small blocking fixes if
  explicitly approved by the task prompt.
- Server-sent events.
- Frontend live UI.
- Real LLM/Agent/RAG streaming.
- Multi-workflow dashboard fanout.
- `/resume` or approval continuation.
- Migrations or model changes.

### Validation Commands

```bash
git status --short
docker-compose config
docker-compose up -d postgres redis
docker-compose run --rm backend-test alembic upgrade head
docker-compose build backend-test
docker-compose run --rm backend-test pytest
docker-compose run --rm backend-test ruff check .
docker-compose run --rm backend-test black --check .
docker-compose run --rm backend-test mypy app
git diff --check
```
