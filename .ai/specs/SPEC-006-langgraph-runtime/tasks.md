# SPEC-006 Tasks - LangGraph Runtime

## TASK 006.1 - Runtime State Adapter and Contracts

### Objective

Define typed runtime contracts and adapters between persisted `WorkflowState`
and LangGraph runtime state.

### Scope

- Add runtime-facing schemas or typed dictionaries where useful.
- Define node names and deterministic runtime event names.
- Convert `WorkflowState` to a LangGraph-compatible state object.
- Convert graph output back into `WorkflowState`.
- Keep adapter behavior generic and product-ready.
- Add tests for adapter round trips and JSON-compatible payloads.

### Deliverables

- Runtime contracts module.
- Runtime state adapter module.
- Focused adapter tests.
- README notes only if useful.

### Acceptance Criteria

- Adapter can import and process existing `WorkflowState`.
- Adapter preserves workflow id, status, workflow type, domain, request,
  runtime context, outputs, steps, and error fields.
- Adapter output is JSON-compatible where persisted.
- No graph execution, API routes, migrations, model changes, Agents, LLM, RAG,
  document indexing, streaming, or frontend work is implemented.

### Out-of-scope

- LangGraph dependency wiring.
- Runtime service orchestration.
- API endpoints.
- Real Agent outputs.
- Human approval resume behavior.

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

## TASK 006.2 - LangGraph Dependency and Graph Skeleton

### Objective

Add the LangGraph dependency and build the first workflow graph skeleton.

### Scope

- Add the required LangGraph package dependency.
- Update lock files through the existing Poetry workflow.
- Define graph construction code.
- Register deterministic placeholder node names:
  - planner
  - retrieval
  - quotation
  - compliance
  - validation
  - approval
  - email_preparation
- Route the initial run path through the pre-approval nodes and stop at
  `WAITING_APPROVAL`.
- Add tests proving graph construction and node ordering.

### Deliverables

- Runtime graph module.
- Dependency updates in `backend/pyproject.toml` and `backend/poetry.lock`.
- Graph skeleton tests.
- README notes if dependency/runtime usage needs documentation.

### Acceptance Criteria

- LangGraph imports in the backend test environment.
- Graph can be constructed without external services beyond the test database
  stack.
- Graph contains the planned node names.
- Initial graph route does not execute real LLM, RAG, Agent, email, streaming,
  queue, or frontend behavior.

### Out-of-scope

- Runtime service persistence.
- Run API endpoint.
- Real node logic.
- `/resume`.
- Human approval UI.

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

## TASK 006.3 - Deterministic Runtime Nodes

### Objective

Implement deterministic, no-LLM placeholder runtime nodes for the initial
workflow graph.

### Scope

- Implement placeholder nodes for planner, retrieval, quotation, compliance,
  validation, approval wait, and email preparation.
- Keep `/run` execution limited to the safe pre-approval path by default.
- Produce bounded, deterministic outputs in generic `WorkflowState` sections.
- Add node start/completion metadata suitable for event payloads.
- Add tests for each node output shape and no-secret/no-hidden-reasoning
  payload bounds.

### Deliverables

- Runtime nodes module.
- Runtime node tests.
- README notes only if useful.

### Acceptance Criteria

- Nodes are deterministic and do not call LLM providers or external retrieval.
- Nodes update only generic runtime state fields.
- Approval node can mark the workflow as waiting for approval without approving
  or generating customer-facing email.
- Email preparation node exists as a future continuation placeholder but does
  not bypass the approval rule in `/run`.

### Out-of-scope

- Production Agent implementations.
- LLM provider abstraction.
- RAG/document search.
- Pricing/calculation engine.
- Email generation quality.
- Human approval APIs or UI.

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

## TASK 006.4 - Runtime Service

### Objective

Create the runtime service that loads persisted workflow state, invokes the
graph, persists status/state changes through existing services, and appends
events.

### Scope

- Add a workflow runtime service class.
- Reuse `WorkflowService` for all status transitions and state updates.
- Reuse `WorkflowEventService` for runtime/node events.
- Validate that `/run` starts from an allowed status, initially `CREATED`.
- Execute deterministic graph nodes in order.
- Persist successful runtime state through `WorkflowService`.
- Handle failures with safe state/error updates and failure events.
- Keep transactions caller-owned; flush through services but do not commit
  inside the runtime service unless an existing convention requires it.

### Deliverables

- Runtime service module.
- Runtime exceptions if useful.
- Runtime service tests using the existing database test pattern.
- README notes if useful.

### Acceptance Criteria

