"""Stable database enum values for core models."""

from enum import StrEnum


class WorkflowStatus(StrEnum):
    """Workflow lifecycle states stored in the database."""

    CREATED = "CREATED"
    PLANNING = "PLANNING"
    RETRIEVING = "RETRIEVING"
    CALCULATING = "CALCULATING"
    CHECKING_COMPLIANCE = "CHECKING_COMPLIANCE"
    VALIDATING = "VALIDATING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    GENERATING_EMAIL = "GENERATING_EMAIL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowEventStatus(StrEnum):
    """Coarse event execution states."""

    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
