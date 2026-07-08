# SPEC-005 - Workflow State

## Status

Draft

## Context

Enterprise Multi-Agent OS is a state-driven workflow orchestration system. The
first MVP domain is procurement quotation automation, but the workflow state
foundation must support future business domains without embedding
procurement-specific Agent logic.

SPEC-001 through SPEC-004 established the backend, database, authentication,
authorization, and storage infrastructure. SPEC-005 starts Phase 2 by defining
the durable workflow state foundation that later specs will use for LangGraph
runtime, workflow APIs, event streaming, Agents, approvals, and frontend
monitoring.

Workflow API endpoints are deferred to SPEC-007 - Workflow API. SPEC-005 covers
schemas, lifecycle rules, service-level behavior, repository usage, workflow
events, and service-level audit writes only.

## Goals

- Define typed WorkflowState schemas aligned with `SPEC.md` and
  `.ai/project/API_CONTRACT.md`.
- Define workflow status values and lifecycle semantics.
- Define allowed workflow status transitions.
- Define workflow service foundation responsibilities for later implementation.
- Use existing `Workflow`, `WorkflowEvent`, and `AuditLog` models where
  appropriate.
- Define workflow event append/read behavior.
- Define service-level audit logging behavior for important workflow lifecycle
  actions.
- Add tests for lifecycle validation, transition rules, event append/read
  behavior, and audit behavior.

## Non-goals

- Workflow API endpoints.
- API pagination or filtering.
- API route RBAC policies.
- LangGraph runtime.
- Agents or Agent execution.
- LLM providers.
- RAG or document indexing.
- Email generation.
- Frontend implementation.
- Human approval UI.
- Procurement-specific Agent logic.

## Architecture Notes

SPEC-005 follows the existing backend layering:

```text
API -> Service -> Repository/Tool -> External System
```

No API route layer is introduced in this spec. Workflow state behavior should be
implemented behind service methods that can later be called by API routes,
LangGraph runtime code, or tests.

The service layer owns lifecycle decisions and audit side effects. Repository
code owns persistence mechanics and does not decide workflow business rules.
Unknown inputs must be parsed into typed schemas before service methods operate
on them.

## Data Model Usage

SPEC-005 uses the Phase 1 SQLAlchemy models already created in SPEC-002:

- `Workflow`
- `WorkflowEvent`
- `AuditLog`

No new database tables are required by default for SPEC-005. A migration should
only be proposed if implementation discovers that existing Phase 1 models cannot
persist required WorkflowState fields or lifecycle evidence.

Workflow state schemas should be Pydantic v2 models and should map cleanly to
the persisted workflow record plus event history.

## Workflow Lifecycle

Supported workflow statuses are:

```text
CREATED
PLANNING
RETRIEVING
CALCULATING
CHECKING_COMPLIANCE
VALIDATING
WAITING_APPROVAL
APPROVED
REJECTED
GENERATING_EMAIL
COMPLETED
FAILED
CANCELLED
```

Initial workflow state starts at `CREATED`.

Allowed transitions should be explicit and test-covered. The baseline lifecycle
is:

```text
CREATED -> PLANNING
PLANNING -> RETRIEVING
RETRIEVING -> CALCULATING
CALCULATING -> CHECKING_COMPLIANCE
CHECKING_COMPLIANCE -> VALIDATING
VALIDATING -> WAITING_APPROVAL
VALIDATING -> FAILED
WAITING_APPROVAL -> APPROVED
WAITING_APPROVAL -> REJECTED
APPROVED -> GENERATING_EMAIL
GENERATING_EMAIL -> COMPLETED
```

Failure and cancellation behavior should be explicit:

```text
PLANNING -> FAILED
RETRIEVING -> FAILED
CALCULATING -> FAILED
CHECKING_COMPLIANCE -> FAILED
VALIDATING -> FAILED
GENERATING_EMAIL -> FAILED
CREATED -> CANCELLED
PLANNING -> CANCELLED
RETRIEVING -> CANCELLED
CALCULATING -> CANCELLED
CHECKING_COMPLIANCE -> CANCELLED
VALIDATING -> CANCELLED
WAITING_APPROVAL -> CANCELLED
```

Terminal statuses are:

```text
COMPLETED
FAILED
CANCELLED
REJECTED
```

Terminal workflows must not transition again in SPEC-005.

## Workflow Event Behavior

Workflow events are append-only records for important lifecycle actions.

Events should include, where available:

- workflow id
- event type
- actor type
- actor id
- agent name
- status
- message
- payload
- created timestamp

SPEC-005 service behavior should support:

- appending a workflow event for lifecycle actions
- reading workflow events for one workflow in creation order
- storing structured payloads without exposing hidden reasoning
- preserving event history when workflow status changes

Event streaming is deferred to SPEC-008 - Event Streaming.

## Audit Behavior

SPEC-005 includes service-level audit log writes for important workflow
lifecycle actions, such as:

- workflow created
- workflow status changed
- workflow failed
- workflow cancelled
- approval wait requested

Audit records should use the existing `AuditLog` model where appropriate and
should avoid logging secrets or sensitive hidden reasoning.

Audit query APIs are out of scope and deferred to a later spec.

## User Stories

### US-003 - Create Workflow from Text Request Foundation

As a Sales user, I want the system to create a durable workflow state record so
that the workflow can later be processed by the orchestration runtime.

### US-018 - View Workflow Progress Foundation

As a Sales user, I want workflow state and events to be recorded so that later
UI work can show workflow progress.

### US-019 - View Agent Errors Foundation

As an Admin, I want workflow failures and events to be persisted so that later
workflow detail views can explain failed work.

### US-023 - Audit Log Foundation

As an Admin, I want workflow lifecycle actions to produce audit evidence so the
system remains explainable and traceable.

## Acceptance Criteria

```gherkin
Given a workflow state payload is created
When it is parsed by the backend
Then it conforms to typed WorkflowState schemas
```

```gherkin
Given a workflow has status CREATED
When it transitions to PLANNING
Then the transition is accepted
And a workflow event can be appended
And a service-level audit record can be written
```

```gherkin
Given a workflow has status CREATED
When it attempts to transition directly to COMPLETED
Then the transition is rejected
```

```gherkin
Given a workflow has a terminal status
When another transition is requested
Then the transition is rejected
```

```gherkin
Given workflow events have been appended
When events are read for the workflow
Then they are returned in creation order
```

```gherkin
Given a workflow lifecycle action is performed
When the service commits the action
Then important lifecycle actions have audit evidence where appropriate
```

## Validation Strategy

SPEC-005 implementation tasks should use the Docker backend quality gate:

```bash
docker-compose config
docker-compose up -d postgres
docker-compose run --rm backend-test alembic upgrade head
docker-compose run --rm backend-test pytest
docker-compose run --rm backend-test ruff check .
docker-compose run --rm backend-test black --check .
docker-compose run --rm backend-test mypy app
git diff --check
```

Focused tests should cover:

- WorkflowState schema parsing and serialization
- lifecycle status values
- allowed and rejected transitions
- terminal status behavior
- event append/read behavior
- service-level audit writes
- no API endpoint creation in this spec

## Out-of-scope List

- Workflow API endpoints
- API pagination/filtering
- API route RBAC policies
- LangGraph runtime
- Agents
- LLM providers
- RAG
- Document indexing
- Email generation
- Frontend
- Human approval UI
- Procurement-specific Agent logic
