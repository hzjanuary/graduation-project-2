"""Tests for workflow transition rules."""

from typing import cast

import pytest

from app.models.enums import WorkflowStatus
from app.workflows import (
    ALLOWED_WORKFLOW_TRANSITIONS,
    InvalidWorkflowTransitionError,
    can_transition,
    get_allowed_transitions,
    is_terminal_status,
    list_status_values,
    validate_transition,
)

BASELINE_TRANSITIONS = (
    (WorkflowStatus.CREATED, WorkflowStatus.PLANNING),
    (WorkflowStatus.PLANNING, WorkflowStatus.RETRIEVING),
    (WorkflowStatus.RETRIEVING, WorkflowStatus.CALCULATING),
    (WorkflowStatus.CALCULATING, WorkflowStatus.CHECKING_COMPLIANCE),
    (WorkflowStatus.CHECKING_COMPLIANCE, WorkflowStatus.VALIDATING),
    (WorkflowStatus.VALIDATING, WorkflowStatus.WAITING_APPROVAL),
    (WorkflowStatus.VALIDATING, WorkflowStatus.FAILED),
    (WorkflowStatus.WAITING_APPROVAL, WorkflowStatus.APPROVED),
    (WorkflowStatus.WAITING_APPROVAL, WorkflowStatus.REJECTED),
    (WorkflowStatus.APPROVED, WorkflowStatus.GENERATING_EMAIL),
    (WorkflowStatus.GENERATING_EMAIL, WorkflowStatus.COMPLETED),
)

FAILURE_TRANSITIONS = (
    (WorkflowStatus.PLANNING, WorkflowStatus.FAILED),
    (WorkflowStatus.RETRIEVING, WorkflowStatus.FAILED),
    (WorkflowStatus.CALCULATING, WorkflowStatus.FAILED),
    (WorkflowStatus.CHECKING_COMPLIANCE, WorkflowStatus.FAILED),
    (WorkflowStatus.VALIDATING, WorkflowStatus.FAILED),
    (WorkflowStatus.GENERATING_EMAIL, WorkflowStatus.FAILED),
)

CANCELLATION_TRANSITIONS = (
    (WorkflowStatus.CREATED, WorkflowStatus.CANCELLED),
    (WorkflowStatus.PLANNING, WorkflowStatus.CANCELLED),
    (WorkflowStatus.RETRIEVING, WorkflowStatus.CANCELLED),
    (WorkflowStatus.CALCULATING, WorkflowStatus.CANCELLED),
    (WorkflowStatus.CHECKING_COMPLIANCE, WorkflowStatus.CANCELLED),
    (WorkflowStatus.VALIDATING, WorkflowStatus.CANCELLED),
    (WorkflowStatus.WAITING_APPROVAL, WorkflowStatus.CANCELLED),
)


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    BASELINE_TRANSITIONS + FAILURE_TRANSITIONS + CANCELLATION_TRANSITIONS,
)
def test_allowed_transitions_return_true_and_validate(
    from_status: WorkflowStatus,
    to_status: WorkflowStatus,
) -> None:
    assert can_transition(from_status, to_status) is True

    validate_transition(from_status, to_status)


def test_transition_map_covers_every_workflow_status() -> None:
    assert set(ALLOWED_WORKFLOW_TRANSITIONS) == set(WorkflowStatus)


def test_get_allowed_transitions_returns_copy() -> None:
    allowed = get_allowed_transitions(WorkflowStatus.CREATED)

    assert allowed == {
        WorkflowStatus.PLANNING,
        WorkflowStatus.CANCELLED,
    }

    allowed.clear()

    assert get_allowed_transitions(WorkflowStatus.CREATED) == {
        WorkflowStatus.PLANNING,
        WorkflowStatus.CANCELLED,
    }


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    (
        (WorkflowStatus.CREATED, WorkflowStatus.COMPLETED),
        (WorkflowStatus.CREATED, WorkflowStatus.RETRIEVING),
        (WorkflowStatus.WAITING_APPROVAL, WorkflowStatus.GENERATING_EMAIL),
        (WorkflowStatus.APPROVED, WorkflowStatus.COMPLETED),
        (WorkflowStatus.GENERATING_EMAIL, WorkflowStatus.APPROVED),
    ),
)
def test_invalid_transitions_return_false_and_raise(
    from_status: WorkflowStatus,
    to_status: WorkflowStatus,
) -> None:
    assert can_transition(from_status, to_status) is False

    with pytest.raises(InvalidWorkflowTransitionError) as exc_info:
        validate_transition(from_status, to_status)

    assert exc_info.value.from_status is from_status
    assert exc_info.value.to_status is to_status


@pytest.mark.parametrize(
    "terminal_status",
    (
        WorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
        WorkflowStatus.REJECTED,
    ),
)
def test_terminal_statuses_cannot_transition(terminal_status: WorkflowStatus) -> None:
    assert is_terminal_status(terminal_status) is True
    assert get_allowed_transitions(terminal_status) == set()

    for to_status in WorkflowStatus:
        assert can_transition(terminal_status, to_status) is False


def test_invalid_transition_error_lists_allowed_transitions() -> None:
    with pytest.raises(InvalidWorkflowTransitionError) as exc_info:
        validate_transition(WorkflowStatus.CREATED, WorkflowStatus.COMPLETED)

    assert exc_info.value.allowed_statuses == {
        WorkflowStatus.PLANNING,
        WorkflowStatus.CANCELLED,
    }
    assert "CREATED" in str(exc_info.value)
    assert "COMPLETED" in str(exc_info.value)
    assert "PLANNING" in str(exc_info.value)


def test_list_status_values_returns_json_friendly_values() -> None:
    assert list_status_values() == [status.value for status in WorkflowStatus]


def test_unknown_status_inputs_are_rejected() -> None:
    invalid_status = cast(WorkflowStatus, "CREATED")

    with pytest.raises(TypeError, match="from_status must be a WorkflowStatus"):
        can_transition(invalid_status, WorkflowStatus.PLANNING)

    with pytest.raises(TypeError, match="status must be a WorkflowStatus"):
        get_allowed_transitions(invalid_status)
