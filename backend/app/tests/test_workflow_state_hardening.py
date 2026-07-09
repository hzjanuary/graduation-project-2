"""Hardening tests for SPEC-005 workflow state behavior."""

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import create_database_engine, create_session_factory
from app.models import AuditLog, Workflow, WorkflowEvent
from app.models.enums import WorkflowEventStatus
from app.workflows import (
    WorkflowEventCreate,
    WorkflowEventService,
    WorkflowService,
    WorkflowState,
    WorkflowStateCreate,
    WorkflowType,
)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a rollback-only database session for hardening tests."""
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


def build_workflow_state_create() -> WorkflowStateCreate:
    """Create typed workflow input for hardening tests."""
    return WorkflowStateCreate.model_validate(
        {
            "workflow_type": "procurement_quotation",
            "domain": "it_equipment",
            "request": {
                "raw_text": "Need 50 business laptops.",
                "source": "manual_text",
            },
        },
    )


async def count_audit_logs_for_workflow(
    db_session: AsyncSession,
    workflow_id: UUID,
) -> int:
    """Return audit log count for one workflow."""
    statement = select(func.count()).where(AuditLog.workflow_id == workflow_id)
    return (await db_session.scalar(statement)) or 0


def test_workflow_state_schema_is_frozen() -> None:
    state = WorkflowState(
        workflow_id="workflow-001",
        workflow_type=WorkflowType.PROCUREMENT_QUOTATION,
    )

    with pytest.raises(ValidationError):
        state.workflow_id = "workflow-002"


@pytest.mark.asyncio
async def test_event_list_for_existing_workflow_can_be_empty(
    db_session: AsyncSession,
) -> None:
    workflow_service = WorkflowService(db_session)
    state = await workflow_service.create_workflow(build_workflow_state_create())
    event_service = WorkflowEventService(db_session)

    events = await event_service.list_events_for_workflow(UUID(state.workflow_id))

    assert events == []


@pytest.mark.asyncio
async def test_workflow_services_leave_transaction_rollback_to_caller() -> None:
    engine = create_database_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)
    workflow_id: UUID
    event_id: UUID
    try:
        async with session_factory() as session:
            transaction = await session.begin()
            workflow_service = WorkflowService(session)
            event_service = WorkflowEventService(session)

            state = await workflow_service.create_workflow(
                build_workflow_state_create(),
            )
            workflow_id = UUID(state.workflow_id)
            event = await event_service.append_event(
                WorkflowEventCreate(
                    workflow_id=workflow_id,
                    event_type="workflow.created",
                    status=WorkflowEventStatus.COMPLETED,
                    payload={"sequence": 1},
                ),
            )
            event_id = event.event_id

            assert await session.get(Workflow, workflow_id) is not None
            assert await session.get(WorkflowEvent, event_id) is not None
            assert await count_audit_logs_for_workflow(session, workflow_id) >= 2

            await transaction.rollback()

        async with session_factory() as verification_session:
            assert await verification_session.get(Workflow, workflow_id) is None
            assert await verification_session.get(WorkflowEvent, event_id) is None
            assert (
                await count_audit_logs_for_workflow(
                    verification_session,
                    workflow_id,
                )
                == 0
            )
    finally:
        await engine.dispose()
