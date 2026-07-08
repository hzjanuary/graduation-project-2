"""Workflow service foundation."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Workflow
from app.models.enums import WorkflowStatus
from app.repositories.workflows import WorkflowRepository
from app.workflows.exceptions import WorkflowNotFoundError, WorkflowStateMismatchError
from app.workflows.lifecycle import validate_transition
from app.workflows.schemas import WorkflowState, WorkflowStateCreate


class WorkflowService:
    """Workflow state use cases backed by the workflow repository."""

    def __init__(self, session: AsyncSession) -> None:
        self.workflow_repository = WorkflowRepository(session)

    async def create_workflow(
        self,
        state: WorkflowStateCreate,
        *,
        created_by_id: UUID | None = None,
    ) -> WorkflowState:
        """Create a persisted workflow record from typed state input."""
        workflow = self.workflow_repository.create(
            workflow_type=state.workflow_type.value,
            domain=state.domain,
            status=WorkflowStatus.CREATED,
            created_by_id=created_by_id,
            request_payload=dict(state.request),
            state_payload={},
        )
        await self.workflow_repository.session.flush()

        workflow_state = self._workflow_to_state(workflow)
        self.workflow_repository.update_state_payload(
            workflow,
            self._state_to_payload(workflow_state),
        )
        await self.workflow_repository.session.flush()
        return self._workflow_to_state(workflow)

    async def get_workflow(self, workflow_id: UUID) -> WorkflowState | None:
        """Return a workflow state by id, or None when not found."""
        workflow = await self.workflow_repository.get_by_id(workflow_id)
        if workflow is None:
            return None
        return self._workflow_to_state(workflow)

    async def list_workflows(
        self,
        *,
        status: WorkflowStatus | None = None,
        domain: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkflowState]:
        """Return workflow states with optional lightweight filters."""
        workflows = await self.workflow_repository.list_workflows(
            status=status,
            domain=domain,
            limit=limit,
            offset=offset,
        )
        return [self._workflow_to_state(workflow) for workflow in workflows]

    async def transition_workflow_status(
        self,
        workflow_id: UUID,
        to_status: WorkflowStatus,
    ) -> WorkflowState:
        """Transition a workflow status after lifecycle validation."""
        workflow = await self._get_required_workflow(workflow_id)
        validate_transition(workflow.status, to_status)

        self.workflow_repository.update_status(workflow, to_status)
        await self.workflow_repository.session.flush()

        workflow_state = self._workflow_to_state(workflow)
        self.workflow_repository.update_state_payload(
            workflow,
            self._state_to_payload(workflow_state),
        )
        await self.workflow_repository.session.flush()
        return self._workflow_to_state(workflow)

    async def update_workflow_state(
        self,
        workflow_id: UUID,
        state: WorkflowState,
    ) -> WorkflowState:
        """Update persisted state payload without changing workflow status."""
        workflow = await self._get_required_workflow(workflow_id)
        if state.workflow_id != str(workflow.id):
            raise WorkflowStateMismatchError(
                f"Workflow state id {state.workflow_id} does not match {workflow.id}",
            )
        if state.status is not workflow.status:
            raise WorkflowStateMismatchError(
                "Workflow state status must match persisted workflow status",
            )

        self.workflow_repository.update_state_payload(
            workflow,
            self._state_to_payload(state),
        )
        await self.workflow_repository.session.flush()
        return self._workflow_to_state(workflow)

    async def _get_required_workflow(self, workflow_id: UUID) -> Workflow:
        workflow = await self.workflow_repository.get_by_id(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} was not found")
        return workflow

    def _workflow_to_state(self, workflow: Workflow) -> WorkflowState:
        payload: dict[str, Any] = dict(workflow.state_payload)
        payload.update(
            {
                "workflow_id": str(workflow.id),
                "workflow_type": workflow.workflow_type,
                "domain": workflow.domain,
                "status": workflow.status,
                "request": dict(workflow.request_payload),
                "created_at": workflow.created_at,
                "updated_at": workflow.updated_at,
            },
        )
        return WorkflowState.model_validate(payload)

    def _state_to_payload(self, state: WorkflowState) -> dict[str, Any]:
        return state.model_dump(mode="json", exclude_none=True)
