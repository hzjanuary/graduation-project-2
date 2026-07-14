# SPEC-011 - LLM Provider Abstraction

## Status

Draft

## Context

Enterprise Multi-Agent OS now has a stable deterministic workflow foundation:

- SPEC-006 provides LangGraph runtime orchestration with deterministic
  placeholder nodes and a `/run` endpoint that stops at `WAITING_APPROVAL`.
- SPEC-007 exposes authenticated workflow REST APIs.
- SPEC-008 persists and streams workflow events.
- SPEC-009 provides the first frontend dashboard.
- SPEC-010 provides deterministic local demo data and a board-ready runbook.

The project contract requires pluggable LLM providers: Groq, OpenRouter,
Ollama, and Gemini. SPEC-011 plans the provider abstraction and controlled
runtime integration needed to move from deterministic placeholders toward
AI-assisted workflow stages without destabilizing the local demo, tests, or
workflow service boundaries.

SPEC-011 is not an Agent implementation spec. It defines the provider layer,
LLM service boundary, safe configuration, structured-output strategy, and
feature-flagged runtime integration path that later Agent specs can use.

## Product Goal

- Move deterministic demo runtime nodes toward real AI-assisted procurement
  workflow stages.
- Keep the board-ready demo stable when no provider keys are configured.
- Allow switching providers without changing `WorkflowService`,
  `WorkflowEventService`, or API route logic.
- Keep LangGraph runtime nodes dependent on provider-independent LLM service
  contracts, not raw provider SDKs.
- Support future multi-agent behavior without binding Agents directly to
  Groq, OpenRouter, Ollama, Gemini, or any specific SDK.
- Preserve deterministic tests and offline local development through a fake
  provider.

## Non-goals

- RAG, embeddings, document indexing, or vector retrieval.
- Frontend provider-management UI.
- Admin API key management.
- Billing, cost dashboards, or quota management.
- `/resume` or human approval continuation.
- Production secret vault integration.
- Real LLM token streaming to the frontend.
- Agent thought streaming or hidden reasoning exposure.
- Replacing all deterministic runtime behavior at once.
- New backend public endpoints.
- Database model changes or migrations.

## Provider Support

SPEC-011 must plan support for these provider modes:

| Provider | Role | Configuration shape |
| --- | --- | --- |
| Groq | Remote OpenAI-compatible chat provider | `GROQ_API_KEY`, `LLM_MODEL` or `GROQ_MODEL` |
| OpenRouter | Remote OpenAI-compatible provider/router | `OPENROUTER_API_KEY`, `LLM_MODEL` or `OPENROUTER_MODEL` |
| Ollama | Local provider for offline development | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |
| Gemini | Remote Gemini API provider | `GEMINI_API_KEY`, `LLM_MODEL` or `GEMINI_MODEL` |
| Fake | Deterministic provider for tests and no-key local demo | no API key |

The fake provider is required. It should produce deterministic, typed outputs
for unit tests, runtime integration tests, and local development when no real
provider is configured.

No implementation task may commit real API keys. Provider configuration must
come from environment variables only.

## Provider Abstraction

Implementation should introduce an `app/llm` package with provider-independent
contracts. Suggested contracts:

- `LLMChatMessage`: role, content, optional name, and bounded metadata.
- `LLMChatRequest`: messages, model, temperature, max output tokens,
  structured response format, timeout, and request metadata.
- `LLMChatResponse`: text content, optional parsed JSON, finish reason,
  provider name, model, request id, usage metadata, and bounded metadata.
- `LLMStructuredRequest`: prompt/messages plus a Pydantic or JSON schema output
  contract.
- `LLMStructuredResponse`: validated structured payload plus provider metadata.
- `LLMModelCapabilities`: JSON mode support, tool/function support, context
  limits, local/remote marker, and streaming capability marker for future work.
- `LLMUsageMetadata`: prompt tokens, completion tokens, total tokens, and
  provider-reported cost fields when available.
