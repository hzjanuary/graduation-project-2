"""Workflow lifecycle exceptions."""

from app.models.enums import WorkflowStatus


class WorkflowLifecycleError(Exception):
    """Base class for workflow lifecycle errors."""


class WorkflowNotFoundError(WorkflowLifecycleError):
    """Raised when a workflow record cannot be found."""


class WorkflowEventNotFoundError(WorkflowLifecycleError):
    """Raised when a workflow event record cannot be found."""


class WorkflowStateMismatchError(WorkflowLifecycleError):
    """Raised when provided state does not match the persisted workflow."""


class InvalidWorkflowTransitionError(WorkflowLifecycleError):
    """Raised when a workflow status transition is not allowed."""

    def __init__(
        self,
        *,
        from_status: WorkflowStatus,
        to_status: WorkflowStatus,
        allowed_statuses: set[WorkflowStatus],
    ) -> None:
        allowed_values = sorted(status.value for status in allowed_statuses)
        message = (
            f"Invalid workflow transition from {from_status.value} "
            f"to {to_status.value}. Allowed transitions: {allowed_values}"
        )
        super().__init__(message)
        self.from_status = from_status
        self.to_status = to_status
        self.allowed_statuses = allowed_statuses
