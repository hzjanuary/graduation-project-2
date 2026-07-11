# SPEC-006 - LangGraph Runtime

## Status

Draft

## Context

Enterprise Multi-Agent OS is a state-driven workflow orchestration platform.
SPEC-005 completed the durable workflow state foundation: typed workflow state
schemas, lifecycle transition rules, workflow service behavior, event
append/read behavior, and service-level audit writes. SPEC-007 completed the
workflow REST API for creating, reading, transitioning, updating, and listing
workflow events.

SPEC-006 adds the first LangGraph-based workflow runtime on top of those
foundations. The runtime must orchestrate workflow state through existing
services instead of mutating database models directly. It should prove the
runtime architecture and lifecycle integration with deterministic placeholder
nodes before later specs add real Agents, LLM provider calls, retrieval, tools,
human approval UI, event streaming, and frontend behavior.

## Goals

- Add a LangGraph-based workflow graph for runtime orchestration.
- Define a runtime service layer that owns graph execution.
- Define a workflow state adapter between persisted `WorkflowState` and
  LangGraph runtime state.
- Reuse `WorkflowService` for persisted status transitions and state updates.
- Reuse `WorkflowEventService` for runtime event append/read behavior.
- Preserve existing service-level audit behavior by using `WorkflowService`
  rather than direct model writes.
- Add a first `/run` workflow API endpoint using existing auth/RBAC patterns.
- Keep runtime behavior generic and product-ready, not procurement-specific
  beyond deterministic MVP placeholder node names and sample output shapes.

## Non-goals

- Real LLM provider calls.
- Multi-provider LLM routing.
- Production-grade Agent implementations.
- RAG, embeddings, document indexing, hybrid search, or Retrieval Agent logic.
- WebSocket or server-sent event streaming.
- Frontend implementation.
- Human approval UI.
- Advanced approval/resume behavior.
- Procurement-specific policy engine.
- Async distributed worker queues or background job schedulers.
- Production-grade retry scheduler.
- New database tables, migrations, or model changes.
- Audit query APIs.

## Runtime Architecture

SPEC-006 should introduce a small runtime package under the backend workflow
area, such as `app/workflows/runtime/`, while preserving the existing backend
layering:

```text
API -> Runtime Service -> LangGraph graph/nodes -> WorkflowService/WorkflowEventService
```

The runtime architecture has these responsibilities:

- Graph builder: creates the deterministic LangGraph workflow graph.
- Runtime state adapter: converts persisted `WorkflowState` into a
  JSON-compatible LangGraph state dictionary and converts graph output back into
  typed `WorkflowState`.
- Runtime nodes: deterministic placeholder node functions for the MVP workflow
  stages.
- Runtime service: loads the workflow, validates runtime preconditions, invokes
  the graph, persists state/status through existing services, appends events,
  and exposes a small API-facing use case.
- API endpoint: parses HTTP input, enforces RBAC, calls runtime service, commits
  on success, and maps known workflow/runtime errors to existing API error
  conventions.

The runtime must not call repositories directly from API routes. It may use the
existing services directly because those services already own lifecycle, events,
and audit behavior.

## Initial Graph Scope

The first graph may use deterministic, no-LLM placeholder nodes. The goal is to
prove orchestration, persistence, lifecycle transitions, and events.

The graph should represent these planned workflow stages:

```text
planner
retrieval
quotation
compliance
validation
approval
email_preparation
```

The initial `/run` path should execute the pre-approval portion and stop safely
at `WAITING_APPROVAL`:

```text
CREATED
  -> PLANNING          planner node
  -> RETRIEVING        retrieval node
  -> CALCULATING       quotation node
  -> CHECKING_COMPLIANCE compliance node
  -> VALIDATING        validation node
  -> WAITING_APPROVAL  approval wait node
```

`email_preparation` should exist in the graph design as the future continuation
after approval, but SPEC-006 should not execute it through `/run` unless a later
task explicitly implements approved-state continuation safely. This keeps the
approval-before-customer-output rule intact.

Each placeholder node should write bounded, deterministic output into the
appropriate generic `WorkflowState` section, such as `planner`, `retrieval`,
`quotation`, `compliance`, `validation`, `approval`, `outputs`, `steps`, and
`current_step`. Placeholder outputs must not claim real retrieval, pricing,
compliance, or email quality.

## Runtime API Scope

SPEC-006 includes:

```text
POST /api/v1/workflows/{workflow_id}/run
```

The run endpoint should:

- require authentication
- allow Admin and Manager initially
- use existing workflow API router conventions
- use existing `WorkflowService`, `WorkflowEventService`, and new runtime
  service dependencies
- return `WorkflowResponse` or a small direct Pydantic runtime response that
  includes the updated workflow state
- commit only after successful runtime service execution
- not expose ORM objects directly

SPEC-006 defers:

```text
POST /api/v1/workflows/{workflow_id}/resume
```

`/resume` moves to a later approval/human-interrupt runtime spec unless SPEC-006
implementation discovers a small, safe resume foundation that does not require
approval UI, approval APIs, streaming, or real Agent execution. The default
planning decision is to defer `/resume`.

## Status And Lifecycle Behavior

Runtime status changes must use the existing lifecycle model:

- The runtime must call `WorkflowService.transition_workflow_status`.
- The runtime must not mutate workflow statuses directly through ORM models or
  repositories.
- Invalid lifecycle transitions should fail safely and surface clear errors.
- The runtime should start only from an allowed initial status, primarily
  `CREATED` for the first `/run` implementation.
