"""Tests for workflow event append/read service."""

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import create_database_engine, create_session_factory
from app.models import WorkflowEvent
from app.models.enums import WorkflowEventStatus
from app.workflows import (
    WorkflowEventCreate,
    WorkflowEventNotFoundError,
    WorkflowEventService,
    WorkflowNotFoundError,
    WorkflowService,
    WorkflowStateCreate,
)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a rollback-only database session for workflow event tests."""
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
    """Create typed workflow input for event service tests."""
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


async def create_workflow(db_session: AsyncSession) -> UUID:
    """Create a workflow and return its id."""
    workflow_service = WorkflowService(db_session)
    state = await workflow_service.create_workflow(build_workflow_state_create())
    return UUID(state.workflow_id)


@pytest.mark.asyncio
async def test_workflow_event_service_appends_event(
    db_session: AsyncSession,
) -> None:
    workflow_id = await create_workflow(db_session)
    service = WorkflowEventService(db_session)

    event = await service.append_event(
        WorkflowEventCreate(
            workflow_id=workflow_id,
            event_type="workflow.created",
            actor_type="user",
            actor_id=uuid4(),
            status=WorkflowEventStatus.COMPLETED,
            message="Workflow created.",
            payload={"source": "manual_text", "sequence": 1},
        ),
    )
    persisted_event = await db_session.get(WorkflowEvent, event.event_id)

    assert persisted_event is not None
    assert persisted_event.workflow_id == workflow_id
    assert persisted_event.event_type == "workflow.created"
    assert persisted_event.payload == {"source": "manual_text", "sequence": 1}
    assert event.status is WorkflowEventStatus.COMPLETED
    assert event.created_at is not None


@pytest.mark.asyncio
async def test_workflow_event_service_lists_events_in_creation_order(
    db_session: AsyncSession,
) -> None:
    workflow_id = await create_workflow(db_session)
    service = WorkflowEventService(db_session)

    await service.append_event(
        WorkflowEventCreate(
            workflow_id=workflow_id,
            event_type="workflow.created",
            status=WorkflowEventStatus.COMPLETED,
            payload={"sequence": 1},
        ),
    )
    await service.append_event(
        WorkflowEventCreate(
            workflow_id=workflow_id,
            event_type="planner.started",
            agent_name="planner",
            status=WorkflowEventStatus.STARTED,
            payload={"sequence": 2},
        ),
    )
    await service.append_event(
        WorkflowEventCreate(
            workflow_id=workflow_id,
            event_type="planner.completed",
            agent_name="planner",
            status=WorkflowEventStatus.COMPLETED,
            payload={"sequence": 3},
        ),
    )

    events = await service.list_events_for_workflow(workflow_id)

    assert [event.event_type for event in events] == [
        "workflow.created",
        "planner.started",
        "planner.completed",
    ]
    assert [event.payload["sequence"] for event in events] == [1, 2, 3]


@pytest.mark.asyncio
async def test_workflow_event_service_list_supports_limit_and_offset(
    db_session: AsyncSession,
) -> None:
    workflow_id = await create_workflow(db_session)
    service = WorkflowEventService(db_session)
    for sequence in range(3):
        await service.append_event(
            WorkflowEventCreate(
                workflow_id=workflow_id,
                event_type=f"event.{sequence}",
                payload={"sequence": sequence},
            ),
        )

    events = await service.list_events_for_workflow(workflow_id, limit=1, offset=1)

    assert len(events) == 1
    assert events[0].event_type == "event.1"


@pytest.mark.asyncio
async def test_workflow_event_service_get_event(
    db_session: AsyncSession,
) -> None:
    workflow_id = await create_workflow(db_session)
    service = WorkflowEventService(db_session)
    event = await service.append_event(
        WorkflowEventCreate(
            workflow_id=workflow_id,
            event_type="workflow.created",
        ),
    )

    found_event = await service.get_event(event.event_id)

    assert found_event is not None
    assert found_event.event_id == event.event_id
    assert found_event.workflow_id == workflow_id


@pytest.mark.asyncio
async def test_workflow_event_service_returns_none_for_missing_event(
    db_session: AsyncSession,
) -> None:
    service = WorkflowEventService(db_session)

    assert await service.get_event(uuid4()) is None


@pytest.mark.asyncio
async def test_workflow_event_service_raises_for_required_missing_event(
    db_session: AsyncSession,
) -> None:
    service = WorkflowEventService(db_session)

    with pytest.raises(WorkflowEventNotFoundError):
        await service.get_required_event(uuid4())


@pytest.mark.asyncio
async def test_workflow_event_service_rejects_missing_workflow(
    db_session: AsyncSession,
) -> None:
    service = WorkflowEventService(db_session)
    missing_workflow_id = uuid4()

    with pytest.raises(WorkflowNotFoundError):
        await service.append_event(
            WorkflowEventCreate(
                workflow_id=missing_workflow_id,
                event_type="workflow.created",
            ),
        )

    with pytest.raises(WorkflowNotFoundError):
        await service.list_events_for_workflow(missing_workflow_id)


def test_workflow_event_create_rejects_invalid_status() -> None:
    with pytest.raises(ValueError):
        WorkflowEventCreate.model_validate(
            {
                "workflow_id": str(uuid4()),
                "event_type": "planner.started",
                "status": "NOT_A_STATUS",
            },
        )
