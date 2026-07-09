"""Workflow event repository helpers."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkflowEvent
from app.models.enums import WorkflowEventStatus
from app.repositories import CRUDRepository


class WorkflowEventRepository(CRUDRepository[WorkflowEvent]):
    """Database access for workflow event records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WorkflowEvent)

    async def get_by_id(self, event_id: UUID) -> WorkflowEvent | None:
        """Return one workflow event by id."""
        return await self.get(event_id)

    async def list_by_workflow_id(
        self,
        workflow_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[WorkflowEvent]:
        """Return workflow events in deterministic creation order."""
        statement = (
            select(WorkflowEvent)
            .where(WorkflowEvent.workflow_id == workflow_id)
            .order_by(WorkflowEvent.created_at, WorkflowEvent.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(statement)
        return result.all()

    def create_event(
        self,
        *,
        workflow_id: UUID,
        event_type: str,
        actor_type: str | None = None,
        actor_id: UUID | None = None,
        agent_name: str | None = None,
        status: WorkflowEventStatus | None = None,
        message: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> WorkflowEvent:
        """Add a workflow event to the current session."""
        event = WorkflowEvent(
            workflow_id=workflow_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            agent_name=agent_name,
            status=status,
            message=message,
            payload=dict(payload or {}),
        )
        return self.add(event)
