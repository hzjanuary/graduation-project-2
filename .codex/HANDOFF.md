# Context Handoff

## Current Project Status

Closed specs:

- SPEC-001 Bootstrap Backend - Approved / Closed
- SPEC-002 Database Foundation - Approved / Closed
- SPEC-003 Authentication and RBAC - Approved / Closed
- SPEC-004 Storage Infrastructure - Approved / Closed
- SPEC-005 Workflow State - Approved / Closed
- SPEC-007 Workflow API Endpoints - Approved / Closed

Current active spec:

- SPEC-006 LangGraph Runtime - TASK 006.1 implemented, awaiting review

## Current SPEC-006 Implementation State

Planning files:

- `.ai/specs/SPEC-006-langgraph-runtime/spec.md`
- `.ai/specs/SPEC-006-langgraph-runtime/tasks.md`

Completed task:

- `TASK 006.1 - Runtime State Adapter and Contracts`

TASK 006.1 deliverables:

- `backend/app/runtime/__init__.py`
- `backend/app/runtime/schemas.py`
- `backend/app/runtime/state_adapter.py`
- `backend/app/tests/test_runtime_state_adapter.py`
- `backend/README.md` runtime adapter notes

TASK 006.1 behavior:

- Defines deterministic runtime stages: planner, retrieval, quotation,
  compliance, validation, approval, and email_preparation.
- Defines `RuntimeWorkflowState` and `RuntimeWorkflowResult` Pydantic v2
  contracts.
- Provides pure adapter functions between persisted `WorkflowState` and runtime
  state:
  - `workflow_state_to_runtime_state`
  - `runtime_state_to_workflow_state`
- Preserves workflow id, workflow type, domain, request, status, metadata,
  runtime context, outputs, stage outputs, steps, error, retry count, and
  events.
- Keeps adapters side-effect free and JSON-compatible.

Overall SPEC-006 scope:

- LangGraph-based workflow runtime foundation.
- Runtime state adapter between persisted `WorkflowState` and LangGraph state.
- Deterministic placeholder graph nodes for planner, retrieval, quotation,
  compliance, validation, approval wait, and email preparation.
- Runtime service using existing `WorkflowService` and `WorkflowEventService`.
- Event append behavior through existing workflow event service.
- Audit preservation through existing workflow service behavior.
- `POST /api/v1/workflows/{workflow_id}/run` with Admin/Manager RBAC.

Explicit SPEC-006 deferrals:

- `POST /api/v1/workflows/{workflow_id}/resume`.
- WebSocket/SSE event streaming.
- Real Agents.
- LLM provider calls and multi-provider routing.
- RAG and document indexing.
- Frontend.
- Advanced human approval UI.
- Procurement-specific policy engine.
- Distributed worker queue.
- Production retry scheduler.
- Audit query APIs.
- Migrations or database model changes.

## Next Task

- Review `TASK 006.1 - Runtime State Adapter and Contracts`.
- Then implement `TASK 006.2 - LangGraph Dependency and Graph Skeleton` only
  after TASK 006.1 is approved.

## Expected SPEC-006 Quality Gate

- `git status --short`
- `docker-compose config`
- `docker-compose up -d postgres`
- `docker-compose run --rm backend-test alembic upgrade head`
- `docker-compose build backend-test`
- `docker-compose run --rm backend-test pytest`
- `docker-compose run --rm backend-test ruff check .`
- `docker-compose run --rm backend-test black --check .`
- `docker-compose run --rm backend-test mypy app`
- `git diff --check`

## Important Constraints For SPEC-006

- Use existing SPEC-005 `WorkflowState`, lifecycle helpers, `WorkflowService`,
  and `WorkflowEventService`.
- Use existing SPEC-007 workflow API router, auth dependencies, RBAC role sets,
  and direct Pydantic response model style.
- Runtime status transitions must go through `WorkflowService`.
- Runtime events must go through `WorkflowEventService`.
- Keep placeholder nodes deterministic and no-LLM.
- Do not implement real Agent reasoning, retrieval, pricing, compliance,
  email generation, streaming, frontend, queues, migrations, or model changes.

## Known Warnings

- Existing FastAPI/TestClient StarletteDeprecationWarning is non-blocking.
- LF/CRLF warnings from `git diff --check` are non-blocking when no whitespace
  errors are reported.

## Harness State

- SPEC-005 final review recorded and approved.
- SPEC-007 final review recorded and approved.
- SPEC-006 planning recorded.
- TASK 006.1 implementation should be recorded after current validation.
