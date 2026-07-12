# SPEC-008 - Event Streaming

## Status

Draft

## Context

Enterprise Multi-Agent OS now has the Phase 2 workflow foundation needed for
near real-time progress delivery:

- SPEC-005 provides durable `WorkflowEvent` append/read behavior.
- SPEC-006 runtime execution appends persisted runtime and node events through
  `WorkflowEventService`.
- SPEC-007 exposes workflow REST APIs and read access to persisted workflow
  events.

SPEC-008 adds an event delivery layer for clients that need workflow progress
updates while a workflow is running. Persisted `WorkflowEvent` records remain
the source of truth. Streaming is a delivery mechanism only; it must not replace
database event persistence, audit behavior, workflow lifecycle rules, or runtime
service orchestration.

## Goals

- Add a bounded event streaming architecture for workflow runtime events.
- Implement the current API contract target:

```text
WS /api/v1/workflows/{workflow_id}/stream
```

- Stream events for one workflow to authenticated, authorized clients.
- Use persisted workflow events for initial backlog/recovery on connection.
- Use Redis pub/sub for near real-time notification delivery after event
  persistence.
- Keep stream messages typed, JSON-compatible, bounded, and safe.
- Reuse existing workflow auth/RBAC read behavior.
- Keep the streaming layer generic and product-ready, not procurement-specific.

## Non-goals

- Server-sent events implementation.
- Frontend live UI.
- Real LLM token streaming.
- Agent thought streaming or hidden reasoning exposure.
- Multi-workflow dashboard fanout.
- Cross-tenant event bus design.
- Durable replay cursor beyond basic event id or created timestamp recovery.
- Production horizontal scaling beyond Redis pub/sub.
- Advanced notification delivery.
- Starting, running, resuming, approving, or cancelling workflows from the
  stream endpoint.
- `/resume` or human approval continuation.
- RAG, document indexing, real Agents, or procurement policy engines.
- New database tables, migrations, or model changes.

## Transport Decision

SPEC-008 uses WebSocket for the MVP because `.ai/project/API_CONTRACT.md`
already declares:

```text
WS /api/v1/workflows/{workflow_id}/stream
```

SSE remains a future alternative if browser-only operational needs make it
preferable later. SPEC-008 must not implement both transports. Keeping one
transport keeps auth, recovery, tests, and deployment behavior bounded.

## Event Delivery Architecture

The event delivery model is:

```text
RuntimeService
  -> WorkflowEventService.append_event()
      -> persist WorkflowEvent
      -> flush caller-owned transaction
      -> publish safe notification after persistence boundary
  -> WebSocket stream endpoint
      -> send backlog from WorkflowEventService
      -> subscribe for new notifications
      -> send typed stream messages
```

Important rules:

- `WorkflowEvent` remains the source of truth.
- RuntimeService continues appending events through `WorkflowEventService`.
- The streaming layer must not mutate workflow status or state.
- The streaming layer must not replace audit or event persistence.
- Persistence must happen before publish, or publish must never be the only
  source of truth.
- Reconnection should recover missed events from persisted records where
  practical.
- Transactions remain caller-owned; publishing must not force API or runtime
  commit behavior changes.

## Publish And Subscribe Layer

SPEC-008 should use Redis pub/sub because SPEC-004 already introduced Redis and
`REDIS_URL` settings. The implementation should add a small event streaming
publisher abstraction rather than coupling WebSocket routes directly to Redis
client details.

Suggested modules:

```text
app/events/
  schemas.py
  publisher.py
  redis.py
```

Responsibilities:

- Define a typed publisher protocol.
- Define stream message schemas.
- Publish a notification for a persisted workflow event.
- Subscribe to a workflow-specific channel.
- Wrap Redis failures in typed streaming exceptions.
- Keep channel names deterministic and scoped by workflow id.

The notification payload should be enough for a stream server to deliver a
typed event message, but the persisted event remains authoritative. If a
notification is lost, a reconnect can use `WorkflowEventService` backlog reads.

## Stream Endpoint Scope

Planned endpoint:

```text
WS /api/v1/workflows/{workflow_id}/stream
```

Behavior:

- Require authentication.
- Require workflow read/events role access.
- Verify the workflow exists before accepting or immediately after accepting
  with a safe close code according to FastAPI/WebSocket constraints.
- Send recent/backlog persisted events for the workflow using
  `WorkflowEventService`.
- Subscribe to newly published events for the same workflow.
- Send typed JSON messages to the client.
- Keep messages bounded and safe.
- Close cleanly on client disconnect.
- Do not run workflows.
- Do not append workflow events from the stream endpoint by default.
- Do not implement event append API behavior.

Optional query parameters may be included if kept small:

```text
limit       backlog event count, bounded
after_id    optional basic recovery cursor if practical
```

Complex filters, cursor pagination, and multi-workflow fanout are deferred.

## Auth And RBAC

The stream endpoint must require authentication and use the same baseline read
policy as SPEC-007 workflow events:

| Role | Stream access |
| --- | --- |
| Admin | Allowed |
| Manager | Allowed |
| Sales | Allowed |
| Legal | Allowed |
| Finance | Allowed |
| Viewer | Allowed |