- Runtime failure before `WAITING_APPROVAL` should transition to `FAILED` where
  the existing lifecycle allows it.
- If failure occurs in a status that cannot transition to `FAILED`, the runtime
  should append a failure event and preserve the persisted status rather than
  forcing an invalid transition.
- The runtime should update the persisted `WorkflowState` through
  `WorkflowService.update_workflow_state`.

## Workflow Event Behavior

The runtime should append workflow events through `WorkflowEventService` for:

- runtime started
- node started
- node completed
- node failed
- runtime completed
- runtime failed

Event payloads must be small, JSON-compatible, and safe:

- include workflow id, node name, status, and bounded output summaries where
  useful
- do not include secrets, raw provider payloads, hidden reasoning, tokens, or
  large documents
- use deterministic event names such as
  `workflow.runtime.started`, `workflow.node.started`,
  `workflow.node.completed`, `workflow.node.failed`,
  `workflow.runtime.completed`, and `workflow.runtime.failed`

Event streaming remains deferred to SPEC-008.

## Audit Behavior

SPEC-006 should preserve audit behavior by using existing services:

- status transitions go through `WorkflowService.transition_workflow_status`
- state updates go through `WorkflowService.update_workflow_state`
- event appends go through `WorkflowEventService.append_event`

The runtime should not write audit rows directly unless a later implementation
task identifies a small helper that reuses existing audit conventions. Audit
query APIs remain out of scope.

## Error Handling

Runtime failures should be explicit and persisted where practical:

- append a failure event
- update `WorkflowState.error` when safe
- set the current step to the failed node
- transition to `FAILED` only through `WorkflowService` and only when allowed
- re-raise or map unexpected errors rather than swallowing them silently
- avoid logging or persisting secrets, raw provider payloads, hidden reasoning,
  or large documents

Suggested runtime exceptions:

- `WorkflowRuntimeError`
- `WorkflowRuntimePreconditionError`
- `WorkflowRuntimeNodeError`

API error mapping should be added only for known runtime errors. Unknown
exceptions should continue to be surfaced through normal FastAPI error handling.

## RBAC

SPEC-006 runtime write endpoints should use a conservative baseline:

| Endpoint | Allowed roles |
| --- | --- |
| `POST /api/v1/workflows/{workflow_id}/run` | Admin, Manager |
| `POST /api/v1/workflows/{workflow_id}/resume` | Deferred; Admin, Manager when implemented |

Existing SPEC-007 read/list/events behavior remains unchanged.

## User Stories

### US-003 - Run Workflow Foundation

As an Admin or Manager, I want to start runtime execution for a created
workflow so that the system can progress it through deterministic workflow
stages.

### US-018 - Runtime Progress Evidence

As an authenticated workflow reader, I want runtime steps to append events so
that workflow progress can be inspected through existing event APIs.

### US-019 - Runtime Failure Evidence

As an Admin, I want runtime failures to persist safe error state and failure
events so that failed workflows can be diagnosed later.

### US-023 - Audit Preservation

As an Admin, I want runtime lifecycle actions to preserve existing audit
behavior by using the workflow service layer.

## Acceptance Criteria

```gherkin
Given a workflow has status CREATED
When an Admin or Manager runs the workflow
Then the runtime executes deterministic placeholder nodes
And the workflow reaches WAITING_APPROVAL
And workflow events are appended for runtime and node progress
```

```gherkin
Given a workflow has a status that cannot be run
When an Admin or Manager runs the workflow
Then the runtime rejects execution with a clear client error
And no invalid status transition is persisted
```

```gherkin
Given a runtime node fails before WAITING_APPROVAL
When the runtime handles the failure
Then a failure event is appended
And safe error state is persisted where practical
And the workflow transitions to FAILED only through WorkflowService
```

```gherkin
Given a workflow runtime action changes workflow status
When the action is persisted
Then existing WorkflowService audit behavior is preserved
```

```gherkin
Given a Sales, Legal, Finance, or Viewer user
When the user calls the run endpoint
Then the API returns 403 Forbidden
```

## Validation Strategy

SPEC-006 implementation tasks should use the Docker backend quality gate:

```bash
git status --short
docker-compose config
docker-compose up -d postgres
docker-compose run --rm backend-test alembic upgrade head
docker-compose build backend-test
docker-compose run --rm backend-test pytest
docker-compose run --rm backend-test ruff check .
docker-compose run --rm backend-test black --check .
docker-compose run --rm backend-test mypy app
git diff --check
```

Focused tests should cover:

- runtime state adapter round trips
- graph construction and deterministic node order
- node output shape and safe payload bounds
- runtime service success path from `CREATED` to `WAITING_APPROVAL`
- event emission for runtime and node start/completion
- runtime failure behavior and failure events
- invalid lifecycle/precondition behavior
- run endpoint success, authentication failure, RBAC failure, missing workflow,
  invalid status/precondition behavior, and validation behavior
- confirmation that `/resume`, streaming, real Agents, LLM providers, RAG,
  document indexing, frontend, migrations, model changes, queues, and
  procurement-specific policy logic remain out of scope

## Out-of-scope List

- Real LLM provider calls.
- Multi-provider routing.
- Production-grade Agent implementations.
- RAG.
- Document indexing.
- WebSocket or server-sent event streaming.
- Frontend.
- Human approval UI.
- Advanced human-in-the-loop resume behavior.
- Procurement-specific policy engine.
- Async distributed worker queue.
- Production-grade retry scheduler.
- Audit query APIs.
- New migrations or database model changes.
