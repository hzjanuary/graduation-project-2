"""Tests for feature-flagged runtime RAG grounding."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import create_database_engine, create_session_factory
from app.knowledge.schemas import (
    KnowledgeCitation,
    KnowledgeDocumentSourceType,
    KnowledgeRetrievalResult,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.models.enums import WorkflowStatus
from app.runtime import (
    KNOWLEDGE_GROUNDING_COMPLETED_EVENT,
    KNOWLEDGE_GROUNDING_FAILED_EVENT,
    KNOWLEDGE_GROUNDING_STARTED_EVENT,
    RuntimeService,
    RuntimeStage,
)
from app.workflows import WorkflowEventService, WorkflowService, WorkflowStateCreate


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a rollback-only database session for RAG runtime tests."""
    engine = create_database_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            transaction = await session.begin()
            try:
                yield session
            finally:
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()


class FakeKnowledgeRetrievalService:
    """Retrieval service double recording runtime search calls."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[KnowledgeSearchRequest] = []

    async def search(
        self,
        request: KnowledgeSearchRequest,
    ) -> KnowledgeSearchResponse:
        self.calls.append(request)
        if self.fail:
            raise RuntimeError("vector provider secret should not leak")
        stage = _stage_for_query_label(request.query)
        return KnowledgeSearchResponse(
            query=request.query,
            results=(
                _retrieval_result(
                    stage=stage,
                    source_type=request.source_types[0],
                    score=0.91,
                ),
            ),
        )


class FailingKnowledgeRetrievalService:
    """Retrieval service double that fails if called."""

    calls: list[KnowledgeSearchRequest]

    def __init__(self) -> None:
        self.calls = []

    async def search(
        self,
        request: KnowledgeSearchRequest,
    ) -> KnowledgeSearchResponse:
        self.calls.append(request)
        raise AssertionError("RAG retrieval should not be called")


def _workflow_state_create() -> WorkflowStateCreate:
    return WorkflowStateCreate.model_validate(
        {
            "workflow_type": "procurement_quotation",
            "domain": "it_equipment",
            "request": {
                "raw_text": "Need 50 business laptops under the Acme agreement.",
                "source": "manual_text",
            },
        },
    )


async def _created_workflow_id(session: AsyncSession) -> UUID:
    workflow_service = WorkflowService(session)
    workflow = await workflow_service.create_workflow(_workflow_state_create())
    return UUID(workflow.workflow_id)


@pytest.mark.asyncio
async def test_rag_disabled_does_not_call_retrieval_or_emit_grounding_events(
    db_session: AsyncSession,
) -> None:
    workflow_service = WorkflowService(db_session)
    event_service = WorkflowEventService(db_session)
    workflow_id = await _created_workflow_id(db_session)
    retrieval_service = FailingKnowledgeRetrievalService()
    runtime_service = RuntimeService(
        workflow_service,
        event_service,
        rag_enabled=False,
        knowledge_retrieval_service=retrieval_service,
    )

    result = await runtime_service.run_workflow(workflow_id)
    events = await event_service.list_events_for_workflow(workflow_id)

    assert result.state.status is WorkflowStatus.WAITING_APPROVAL
    assert "rag" not in result.state.runtime_context
    assert retrieval_service.calls == []
    assert {
        event.event_type
        for event in events
        if event.event_type.startswith("knowledge.grounding")
    } == set()


@pytest.mark.asyncio
async def test_rag_enabled_retrieves_for_supported_stages_and_writes_citations(
    db_session: AsyncSession,
) -> None:
    workflow_service = WorkflowService(db_session)
    event_service = WorkflowEventService(db_session)
    workflow_id = await _created_workflow_id(db_session)
    retrieval_service = FakeKnowledgeRetrievalService()
    runtime_service = RuntimeService(
        workflow_service,
        event_service,
        rag_enabled=True,
        knowledge_retrieval_service=retrieval_service,
        rag_top_k=2,
    )

    result = await runtime_service.run_workflow(workflow_id)
    persisted_state = await workflow_service.get_workflow(workflow_id)
    events = await event_service.list_events_for_workflow(workflow_id)

    assert result.state.status is WorkflowStatus.WAITING_APPROVAL
    assert [call.top_k for call in retrieval_service.calls] == [2, 2, 2]
    assert [call.source_types for call in retrieval_service.calls] == [
        (
            KnowledgeDocumentSourceType.POLICY,
            KnowledgeDocumentSourceType.CONTRACT,
            KnowledgeDocumentSourceType.COMPLIANCE_CHECKLIST,
        ),
        (
            KnowledgeDocumentSourceType.PRICING,
            KnowledgeDocumentSourceType.SUPPLIER_PROFILE,
            KnowledgeDocumentSourceType.POLICY,
        ),
        (
            KnowledgeDocumentSourceType.POLICY,
            KnowledgeDocumentSourceType.CONTRACT,
            KnowledgeDocumentSourceType.PRICING,
            KnowledgeDocumentSourceType.COMPLIANCE_CHECKLIST,
        ),
    ]
    assert "rag" in result.state.runtime_context
    assert set(result.state.runtime_context["rag"]["stages"]) == {
        RuntimeStage.COMPLIANCE.value,
        RuntimeStage.VALIDATION.value,
        RuntimeStage.APPROVAL.value,
    }
    assert result.state.stage_outputs[RuntimeStage.COMPLIANCE]["evidence_count"] == 1
    citation = result.state.stage_outputs[RuntimeStage.COMPLIANCE]["evidence"][0]
    assert citation["document_title"] == "Demo Procurement Policy"
    assert citation["stage"] == RuntimeStage.COMPLIANCE.value
    assert "raw_vector_payload" not in json.dumps(result.state.model_dump(mode="json"))
    assert persisted_state is not None
    assert persisted_state.compliance["evidence_count"] == 1
    grounding_event_types = [
        event.event_type
        for event in events
        if event.event_type.startswith("knowledge.grounding")
    ]
    assert grounding_event_types == [
        KNOWLEDGE_GROUNDING_STARTED_EVENT,
        KNOWLEDGE_GROUNDING_COMPLETED_EVENT,
        KNOWLEDGE_GROUNDING_STARTED_EVENT,
        KNOWLEDGE_GROUNDING_COMPLETED_EVENT,
        KNOWLEDGE_GROUNDING_STARTED_EVENT,
        KNOWLEDGE_GROUNDING_COMPLETED_EVENT,
    ]
    completed_event = next(
        event
        for event in events
        if event.event_type == KNOWLEDGE_GROUNDING_COMPLETED_EVENT
    )
    assert completed_event.payload["result_count"] == 1
    assert completed_event.payload["citation_ids"] == ["citation:compliance-policy"]
    assert "excerpt" not in completed_event.payload


@pytest.mark.asyncio
async def test_rag_retrieval_failure_degrades_without_failing_runtime(
    db_session: AsyncSession,
) -> None:
    workflow_service = WorkflowService(db_session)
    event_service = WorkflowEventService(db_session)
    workflow_id = await _created_workflow_id(db_session)
    retrieval_service = FakeKnowledgeRetrievalService(fail=True)
    runtime_service = RuntimeService(
        workflow_service,
        event_service,
        rag_enabled=True,
        knowledge_retrieval_service=retrieval_service,
    )

    result = await runtime_service.run_workflow(workflow_id)
    events = await event_service.list_events_for_workflow(workflow_id)
    payload_text = json.dumps([event.payload for event in events], sort_keys=True)

    assert result.state.status is WorkflowStatus.WAITING_APPROVAL
    assert result.state.runtime_context["rag"]["stages"]["compliance"] == {
        "stage": "compliance",
        "status": "failed",
        "result_count": 0,
        "error_type": "RuntimeError",
    }
    assert KNOWLEDGE_GROUNDING_FAILED_EVENT in [event.event_type for event in events]
    assert "vector provider secret should not leak" not in payload_text


@pytest.mark.asyncio
async def test_rag_enabled_does_not_retrieve_during_resume_continuation(
    db_session: AsyncSession,
) -> None:
    workflow_service = WorkflowService(db_session)
    event_service = WorkflowEventService(db_session)
    created_state = await workflow_service.create_workflow(_workflow_state_create())
    workflow_id = UUID(created_state.workflow_id)
    for status in (
        WorkflowStatus.PLANNING,
        WorkflowStatus.RETRIEVING,
        WorkflowStatus.CALCULATING,
        WorkflowStatus.CHECKING_COMPLIANCE,
        WorkflowStatus.VALIDATING,
        WorkflowStatus.WAITING_APPROVAL,
        WorkflowStatus.APPROVED,
    ):
        await workflow_service.transition_workflow_status(workflow_id, status)
    approved_state = await workflow_service.get_workflow(workflow_id)
    assert approved_state is not None
    approved_state = approved_state.model_copy(
        update={
            "approval": {
                "approval_history": [
                    {
                        "decision_id": str(uuid4()),
                        "workflow_id": str(workflow_id),
                        "decision": "approve",
                        "comment": "Approved.",
                        "actor_id": str(uuid4()),
                        "actor_email": "manager@example.test",
                        "actor_roles": ["Manager"],
                        "decided_at": "2026-01-01T00:00:00Z",
                        "previous_status": "WAITING_APPROVAL",
                        "next_status": "APPROVED",
                        "request_id": None,
                        "metadata": {},
                    },
                ],
                "approval_state": {
                    "final_decision": "approve",
                    "can_resume": True,
                },
            },
        },
    )
    await workflow_service.update_workflow_state(workflow_id, approved_state)
    retrieval_service = FailingKnowledgeRetrievalService()
    runtime_service = RuntimeService(
        workflow_service,
        event_service,
        rag_enabled=True,
        knowledge_retrieval_service=retrieval_service,
    )

    result = await runtime_service.resume_workflow_after_approval(workflow_id)

    assert result.state.status is WorkflowStatus.COMPLETED
    assert retrieval_service.calls == []


def test_rag_settings_default_disabled_and_bounds() -> None:
    settings = Settings()

    assert settings.rag_enabled is False
    assert settings.rag_top_k == 3
    assert settings.rag_minimum_score == 0.0
    assert settings.rag_max_context_chars == 3000
    assert settings.rag_event_payload_max_chars == 2000


@pytest.mark.parametrize(
    ("env_name", "env_value"),
    [
        ("RAG_TOP_K", "0"),
        ("RAG_TOP_K", "21"),
        ("RAG_MINIMUM_SCORE", "-0.1"),
        ("RAG_MINIMUM_SCORE", "1.1"),
        ("RAG_MAX_CONTEXT_CHARS", "99"),
        ("RAG_MAX_CONTEXT_CHARS", "20001"),
        ("RAG_EVENT_PAYLOAD_MAX_CHARS", "99"),
        ("RAG_EVENT_PAYLOAD_MAX_CHARS", "10001"),
    ],
)
def test_rag_settings_validate_bounds(
    monkeypatch: pytest.MonkeyPatch,
    env_name: str,
    env_value: str,
) -> None:
    monkeypatch.setenv(env_name, env_value)

    with pytest.raises(ValidationError):
        Settings()


def _retrieval_result(
    *,
    stage: RuntimeStage,
    source_type: KnowledgeDocumentSourceType,
    score: float,
) -> KnowledgeRetrievalResult:
    chunk_id = f"{stage.value}-{source_type.value}"
    citation = KnowledgeCitation(
        citation_id=f"citation:{chunk_id}",
        document_id="demo-kb-procurement-policy",
        document_title="Demo Procurement Policy",
        source_type=source_type,
        excerpt="Manager approval is required for large discount exceptions.",
        relevance_score=score,
        citation_label="Demo Procurement Policy chunk 1",
    )
    return KnowledgeRetrievalResult(
        chunk_id=chunk_id,
        document_id="demo-kb-procurement-policy",
        chunk_text=citation.excerpt,
        score=score,
        source_type=source_type,
        document_title="Demo Procurement Policy",
        domain="procurement",
        citation=citation,
        metadata={"demo_seed": True},
    )


def _stage_for_query_label(query: str) -> RuntimeStage:
    if "finance risk" in query:
        return RuntimeStage.VALIDATION
    if "approval evidence" in query:
        return RuntimeStage.APPROVAL
    return RuntimeStage.COMPLIANCE
