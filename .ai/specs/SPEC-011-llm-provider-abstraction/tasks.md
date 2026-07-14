# SPEC-011 - LLM Provider Abstraction Tasks

## TASK 011.1 - LLM Provider Contracts and Settings

### Objective

Define provider-independent LLM contracts, typed settings, fake-provider
defaults, and safe configuration validation without implementing real provider
clients or runtime integration.

### Scope

- Add an `app/llm` package structure.
- Define Pydantic v2 contracts for chat messages, chat requests, chat
  responses, structured requests/responses, usage metadata, model capabilities,
  provider health, and provider errors.
- Define provider name enum values for Groq, OpenRouter, Ollama, Gemini, and
  Fake.
- Add typed settings for provider selection, models, API keys, timeouts,
  retries, and LLM runtime feature flag.
- Update `backend/.env.example` with safe empty/default provider variables.
- Add tests for settings defaults, missing-key validation, enum parsing, error
  categories, and JSON serialization.

### Deliverables

- `backend/app/llm/__init__.py`
- `backend/app/llm/schemas.py`
- `backend/app/llm/errors.py`
- `backend/app/llm/settings.py` or equivalent settings integration
- `backend/app/tests/test_llm_contracts.py`
- `backend/app/tests/test_llm_settings.py`
- `backend/.env.example` updated
- `backend/README.md` updated if useful

### Acceptance Criteria

- Contracts import cleanly.
- Provider enum includes Groq, OpenRouter, Ollama, Gemini, and Fake.
- Fake/no-key defaults preserve local deterministic behavior.
- Real provider modes fail safely when required keys are missing.
- No provider HTTP clients are implemented.
- No runtime behavior changes are made.
- No real secrets are committed.

### Out-of-scope

- Groq/OpenRouter/Ollama/Gemini client implementations.
- LLM service router.
- Runtime node changes.
- Prompt templates.
- Backend API changes.
- Frontend changes.
- Migrations or model changes.

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

## TASK 011.2 - Provider Client Implementations with Mocked HTTP Tests

### Objective

Implement provider-specific clients for Groq, OpenRouter, Ollama, Gemini, and
Fake behind the common provider protocol, with all tests using mocked HTTP or
deterministic fake behavior.

### Scope

- Add a common async `LLMProvider` protocol.
- Implement a deterministic `FakeLLMProvider`.
- Implement Groq and OpenRouter clients using OpenAI-compatible HTTP shapes
  where appropriate.
- Implement an Ollama HTTP client for local model endpoints.
- Implement a Gemini HTTP client behind the common contract.
- Normalize provider responses into shared response schemas.
- Map provider failures into typed provider errors.
- Add mocked HTTP tests for success, auth/config failure, rate limit, timeout,
  unavailable provider, invalid JSON, and malformed structured output.

### Deliverables

- `backend/app/llm/providers/base.py`
- `backend/app/llm/providers/fake.py`
- `backend/app/llm/providers/openai_compatible.py` or equivalent
- `backend/app/llm/providers/groq.py`
- `backend/app/llm/providers/openrouter.py`
- `backend/app/llm/providers/ollama.py`
- `backend/app/llm/providers/gemini.py`
- `backend/app/tests/test_llm_provider_fake.py`
- `backend/app/tests/test_llm_provider_groq.py`
- `backend/app/tests/test_llm_provider_openrouter.py`
- `backend/app/tests/test_llm_provider_ollama.py`
- `backend/app/tests/test_llm_provider_gemini.py`

### Acceptance Criteria

- Every provider conforms to the common async provider protocol.
- Fake provider returns deterministic responses.
- Provider tests do not use live network access.
- Provider tests do not require real API keys.
- Raw provider payloads do not leak outside provider modules.
- Provider errors are normalized into safe categories.

### Out-of-scope

- Runtime integration.
- LLM service fallback routing.
- Prompt template package.
- Frontend provider UI.
- Real provider smoke tests.

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

## TASK 011.3 - LLM Service Router, Fallbacks, and Error Handling

### Objective

Add an LLM service layer that selects the configured provider, applies timeout
and retry policy, preserves deterministic fake fallback behavior, and exposes a
single interface to runtime nodes and future Agents.

### Scope

- Add `LLMService` or equivalent application service.
- Add provider factory/router based on typed settings.
- Implement bounded retries for retryable provider errors.
- Implement timeout and cancellation handling.
- Keep fake provider as default/offline path.
- Add safe fallback behavior for no-key local demo mode.
- Add dependency provider wiring if appropriate, without changing runtime
  behavior yet.
- Add tests for provider selection, fake default, missing-key behavior, retry
  policy, non-retryable failures, timeout handling, and safe error messages.

### Deliverables

- `backend/app/llm/service.py`
- `backend/app/llm/provider_factory.py`
- `backend/app/core/dependencies.py` updated only if provider dependency wiring
  is needed
- `backend/app/tests/test_llm_service.py`
- `backend/app/tests/test_llm_provider_factory.py`
- README notes if useful

### Acceptance Criteria

- Runtime/Agent-facing code can call one LLM service interface.
- Provider selection is settings-driven.
- Fake provider remains available for tests and no-key local development.
- Retries are bounded and category-aware.
- Provider errors are safe and do not expose secrets or raw provider payloads.
- Existing runtime behavior is unchanged.

### Out-of-scope

- Runtime node LLM usage.
- Prompt templates.
- API endpoints.
- Frontend changes.
- Real live provider validation.

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

## TASK 011.4 - Prompt Templates and Structured Output Schemas

### Objective

Define bounded prompt templates and structured output schemas for initial
AI-assisted procurement runtime stages without wiring them into runtime
execution yet.

### Scope