- `LLMProviderError`: typed provider exception with a safe category.

Provider clients should implement one common async protocol, such as:

```text
LLMProvider.complete_chat(request: LLMChatRequest) -> LLMChatResponse
LLMProvider.complete_structured(request: LLMStructuredRequest) -> LLMStructuredResponse
LLMProvider.health_check() -> LLMProviderHealth
```

The abstraction must normalize provider differences:

- Groq and OpenRouter can use OpenAI-compatible HTTP shapes where appropriate.
- Ollama uses a local HTTP endpoint and should not require an API key.
- Gemini uses its own API shape behind the same provider protocol.
- Provider raw payloads must stay inside provider-specific modules.
- Runtime and Agent code should never inspect provider-specific response
  objects.

## Configuration

SPEC-011 implementation should extend typed settings and `.env.example` in the
first implementation task. Planned variables:

```text
LLM_PROVIDER=fake
LLM_MODEL=
LLM_RUNTIME_ENABLED=false
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2

GROQ_API_KEY=
GROQ_MODEL=

OPENROUTER_API_KEY=
OPENROUTER_MODEL=

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=

GEMINI_API_KEY=
GEMINI_MODEL=
```

Safe default behavior:

- `LLM_PROVIDER=fake` or equivalent deterministic fallback keeps local tests
  offline.
- `LLM_RUNTIME_ENABLED=false` keeps the current deterministic runtime path
  unchanged by default.
- Missing provider keys must not break the board-ready demo.
- Real provider mode should fail fast with a safe configuration error if the
  selected provider requires a missing key.
- Real secrets must never be committed to the repository.

## Runtime Integration Strategy

SPEC-011 should add an LLM service layer behind the provider abstraction.

Target layering:

```text
Runtime node or future Agent
  -> LLMService
      -> selected LLMProvider
          -> provider-specific HTTP/client implementation
```

Runtime integration rules:

- Runtime nodes depend on `LLMService` or a narrow LLM interface, not raw
  provider clients.
- Existing deterministic runtime nodes remain the default path.
- LLM-assisted nodes are enabled only behind a runtime feature flag.
- Existing `POST /api/v1/workflows/{workflow_id}/run` behavior remains stable
  unless a later task explicitly changes it.
- Runtime still uses `WorkflowService` for lifecycle status transitions.
- Runtime still uses `WorkflowEventService` for persisted events.
- Runtime must not mutate workflow status directly.
- Provider failures should append safe workflow events and persist bounded error
  state where practical.
- Event payloads must not include API keys, full prompts, raw provider payloads,
  hidden reasoning, or unbounded inputs/outputs.

The first LLM-enabled runtime integration should use the fake provider in tests
and remain deterministic. Real providers may be selectable in local development
only when env vars are configured.

## Prompt And Structured Output Strategy

Prompt work should be explicit, bounded, and separate from provider clients.

Planned prompt/output areas:

- Intake/requirement extraction.
- Supplier or pricing analysis placeholder.
- Legal/compliance analysis placeholder.
- Finance/risk analysis placeholder.
- Approval package preparation.

Rules:

- Use structured response schemas where practical.
- Validate LLM output with Pydantic before merging into `WorkflowState`.
- Treat invalid JSON, missing fields, schema mismatch, and unsafe content as
  typed provider or output validation failures.
- Do not use LLMs for deterministic arithmetic.
- Calculator arithmetic remains a deterministic tool responsibility.
- Prompts must not request hidden chain-of-thought.
- Persist only bounded summaries and validated structured outputs.

## Error Handling

Provider errors should be classified into safe categories:

- configuration error
- authentication error
- rate limit
- timeout
- cancellation
- invalid request
- invalid response
- provider unavailable
- safety/content error
- unknown provider error

Retry strategy:

- Keep retries bounded by `LLM_MAX_RETRIES`.
- Retry only retryable categories such as timeouts, rate limits, and temporary
  provider unavailable errors.
- Do not retry authentication or configuration failures.
- Respect request cancellation/timeouts.
- Keep provider-specific error details out of client-facing API responses.

