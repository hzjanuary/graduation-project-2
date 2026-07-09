"""Workflow audit log helpers."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog
from app.models.enums import WorkflowStatus
from app.repositories.audit_logs import AuditLogRepository

WORKFLOW_CREATED_ACTION = "workflow.created"
WORKFLOW_STATUS_TRANSITIONED_ACTION = "workflow.status_transitioned"
WORKFLOW_STATE_UPDATED_ACTION = "workflow.state_updated"
WORKFLOW_EVENT_APPENDED_ACTION = "workflow.event_appended"


class WorkflowAuditLogger:
    """Append service-level workflow audit records."""

    def __init__(self, session: AsyncSession) -> None:
        self.audit_log_repository = AuditLogRepository(session)

    def audit_workflow_created(
        self,
        *,
        workflow_id: UUID,
        workflow_type: str,
        domain: str | None,
        actor_user_id: UUID | None = None,
    ) -> AuditLog:
        """Record workflow creation audit evidence."""
        return self.append_audit_log(
            action=WORKFLOW_CREATED_ACTION,
            workflow_id=workflow_id,
            actor_type="user" if actor_user_id is not None else None,
            actor_id=actor_user_id,
            resource_type="workflow",
            resource_id=workflow_id,
            payload={
                "workflow_id": str(workflow_id),
                "workflow_type": workflow_type,
                "domain": domain,
                "status": WorkflowStatus.CREATED.value,
            },
        )

    def audit_workflow_status_transitioned(
        self,
        *,
        workflow_id: UUID,
        old_status: WorkflowStatus,
        new_status: WorkflowStatus,
        actor_type: str | None = None,
        actor_id: UUID | None = None,
        reason: str | None = None,
    ) -> AuditLog:
        """Record a valid workflow status transition."""
        payload: dict[str, Any] = {
            "workflow_id": str(workflow_id),
            "old_status": old_status.value,
            "new_status": new_status.value,
        }
        if reason is not None:
            payload["reason"] = reason

        return self.append_audit_log(
            action=WORKFLOW_STATUS_TRANSITIONED_ACTION,
            workflow_id=workflow_id,
            actor_type=actor_type,
            actor_id=actor_id,
            resource_type="workflow",
            resource_id=workflow_id,
            payload=payload,
        )

    def audit_workflow_state_updated(
        self,
        *,
        workflow_id: UUID,
        status: WorkflowStatus,
        actor_type: str | None = None,
        actor_id: UUID | None = None,
        reason: str | None = None,
        updated_fields: list[str] | None = None,
    ) -> AuditLog:
        """Record a workflow state payload update."""
        payload: dict[str, Any] = {
            "workflow_id": str(workflow_id),
            "status": status.value,
            "updated_fields": list(updated_fields or []),
        }
        if reason is not None:
            payload["reason"] = reason

        return self.append_audit_log(
            action=WORKFLOW_STATE_UPDATED_ACTION,
            workflow_id=workflow_id,
            actor_type=actor_type,
            actor_id=actor_id,
            resource_type="workflow",
            resource_id=workflow_id,
            payload=payload,
        )

    def audit_workflow_event_appended(
        self,
        *,
        workflow_id: UUID,
        event_id: UUID,
        event_type: str,
        actor_type: str | None = None,
        actor_id: UUID | None = None,
        agent_name: str | None = None,
    ) -> AuditLog:
        """Record that a workflow event was appended."""
        payload: dict[str, Any] = {
            "workflow_id": str(workflow_id),
            "event_id": str(event_id),
            "event_type": event_type,
        }
        if agent_name is not None:
            payload["agent_name"] = agent_name

        return self.append_audit_log(
            action=WORKFLOW_EVENT_APPENDED_ACTION,
            workflow_id=workflow_id,
            actor_type=actor_type,
            actor_id=actor_id,
            resource_type="workflow_event",
            resource_id=event_id,
            payload=payload,
        )

    def append_audit_log(
        self,
        *,
        action: str,
        workflow_id: UUID | None = None,
        actor_type: str | None = None,
        actor_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Append one audit log without flushing or committing."""
        return self.audit_log_repository.create_log(
            action=action,
            workflow_id=workflow_id,
            actor_type=actor_type,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
        )
