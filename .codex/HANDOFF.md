# Context Handoff

## Current Project Status

Closed specs:

- SPEC-001 Bootstrap Backend - Approved / Closed
- SPEC-002 Database Foundation - Approved / Closed
- SPEC-003 Authentication and RBAC - Approved / Closed
- SPEC-004 Storage Infrastructure - Approved / Closed
- SPEC-005 Workflow State - Approved / Closed
- SPEC-006 LangGraph Runtime - Approved / Closed
- SPEC-007 Workflow API Endpoints - Approved / Closed

Current active spec:

- SPEC-008 Event Streaming - planning prepared, awaiting review

## Current SPEC-008 Planning State

Planning files:

- `.ai/specs/SPEC-008-event-streaming/spec.md`
- `.ai/specs/SPEC-008-event-streaming/tasks.md`

Planned tasks:

- `TASK 008.1 - Event Stream Schemas and Publisher Contracts`
- `TASK 008.2 - Redis Pub/Sub Event Publisher`
- `TASK 008.3 - WorkflowEvent Publish Integration`
- `TASK 008.4 - WebSocket Stream Endpoint`
- `TASK 008.5 - Stream Auth/RBAC and Recovery Tests`
- `TASK 008.6 - Event Streaming Hardening and SPEC-008 Final Review`

Overall SPEC-008 scope:

- `WorkflowEvent` remains the source of truth.
- RuntimeService continues appending persisted events through
  `WorkflowEventService`.
- The streaming layer delivers workflow events to clients in near real time.
- Transport decision: implement WebSocket endpoint
  `WS /api/v1/workflows/{workflow_id}/stream`.
- Redis pub/sub is the near-real-time notification mechanism because SPEC-004
  already provides Redis infrastructure.
- On WebSocket connect, the stream can deliver recent/backlog persisted events
  through `WorkflowEventService`, then forward newly published events.
- Stream auth/RBAC matches SPEC-007 workflow event read behavior:
  Admin, Manager, Sales, Legal, Finance, and Viewer.
- Stream messages must be typed, JSON-compatible, bounded, and sanitized.

Explicit SPEC-008 deferrals:

- Server-sent events.
- Frontend live UI.
- Real LLM token streaming.
- Agent thought streaming or hidden reasoning exposure.
- Multi-workflow dashboard fanout.
- Cross-tenant event bus.
- Durable replay cursor beyond basic event id or created timestamp recovery.
- Production horizontal scaling beyond Redis pub/sub.
- Advanced notification delivery.
- `/resume` and human approval continuation.
- RAG, document indexing, real Agents, and procurement policy engine.
- New migrations or database model changes.

## Next Task

- Review SPEC-008 planning files.
- Then implement `TASK 008.1 - Event Stream Schemas and Publisher Contracts`
  only after planning is approved.

## Expected SPEC-008 Quality Gate

- `git status --short`
- `docker-compose config`
- `docker-compose up -d postgres redis`
- `docker-compose run --rm backend-test alembic upgrade head`
- `docker-compose build backend-test`
- `docker-compose run --rm backend-test pytest`
- `docker-compose run --rm backend-test ruff check .`
- `docker-compose run --rm backend-test black --check .`
- `docker-compose run --rm backend-test mypy app`
- `git diff --check`

## Important Constraints For SPEC-008

- Use existing SPEC-005 `WorkflowEventService` and persisted `WorkflowEvent`
  records as source of truth.
- Use existing SPEC-007 workflow router/auth/RBAC patterns for stream access.
- Use existing SPEC-004 Redis settings and infrastructure for pub/sub.
- Do not replace database event persistence with pub/sub.
- Do not mutate workflow state/status from the streaming layer.
- Do not implement `/resume`, SSE, frontend live UI, real LLM token streaming,
  Agent thought streaming, RAG, document indexing, migrations, or model changes.

## Known Warnings

- Existing FastAPI/TestClient StarletteDeprecationWarning is non-blocking.
- LF/CRLF warnings from `git diff --check` are non-blocking when no whitespace
  errors are reported.

## Harness State

- SPEC-005 final review recorded and approved.
- SPEC-007 final review recorded and approved.
- SPEC-006 planning recorded.
- TASK 006.1 implementation recorded and approved.
- TASK 006.2 implementation recorded and approved.
- TASK 006.3 implementation recorded and approved.
- TASK 006.4 implementation recorded and approved.
- TASK 006.5 implementation recorded with Harness intake #54 and trace #63.
- TASK 006.6 implementation recorded with Harness intake #55 and trace #64.
- TASK 006.7 final review recorded with Harness intake #56 and trace #65.
- SPEC-008 planning recorded with Harness intake #57.