- Runtime service can run a `CREATED` workflow to `WAITING_APPROVAL`.
- Runtime status transitions use existing lifecycle validation.
- Runtime events are appended for start/completion/failure behavior.
- Invalid runtime preconditions are rejected clearly.
- Runtime failure does not silently swallow unexpected errors.
- Existing audit behavior is preserved through `WorkflowService`.

### Out-of-scope

- API route implementation.
- `/resume`.
- Event streaming.
- Distributed queues.
- Production retry scheduler.
- Real Agents, LLM, RAG, document indexing, frontend, migrations, or model
  changes.

### Validation Commands

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

## TASK 006.5 - Run Workflow API Endpoint

### Objective

Expose the runtime through `POST /api/v1/workflows/{workflow_id}/run`.

### Scope

- Add a runtime service dependency provider.
- Add request/response schemas only if `WorkflowResponse` is insufficient.
- Implement `POST /api/v1/workflows/{workflow_id}/run`.
- Apply RBAC: Admin and Manager only.
- Map missing workflow, invalid runtime precondition, and invalid transition
  errors to clear HTTP responses.
- Commit at the API route boundary after successful runtime execution.
- Add API tests for success, auth failure, RBAC failure, missing workflow,
  invalid workflow id, invalid status/precondition behavior, and no `/resume`
  route.

### Deliverables

- Runtime dependency provider.
- Run endpoint implementation.
- API tests.
- README workflow API notes.

### Acceptance Criteria

- Admin or Manager can run a `CREATED` workflow.
- Successful run returns the updated workflow state.
- Sales, Legal, Finance, and Viewer receive `403 Forbidden`.
- Unauthenticated requests return `401 Unauthorized`.
- Missing workflows return `404 Not Found`.
- Invalid runtime preconditions return a clear client error.
- API route commits only after successful runtime execution.
- `/resume` remains unimplemented in SPEC-006 unless explicitly approved later.

### Out-of-scope

- Resume endpoint.
- WebSocket/SSE streaming.
- Approval APIs/UI.
- Real Agents.
- LLM, RAG, document indexing, frontend, queues, migrations, or model changes.

### Validation Commands

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

## TASK 006.6 - Runtime Events and Failure Handling Hardening

### Objective

Harden runtime observability and failure behavior before final review.

### Scope

- Add or improve tests for runtime started/completed/failed events.
- Add or improve tests for node started/completed/failed events.
- Verify deterministic event ordering through existing event APIs/services.
- Verify safe, bounded event payloads.
- Verify failure state persistence where practical.
- Verify invalid transitions do not produce invalid persisted statuses.
- Verify no secrets/raw provider payloads/hidden reasoning are logged or
  persisted.
- Fix small bugs discovered by tests.

### Deliverables

- Additional runtime service and API tests.
- Small bug fixes limited to SPEC-006 if required.
- README cleanup if runtime behavior needs clarification.

### Acceptance Criteria

- Runtime event behavior is covered by tests.
- Failure paths append useful failure events.
- Safe error state is persisted where practical.
- Invalid lifecycle transitions fail safely.
- Test suite and quality gate pass.
- No out-of-scope features are added.

### Out-of-scope

- Event streaming.
- Production retry scheduler.
- Distributed queue.
- Real Agents, LLM, RAG, document indexing, frontend, migrations, model
  changes, or procurement-specific policy logic.

### Validation Commands

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

## TASK 006.7 - Runtime Tests and SPEC-006 Final Review

### Objective

Verify SPEC-006 is complete, hardened, and ready to close.

### Scope

- Review runtime adapter, graph, deterministic nodes, runtime service, run API,
  events, failure handling, RBAC, and tests.
- Confirm validation proof.
- Confirm `/resume`, event streaming, real Agents, LLM provider calls, RAG,
  document indexing, frontend, queues, migrations, and model changes remain out
  of scope.
- Record Harness evidence.

### Deliverables

- SPEC-006 final review result.
- Harness durable story/trace evidence when available.
- Recommendation for the next SPEC.

### Acceptance Criteria

- All SPEC-006 implementation tasks are completed and validated.
- Runtime can run a created workflow to waiting for approval.
- Runtime uses existing workflow state, lifecycle, event, audit, and API
  foundations.
- Runtime status changes go through `WorkflowService`.
- Runtime events go through `WorkflowEventService`.
- Run endpoint uses Admin/Manager RBAC.
- Quality gate passes.
- No out-of-scope behavior is implemented.

### Out-of-scope

- Application code changes during final review except review-only fixes if
  explicitly approved by a later prompt.
- Resume endpoint.
- Event streaming.
- Real Agents or LLM providers.
- RAG/document indexing.
- Frontend.
- Migrations or database model changes.

### Validation Commands

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
