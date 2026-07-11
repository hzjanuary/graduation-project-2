"""Runtime-facing workflow state contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import WorkflowStatus
from app.workflows.schemas import (
    WorkflowError,
    WorkflowStateMetadata,
    WorkflowStepState,
    WorkflowType,
)


class RuntimeStage(StrEnum):
    """Deterministic runtime stage names for the initial workflow graph."""

    PLANNER = "planner"
    RETRIEVAL = "retrieval"
    QUOTATION = "quotation"
    COMPLIANCE = "compliance"
    VALIDATION = "validation"
    APPROVAL = "approval"
    EMAIL_PREPARATION = "email_preparation"


RUNTIME_STAGES: tuple[RuntimeStage, ...] = tuple(RuntimeStage)


def runtime_stage_values() -> tuple[str, ...]:
    """Return runtime stage values in execution order."""
    return tuple(stage.value for stage in RUNTIME_STAGES)


class RuntimeWorkflowState(BaseModel):
    """JSON-compatible workflow state shape for future LangGraph execution."""

    model_config = ConfigDict(frozen=True)

    workflow_id: str = Field(min_length=1)
    workflow_type: WorkflowType
    domain: str | None = Field(default=None, min_length=1, max_length=100)
    status: WorkflowStatus
    request: dict[str, Any] = Field(default_factory=dict)
    metadata: WorkflowStateMetadata = Field(default_factory=WorkflowStateMetadata)
    customer: dict[str, Any] = Field(default_factory=dict)
    items: list[dict[str, Any]] = Field(default_factory=list)
    current_stage: RuntimeStage | None = None
    completed_stages: tuple[RuntimeStage, ...] = Field(default_factory=tuple)
    failed_stage: RuntimeStage | None = None
    runtime_context: dict[str, Any] = Field(default_factory=dict)
    stage_outputs: dict[RuntimeStage, dict[str, Any]] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[WorkflowStepState] = Field(default_factory=list)
    error: WorkflowError | None = None
    retry_count: int = Field(default=0, ge=0)
    events: list[dict[str, Any]] = Field(default_factory=list)


class RuntimeWorkflowResult(BaseModel):
    """Lightweight result contract for future runtime service execution."""

    model_config = ConfigDict(frozen=True)

    state: RuntimeWorkflowState
    completed: bool = False
    failed: bool = False
    message: str | None = Field(default=None, min_length=1)