## Observability And Safety

Logs and events may include:

- provider name
- model name
- workflow id
- runtime stage
- request id/correlation id
- error category
- bounded duration/usage metadata

Logs and events must not include:

- API keys or bearer tokens
- raw provider payloads
- full prompts when they may contain user or business-sensitive text
- full generated content unless explicitly bounded and safe
- hidden reasoning or chain-of-thought

Prompt and output sizes should be bounded before provider calls and before
state/event persistence. Structured outputs should be validated before state
updates.

## Testing Strategy

SPEC-011 implementation must keep tests deterministic:

- Unit tests use the fake provider by default.
- Provider client tests use mocked HTTP transports, not live network calls.
- No test may require real API keys.
- No test may require Groq, OpenRouter, Ollama, or Gemini availability.
- Runtime integration tests use fake provider output and feature flags.
- Contract tests should cover request/response normalization across providers.
- Error tests should cover config, auth, rate limit, timeout, invalid response,
  unavailable provider, and retry behavior.

Network access and real credentials are explicitly out of scope for automated
tests.

## Documentation

Implementation tasks should update backend documentation with:

- provider configuration overview
- safe `.env.example` variables
- Groq setup notes
- OpenRouter setup notes
- Ollama local setup notes
- Gemini setup notes
- fake provider/no-key demo behavior
- troubleshooting for missing keys, provider unavailable, timeout, rate limit,
  invalid structured output, and disabled LLM runtime mode

Documentation must clearly state that deterministic demo behavior remains the
default unless LLM runtime mode is explicitly enabled.

## User Stories

### Runtime Operator - Preserve Demo Stability

As a demo operator, I want the system to keep deterministic runtime behavior
when no provider keys are configured so that the board-ready demo remains
repeatable.

### Developer - Use One Provider Contract

As a backend developer, I want runtime nodes and future Agents to call one LLM
service interface so that provider-specific APIs do not leak into workflow
logic.

### Administrator - Configure Provider By Environment

As an operator, I want provider selection and keys configured through
environment variables so that secrets are not committed and providers can be
swapped per environment.

### Reviewer - Validate Structured LLM Output

As a reviewer, I want LLM output validated before workflow state is updated so
that invalid provider responses cannot silently corrupt persisted state.

## Acceptance Criteria

```gherkin
Given no real LLM provider keys are configured
When the backend test suite runs
Then tests use the fake provider or deterministic runtime path
And no external network access is required
```

```gherkin
Given a runtime node needs LLM assistance
When the node is implemented in a later task
Then it depends on LLMService contracts
And it does not import Groq, OpenRouter, Ollama, or Gemini clients directly
```

```gherkin
Given a selected remote provider is missing its required API key
When the provider is initialized
Then the system reports a safe configuration error
And no secret value is logged
```

```gherkin
Given a provider returns invalid structured JSON
When the LLM service validates the response
Then the service returns or raises a typed invalid-response error
And workflow state is not updated with unvalidated content
```

```gherkin
Given LLM runtime mode is disabled
When a workflow is run through the existing run endpoint
Then the current deterministic runtime behavior remains unchanged
```

## Validation Strategy

Planning-only validation for SPEC-011:

```bash
git status --short
docker-compose config
git diff --check
```

Implementation tasks should use the backend quality gate:

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

Provider-specific implementation tasks should additionally prove mocked HTTP
client behavior without live provider calls.

## Out-of-scope List

- RAG, embeddings, document upload, document indexing, or vector retrieval.
- Frontend provider-management UI.
- Admin provider key management APIs.
- Billing, cost dashboards, or token budget dashboards.
- `/resume` and human approval continuation.
- Production secret vault integration.
- Real LLM token streaming to frontend clients.
- Agent thought streaming or hidden reasoning exposure.
- Full Agent implementation.
- Replacing deterministic runtime behavior without a feature flag.
- New public backend endpoints.
- Database model changes or migrations.