- Add prompt template module or files for:
  - intake/requirement extraction
  - supplier or pricing analysis placeholder
  - legal/compliance analysis placeholder
  - finance/risk analysis placeholder
  - approval package preparation
- Add Pydantic v2 structured output schemas for each prompt area.
- Add prompt rendering helpers that bound input size and avoid hidden
  chain-of-thought requests.
- Add validation helpers for structured response parsing.
- Add tests for prompt rendering, size bounds, schema validation, invalid JSON,
  and unsafe/missing field behavior.

### Deliverables

- `backend/app/llm/prompts/` or equivalent
- `backend/app/llm/structured_outputs.py`
- `backend/app/tests/test_llm_prompts.py`
- `backend/app/tests/test_llm_structured_outputs.py`

### Acceptance Criteria

- Prompt templates are explicit and versionable.
- Structured outputs are validated with Pydantic v2.
- Prompt rendering is deterministic and bounded.
- Invalid provider output is rejected safely.
- No runtime nodes call LLMs yet.
- Calculator arithmetic remains out of LLM scope.

### Out-of-scope

- Runtime integration.
- RAG/document retrieval.
- Real pricing or policy engine.
- Frontend changes.
- New APIs.

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

## TASK 011.5 - Runtime Integration Behind Feature Flag

### Objective

Integrate LLM-assisted runtime behavior behind a feature flag while preserving
the existing deterministic runtime path as the default.

### Scope

- Add LLM-capable runtime node variants or injected node handlers.
- Use `LLMService`, not raw provider clients.
- Keep `LLM_RUNTIME_ENABLED=false` default behavior unchanged.
- Use fake provider for deterministic runtime integration tests.
- Validate structured outputs before updating runtime/workflow state.
- Append safe workflow events for LLM stage start, completion, validation
  failure, and provider failure.
- Preserve `WorkflowService` lifecycle transitions and `WorkflowEventService`
  event persistence.
- Keep `/run` route behavior stable unless the feature flag is enabled.

### Deliverables

- Runtime node/service integration changes scoped to `backend/app/runtime/`
- Tests for deterministic-disabled mode
- Tests for fake-provider LLM-enabled mode
- Tests for invalid structured output and provider failure
- README notes if useful

### Acceptance Criteria

- Existing deterministic runtime tests continue to pass.
- With LLM runtime disabled, `/run` behavior remains unchanged.
- With LLM runtime enabled and fake provider configured, runtime output remains
  deterministic.
- Runtime nodes depend on `LLMService`, not provider-specific clients.
- Provider failures persist safe failure evidence where practical.
- No raw prompts, secrets, provider payloads, or hidden reasoning are persisted.

### Out-of-scope

- `/resume` or approval continuation.
- Real RAG/document indexing.
- Real deterministic pricing tool implementation.
- Frontend provider UI.
- New public APIs.
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

## TASK 011.6 - Provider Documentation and Local Demo Guide

### Objective

Document provider configuration, local Ollama setup, fake/no-key demo behavior,
and troubleshooting without adding product behavior.

### Scope

- Update backend README with provider overview and safe env examples.
- Update `.env.example` notes if needed after implementation tasks.
- Document Groq setup.
- Document OpenRouter setup.
- Document Ollama local setup.
- Document Gemini setup.
- Document fake provider behavior and deterministic demo fallback.
- Document troubleshooting for missing keys, unavailable provider, timeouts,
  rate limits, invalid structured output, and disabled runtime mode.

### Deliverables

- `backend/README.md` provider section
- Optional `docs/demo/` or `docs/llm/` provider setup guide
- `.codex/HANDOFF.md` update

### Acceptance Criteria

- Documentation clearly says no real keys are committed.
- Documentation clearly says fake/deterministic behavior is the safe default.
- Provider setup examples cover Groq, OpenRouter, Ollama, and Gemini.
- Documentation does not claim RAG, `/resume`, frontend provider UI, token
  streaming, or production secret vault support exists.

### Out-of-scope

- Code changes except docs/copy.
- Provider management UI.
- Production secret management.
- Live provider validation.

### Validation Commands

```bash
git status --short
docker-compose config
git diff --check
```

## TASK 011.7 - LLM Provider Hardening and SPEC-011 Final Review

### Objective

Verify that SPEC-011 is complete, bounded, provider-portable, deterministic in
tests, safe for local demo use, and ready to close.

### Scope

- Review provider contracts, settings, provider clients, LLM service routing,
  prompt templates, structured outputs, runtime feature-flag integration,
  provider docs, and tests.
- Verify Groq, OpenRouter, Ollama, Gemini, and Fake provider support exists.
- Verify no tests require real network access or API keys.
- Verify deterministic demo behavior works with no keys configured.
- Verify runtime uses LLM service contracts and not raw provider clients.
- Verify provider errors, logs, and events are safe and bounded.
- Verify no RAG, frontend provider UI, `/resume`, token streaming, migrations,
  model changes, or public provider-management API was added.
- Record Harness durable evidence.

### Deliverables

- SPEC-011 final review result.
- Validation evidence.
- Harness story/trace evidence.
- Recommendation for next SPEC.

### Acceptance Criteria

- Provider abstraction supports Groq, OpenRouter, Ollama, Gemini, and Fake.
- Provider-specific logic is isolated behind provider modules.
- Runtime integration remains feature-flagged and deterministic by default.
- Tests use fake provider or mocked HTTP only.
- No real secrets are committed.
- No backend/frontend behavior changes beyond approved SPEC-011 scope are
  present.
- No migrations or model changes are added.

### Out-of-scope

- New product features during final review except tiny blocking fixes.
- Real RAG/document indexing.
- `/resume` or approval continuation.
- Frontend provider management.
- Production secret vault integration.
- Token streaming.

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
