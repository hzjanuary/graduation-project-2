"""Workflow repository helpers."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Workflow
from app.models.enums import WorkflowStatus
from app.repositories import CRUDRepository


class WorkflowRepository(CRUDRepository[Workflow]):
    """Database access for workflow state records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Workflow)

    async def get_by_id(self, workflow_id: UUID) -> Workflow | None:
        """Return one workflow by id."""
        return await self.get(workflow_id)

    async def list_workflows(
        self,
        *,
        status: WorkflowStatus | None = None,
        domain: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Workflow]:
        """Return workflow records with optional lightweight filters."""
        statement = select(Workflow).where(Workflow.deleted_at.is_(None))
        if status is not None:
            statement = statement.where(Workflow.status == status)
        if domain is not None:
            statement = statement.where(Workflow.domain == domain)
        statement = statement.order_by(Workflow.created_at, Workflow.id).limit(limit)
        statement = statement.offset(offset)
        result = await self.session.scalars(statement)
        return result.all()

    def create(
        self,
        *,
        workflow_type: str,
        domain: str | None,
        status: WorkflowStatus,
        created_by_id: UUID | None,
        request_payload: dict[str, object],
        state_payload: dict[str, object],
    ) -> Workflow:
        """Add a workflow record to the current session."""
        workflow = Workflow(
            workflow_type=workflow_type,
            domain=domain,
            status=status,
            created_by_id=created_by_id,
            request_payload=request_payload,
            state_payload=state_payload,
        )
        return self.add(workflow)

    def update_status(
        self,
        workflow: Workflow,
        status: WorkflowStatus,
    ) -> Workflow:
        """Set workflow status without flushing or committing."""
        workflow.status = status
        return workflow

    def update_state_payload(
        self,
        workflow: Workflow,
        state_payload: dict[str, Any],
    ) -> Workflow:
        """Set workflow state payload without flushing or committing."""
        workflow.state_payload = dict(state_payload)
        return workflow
