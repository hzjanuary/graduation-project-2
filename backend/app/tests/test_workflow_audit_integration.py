"""Tests for workflow service audit integration."""

from collections.abc import AsyncIterator, Sequence
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import create_database_engine, create_session_factory
from app.models import AuditLog
from app.models.enums import WorkflowEventStatus, WorkflowStatus
from app.workflows import (
    WORKFLOW_CREATED_ACTION,
    WORKFLOW_EVENT_APPENDED_ACTION,
    WORKFLOW_STATE_UPDATED_ACTION,
    WORKFLOW_STATUS_TRANSITIONED_ACTION,
    InvalidWorkflowTransitionError,
    WorkflowEventCreate,
    WorkflowEventService,
    WorkflowService,
    WorkflowStateCreate,
)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a rollback-only database session for workflow audit tests."""
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
    """Create typed workflow input for audit integration tests."""
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


async def list_audit_logs(
    db_session: AsyncSession,
    workflow_id: UUID,
) -> Sequence[AuditLog]:
    """Return audit logs for one workflow in deterministic order."""
    statement = (
        select(AuditLog)
        .where(AuditLog.workflow_id == workflow_id)
        .order_by(AuditLog.created_at, AuditLog.id)
    )
    return (await db_session.scalars(statement)).all()


@pytest.mark.asyncio
async def test_workflow_create_writes_audit_log(
    db_session: AsyncSession,
) -> None:
    service = WorkflowService(db_session)

    state = await service.create_workflow(build_workflow_state_create())
    workflow_id = UUID(state.workflow_id)
    audit_logs = await list_audit_logs(db_session, workflow_id)

    assert len(audit_logs) == 1
    audit_log = audit_logs[0]
    assert audit_log.action == WORKFLOW_CREATED_ACTION
    assert audit_log.workflow_id == workflow_id
    assert audit_log.resource_type == "workflow"
    assert audit_log.resource_id == workflow_id
    assert audit_log.payload == {
        "workflow_id": state.workflow_id,
        "workflow_type": "procurement_quotation",
        "domain": "it_equipment",
        "status": "CREATED",
    }


@pytest.mark.asyncio
async def test_workflow_transition_writes_audit_log(
    db_session: AsyncSession,
) -> None:
    service = WorkflowService(db_session)
    state = await service.create_workflow(build_workflow_state_create())
    workflow_id = UUID(state.workflow_id)
    actor_id = uuid4()

    await service.transition_workflow_status(
        workflow_id,
        WorkflowStatus.PLANNING,
        actor_type="user",
        actor_id=actor_id,
        reason="Start planning.",
    )
    audit_logs = await list_audit_logs(db_session, workflow_id)
    transition_audit = audit_logs[-1]

    assert [audit_log.action for audit_log in audit_logs] == [
        WORKFLOW_CREATED_ACTION,
        WORKFLOW_STATUS_TRANSITIONED_ACTION,
    ]
    assert transition_audit.actor_type == "user"
    assert transition_audit.actor_id == actor_id
    assert transition_audit.resource_type == "workflow"
    assert transition_audit.payload == {
        "workflow_id": state.workflow_id,
        "old_status": "CREATED",
        "new_status": "PLANNING",
        "reason": "Start planning.",
    }


@pytest.mark.asyncio
async def test_invalid_transition_does_not_write_audit_log(
    db_session: AsyncSession,
) -> None:
    service = WorkflowService(db_session)
    state = await service.create_workflow(build_workflow_state_create())
    workflow_id = UUID(state.workflow_id)

    with pytest.raises(InvalidWorkflowTransitionError):
        await service.transition_workflow_status(
            workflow_id,
            WorkflowStatus.COMPLETED,
        )

    audit_logs = await list_audit_logs(db_session, workflow_id)
    assert [audit_log.action for audit_log in audit_logs] == [
        WORKFLOW_CREATED_ACTION,
    ]


@pytest.mark.asyncio
async def test_workflow_state_update_writes_bounded_audit_log(
    db_session: AsyncSession,
) -> None:
    service = WorkflowService(db_session)
    state = await service.create_workflow(build_workflow_state_create())
    workflow_id = UUID(state.workflow_id)
    updated_state = state.model_copy(
        update={
            "current_step": "planner",
            "planner": {"plan_id": "plan-001"},
        },
    )

    await service.update_workflow_state(
        workflow_id,
        updated_state,
        actor_type="system",
        reason="Planner state merged.",
    )
    audit_logs = await list_audit_logs(db_session, workflow_id)
    state_audit = audit_logs[-1]

    assert state_audit.action == WORKFLOW_STATE_UPDATED_ACTION
    assert state_audit.actor_type == "system"
    assert state_audit.resource_type == "workflow"
    assert state_audit.payload == {
        "workflow_id": state.workflow_id,
        "status": "CREATED",
        "updated_fields": ["current_step", "planner"],
        "reason": "Planner state merged.",
    }
    assert "raw_text" not in state_audit.payload


@pytest.mark.asyncio
async def test_workflow_event_append_writes_audit_log(
    db_session: AsyncSession,
) -> None:
    workflow_service = WorkflowService(db_session)
    state = await workflow_service.create_workflow(build_workflow_state_create())
    workflow_id = UUID(state.workflow_id)
    event_service = WorkflowEventService(db_session)
    actor_id = uuid4()

    event = await event_service.append_event(
        WorkflowEventCreate(
            workflow_id=workflow_id,
            event_type="planner.started",
            actor_type="system",
            actor_id=actor_id,
            agent_name="planner",
            status=WorkflowEventStatus.STARTED,
            payload={"step": "planner"},
        ),
    )
    audit_logs = await list_audit_logs(db_session, workflow_id)
    event_audit = audit_logs[-1]

    assert event_audit.action == WORKFLOW_EVENT_APPENDED_ACTION
    assert event_audit.actor_type == "system"
    assert event_audit.actor_id == actor_id
    assert event_audit.resource_type == "workflow_event"
    assert event_audit.resource_id == event.event_id
    assert event_audit.payload == {
        "workflow_id": state.workflow_id,
        "event_id": str(event.event_id),
        "event_type": "planner.started",
        "agent_name": "planner",
    }
    assert "step" not in event_audit.payload