Unauthenticated connections must be rejected. Authenticated users without a
recognized required role must be rejected. SPEC-008 must not invent new roles
or encode procurement-specific authorization policy.

## Stream Message Schema

SPEC-008 should define direct Pydantic stream message models. A global response
envelope is not introduced for WebSocket messages in this spec.

Suggested message shape:

```json
{
  "type": "workflow.event",
  "workflow_id": "uuid",
  "event_id": "uuid",
  "event_type": "workflow.node.completed",
  "status": "COMPLETED",
  "stage": "planner",
  "message": "Runtime stage planner completed.",
  "created_at": "datetime",
  "payload": {
    "stage": "planner",
    "workflow_status": "PLANNING"
  }
}
```

Message requirements:

- JSON-compatible.
- Pydantic v2.
- No ORM objects.
- No secrets, hidden reasoning, raw provider payloads, or large request dumps.
- Payloads should be bounded and sanitized at the schema/helper boundary.
- Include `workflow_id`, `event_id`, event name/type, status when available,
  stage/agent when available, `created_at`, message, and sanitized payload.

Optional control messages may be defined if useful:

- `workflow.stream.connected`
- `workflow.stream.backlog_complete`
- `workflow.stream.keepalive`
- `workflow.stream.error`

Control messages must not expose sensitive details.

## Runtime Integration

RuntimeService already emits persisted events through `WorkflowEventService`.
SPEC-008 should add publish behavior at the event append boundary where
practical:

- Prefer integrating publisher calls into `WorkflowEventService.append_event`
  through dependency injection or an optional publisher.
- Keep existing runtime business logic unchanged unless minimal constructor
  wiring is required.
- Do not add runtime stages.
- Do not change lifecycle rules.
- Do not mutate workflow status or state from the publisher.
- Do not publish before the event is persisted/flushed.

If implementation finds that publishing before database commit can expose
rolled-back events, the task should document the caveat and either publish only
after route/runtime success where practical or keep backlog recovery as the
source of truth. The implementation must not weaken caller-owned transaction
boundaries without a later explicit decision.

## Error Handling

Expected behaviors:

- Missing workflow returns a safe WebSocket rejection/close behavior covered by
  tests.
- Auth failures reject connection without exposing token details.
- RBAC failures reject connection without exposing internal role data.
- Redis publish/subscribe failures are wrapped in typed stream errors.
- Client disconnects are handled without leaking tasks or Redis subscriptions.
- Unexpected exceptions are not swallowed silently and must not leak secrets to
  clients.

## User Stories

### US-018 - View Workflow Progress Stream

As a workflow reader, I want to subscribe to one workflow's event stream so that
I can see runtime progress without polling.

### US-019 - View Agent Errors Stream

As an Admin, I want failure events to arrive through the workflow stream so that
runtime errors can be surfaced quickly.

### US-023 - Preserve Event Auditability

As an Admin, I want streamed events to match persisted workflow events so that
real-time delivery stays auditable and replayable.

## Acceptance Criteria

```gherkin
Given a workflow has persisted events
When an authorized user opens the workflow stream
Then the stream sends recent persisted events for that workflow
```

```gherkin
Given RuntimeService appends a workflow event
When the event is persisted
Then a workflow-scoped stream notification is published where practical
```

```gherkin
Given an authorized user is connected to a workflow stream
When a new event is published for that workflow
Then the user receives a typed JSON stream message
```

```gherkin
Given an unauthenticated client
When it attempts to connect to the workflow stream
Then the connection is rejected
```

```gherkin
Given an authenticated user without a required role
When it attempts to connect to the workflow stream
Then the connection is rejected
```

```gherkin
Given a client reconnects after missing messages
When it requests backlog events within the supported basic recovery behavior
Then missed persisted events can be delivered from `WorkflowEventService`
```

## Validation Strategy

SPEC-008 implementation tasks should use the Docker backend quality gate:

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

Focused tests should cover:

- stream message schema validation and sanitization
- publisher protocol/import behavior
- Redis publisher publish/subscribe behavior against Compose Redis where
  practical
- persisted event append triggering publish behavior
- stream endpoint connection success
- backlog delivery
- new event delivery
- client disconnect cleanup
- authentication and RBAC rejection behavior
- missing workflow behavior
- absence of SSE, event append API, `/resume`, frontend, LLM token streaming,
  Agents, RAG, migrations, and model changes

## Out-of-scope List

- Server-sent events.
- Frontend live UI.
- Real LLM token streaming.
- Agent thought streaming.
- Multi-workflow dashboard fanout.
- Cross-tenant event bus.
- Durable replay cursor beyond basic event id or created timestamp recovery.
- Production horizontal scaling beyond Redis pub/sub.
- Advanced notification delivery.
- `/resume` and human approval continuation.
- Workflow run/start behavior from the stream.
- Event append API endpoint.
- RAG or document indexing.
- Real procurement policy engine.
- Real Agent implementations.
- Email sending.
- New migrations or database model changes.
