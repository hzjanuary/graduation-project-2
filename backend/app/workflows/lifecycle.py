"""Workflow lifecycle status metadata helpers."""

from collections.abc import Mapping

from app.models.enums import WorkflowStatus
from app.workflows.exceptions import InvalidWorkflowTransitionError
from app.workflows.schemas import WorkflowLifecycleInfo

INITIAL_WORKFLOW_STATUS = WorkflowStatus.CREATED

WORKFLOW_STATUSES: tuple[WorkflowStatus, ...] = tuple(WorkflowStatus)

TERMINAL_WORKFLOW_STATUSES: tuple[WorkflowStatus, ...] = (
    WorkflowStatus.COMPLETED,
    WorkflowStatus.FAILED,
    WorkflowStatus.CANCELLED,
    WorkflowStatus.REJECTED,
)

ALLOWED_WORKFLOW_TRANSITIONS: Mapping[WorkflowStatus, frozenset[WorkflowStatus]] = {
    WorkflowStatus.CREATED: frozenset(
        {
            WorkflowStatus.PLANNING,
            WorkflowStatus.CANCELLED,
        },
    ),
    WorkflowStatus.PLANNING: frozenset(
        {
            WorkflowStatus.RETRIEVING,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        },
    ),
    WorkflowStatus.RETRIEVING: frozenset(
        {
            WorkflowStatus.CALCULATING,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        },
    ),
    WorkflowStatus.CALCULATING: frozenset(
        {
            WorkflowStatus.CHECKING_COMPLIANCE,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        },
    ),
    WorkflowStatus.CHECKING_COMPLIANCE: frozenset(
        {
            WorkflowStatus.VALIDATING,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        },
    ),
    WorkflowStatus.VALIDATING: frozenset(
        {
            WorkflowStatus.WAITING_APPROVAL,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        },
    ),
    WorkflowStatus.WAITING_APPROVAL: frozenset(
        {
            WorkflowStatus.APPROVED,
            WorkflowStatus.REJECTED,
            WorkflowStatus.CANCELLED,
        },
    ),
    WorkflowStatus.APPROVED: frozenset({WorkflowStatus.GENERATING_EMAIL}),
    WorkflowStatus.GENERATING_EMAIL: frozenset(
        {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
        },
    ),
    WorkflowStatus.COMPLETED: frozenset(),
    WorkflowStatus.FAILED: frozenset(),
    WorkflowStatus.CANCELLED: frozenset(),
    WorkflowStatus.REJECTED: frozenset(),
}


def is_terminal_status(status: WorkflowStatus) -> bool:
    """Return whether a workflow status is terminal."""
    _require_workflow_status(status, "status")
    return status in TERMINAL_WORKFLOW_STATUSES


def workflow_status_values() -> tuple[str, ...]:
    """Return approved workflow status values in enum order."""
    return tuple(status.value for status in WORKFLOW_STATUSES)


def list_status_values() -> list[str]:
    """Return approved workflow status values as a JSON-friendly list."""
    return list(workflow_status_values())


def get_allowed_transitions(status: WorkflowStatus) -> set[WorkflowStatus]:
    """Return allowed next statuses for a workflow status."""
    _require_workflow_status(status, "status")
    return set(ALLOWED_WORKFLOW_TRANSITIONS[status])


def can_transition(
    from_status: WorkflowStatus,
    to_status: WorkflowStatus,
) -> bool:
    """Return whether a workflow status transition is allowed."""
    _require_workflow_status(from_status, "from_status")
    _require_workflow_status(to_status, "to_status")
    return to_status in ALLOWED_WORKFLOW_TRANSITIONS[from_status]


def validate_transition(
    from_status: WorkflowStatus,
    to_status: WorkflowStatus,
) -> None:
    """Raise when a workflow status transition is not allowed."""
    if can_transition(from_status, to_status):
        return

    raise InvalidWorkflowTransitionError(
        from_status=from_status,
        to_status=to_status,
        allowed_statuses=get_allowed_transitions(from_status),
    )


def get_workflow_lifecycle_info() -> WorkflowLifecycleInfo:
    """Return serializable workflow lifecycle metadata."""
    return WorkflowLifecycleInfo(
        statuses=WORKFLOW_STATUSES,
        initial_status=INITIAL_WORKFLOW_STATUS,
        terminal_statuses=TERMINAL_WORKFLOW_STATUSES,
    )


def _require_workflow_status(value: WorkflowStatus, field_name: str) -> None:
    if not isinstance(value, WorkflowStatus):
        raise TypeError(f"{field_name} must be a WorkflowStatus")
