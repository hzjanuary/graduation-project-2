"""Tests for workflow state schemas and lifecycle metadata."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.enums import WorkflowStatus
from app.workflows import (
    INITIAL_WORKFLOW_STATUS,
    TERMINAL_WORKFLOW_STATUSES,
    WORKFLOW_STATUSES,
    WorkflowError,
    WorkflowState,
    WorkflowStateCreate,
    WorkflowStepState,
    WorkflowType,
    get_workflow_lifecycle_info,
    is_terminal_status,
    workflow_status_values,
)


def test_workflow_state_validates_minimal_spec_shape() -> None:
    created_at = datetime(2026, 7, 8, tzinfo=UTC)

    state = WorkflowState(
        workflow_id="workflow-001",
        workflow_type=WorkflowType.PROCUREMENT_QUOTATION,
        domain="it_equipment",
        status=WorkflowStatus.CREATED,
        request={
            "raw_text": "Need 50 business laptops.",
            "source": "manual_text",
            "uploaded_document_ids": [],
        },
        created_at=created_at,
        updated_at=created_at,
    )

    assert state.workflow_id == "workflow-001"
    assert state.workflow_type is WorkflowType.PROCUREMENT_QUOTATION
    assert state.status is WorkflowStatus.CREATED
    assert state.metadata.state_version == 1
    assert state.retry_count == 0
    assert state.events == []
    assert state.created_at == created_at


def test_workflow_state_serializes_to_json_compatible_values() -> None:
    state = WorkflowState.model_validate(
        {
            "workflow_id": "workflow-001",
            "workflow_type": "procurement_quotation",
            "status": "WAITING_APPROVAL",
            "request": {"raw_text": "Need 50 business laptops."},
        },
    )

    data = state.model_dump(mode="json")

    assert data["workflow_type"] == "procurement_quotation"
    assert data["status"] == "WAITING_APPROVAL"
    assert data["metadata"]["state_version"] == 1


def test_workflow_state_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        WorkflowState.model_validate(
            {
                "workflow_id": "workflow-001",
                "workflow_type": "procurement_quotation",
                "status": "UNKNOWN",
            },
        )


def test_workflow_state_rejects_invalid_workflow_type() -> None:
    with pytest.raises(ValidationError):
        WorkflowState.model_validate(
            {
                "workflow_id": "workflow-001",
                "workflow_type": "unknown",
                "status": WorkflowStatus.CREATED,
            },
        )


def test_workflow_state_rejects_negative_retry_count() -> None:
    with pytest.raises(ValidationError):
        WorkflowState.model_validate(
            {
                "workflow_id": "workflow-001",
                "workflow_type": "procurement_quotation",
                "retry_count": -1,
            },
        )


def test_workflow_state_create_schema_parses_initial_payload() -> None:
    payload = WorkflowStateCreate.model_validate(
        {
            "workflow_type": "procurement_quotation",
            "domain": "software_subscription",
            "request": {"raw_text": "Need annual licenses."},
        },
    )

    assert payload.workflow_type is WorkflowType.PROCUREMENT_QUOTATION
    assert payload.domain == "software_subscription"
    assert payload.metadata.state_version == 1


def test_workflow_step_state_and_error_are_structured() -> None:
    error = WorkflowError(
        code="RETRIEVAL_TIMEOUT",
        message="Retrieval timed out.",
        failed_step="retrieval",
        retryable=True,
        details={"timeout_seconds": 30},
    )

    step = WorkflowStepState(
        name="retrieval",
        status=WorkflowStatus.FAILED,
        duration_ms=30000,
        error=error,
    )

    assert step.name == "retrieval"
    assert step.status is WorkflowStatus.FAILED
    assert step.error == error
    assert step.output == {}


def test_lifecycle_statuses_reuse_existing_workflow_status_enum() -> None:
    assert INITIAL_WORKFLOW_STATUS is WorkflowStatus.CREATED
    assert tuple(WorkflowStatus) == WORKFLOW_STATUSES
    assert workflow_status_values() == tuple(status.value for status in WorkflowStatus)


def test_terminal_status_helper_matches_spec() -> None:
    assert TERMINAL_WORKFLOW_STATUSES == (
        WorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
        WorkflowStatus.REJECTED,
    )
    assert is_terminal_status(WorkflowStatus.COMPLETED) is True
    assert is_terminal_status(WorkflowStatus.FAILED) is True
    assert is_terminal_status(WorkflowStatus.CANCELLED) is True
    assert is_terminal_status(WorkflowStatus.REJECTED) is True
    assert is_terminal_status(WorkflowStatus.CREATED) is False
    assert is_terminal_status(WorkflowStatus.WAITING_APPROVAL) is False


def test_lifecycle_info_is_serializable() -> None:
    info = get_workflow_lifecycle_info()
    data = info.model_dump(mode="json")

    assert data["initial_status"] == "CREATED"
    assert "WAITING_APPROVAL" in data["statuses"]
    assert data["terminal_statuses"] == [
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        "REJECTED",
    ]
