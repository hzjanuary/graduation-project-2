"""Typed workflow state schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import WorkflowEventStatus, WorkflowStatus


class WorkflowType(StrEnum):
    """Supported workflow types for state payloads."""

    PROCUREMENT_QUOTATION = "procurement_quotation"


class WorkflowStateMetadata(BaseModel):
    """Implementation-agnostic workflow state metadata."""

    model_config = ConfigDict(frozen=True)

    state_version: int = Field(default=1, ge=1)
    created_by_id: str | None = Field(default=None, min_length=1)
    tags: dict[str, str] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)


class WorkflowError(BaseModel):
    """Structured workflow error details safe for state storage."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1)
    failed_step: str | None = Field(default=None, min_length=1, max_length=100)
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class WorkflowStepState(BaseModel):
    """State for one workflow step or runtime node."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=100)
    status: WorkflowStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    output: dict[str, Any] = Field(default_factory=dict)
    error: WorkflowError | None = None


class WorkflowLifecycleInfo(BaseModel):
    """Serializable workflow lifecycle status metadata."""

    model_config = ConfigDict(frozen=True)

    statuses: tuple[WorkflowStatus, ...]
    initial_status: WorkflowStatus
    terminal_statuses: tuple[WorkflowStatus, ...]


class WorkflowEventCreate(BaseModel):
    """Input schema for appending a workflow event."""

    model_config = ConfigDict(frozen=True)

    workflow_id: UUID
    event_type: str = Field(min_length=1, max_length=100)
    actor_type: str | None = Field(default=None, min_length=1, max_length=100)
    actor_id: UUID | None = None
    agent_name: str | None = Field(default=None, min_length=1, max_length=100)
    status: WorkflowEventStatus | None = None
    message: str | None = Field(default=None, min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowEventRead(WorkflowEventCreate):
    """Read schema for persisted workflow events."""

    event_id: UUID
    created_at: datetime
    updated_at: datetime | None = None


class WorkflowStateCreate(BaseModel):
    """Input schema for creating an initial workflow state envelope."""

    model_config = ConfigDict(frozen=True)

    workflow_type: WorkflowType
    domain: str | None = Field(default=None, min_length=1, max_length=100)
    request: dict[str, Any] = Field(default_factory=dict)
    metadata: WorkflowStateMetadata = Field(default_factory=WorkflowStateMetadata)


class WorkflowState(WorkflowStateCreate):
    """Typed workflow state envelope aligned with SPEC-005."""

    workflow_id: str = Field(min_length=1)
    status: WorkflowStatus = WorkflowStatus.CREATED
    customer: dict[str, Any] = Field(default_factory=dict)
    items: list[dict[str, Any]] = Field(default_factory=list)
    planner: dict[str, Any] = Field(default_factory=dict)
    retrieval: dict[str, Any] = Field(default_factory=dict)
    quotation: dict[str, Any] = Field(default_factory=dict)
    compliance: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)
    approval: dict[str, Any] = Field(default_factory=dict)
    email: dict[str, Any] = Field(default_factory=dict)
    current_step: str | None = Field(default=None, min_length=1, max_length=100)
    runtime_context: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[WorkflowStepState] = Field(default_factory=list)
    error: WorkflowError | None = None
    retry_count: int = Field(default=0, ge=0)
    events: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
