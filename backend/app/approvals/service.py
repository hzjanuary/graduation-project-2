"""Backend approval decision service."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals.events import (
    APPROVAL_APPROVED_EVENT,
    APPROVAL_CHANGES_REQUESTED_EVENT,
    APPROVAL_REJECTED_EVENT,
)
from app.approvals.exceptions import (
    ApprovalPermissionDeniedError,
    DuplicateFinalApprovalDecisionError,
)
from app.approvals.lifecycle import (
    get_next_status_for_decision,
    get_resume_allowed_after_decision,
    has_final_approval_decision,
    is_final_approval_decision,
    validate_approval_decision_allowed,
)
from app.approvals.policies import can_submit_approval_decision
from app.approvals.schemas import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalDecisionType,
    ApprovalHistoryResponse,
    ApprovalRecord,
)
from app.auth.rbac import get_user_role_names
from app.models import User
from app.models.enums import WorkflowEventStatus
from app.workflows import (
    WorkflowEventCreate,
    WorkflowEventService,
    WorkflowNotFoundError,
    WorkflowService,
)
from app.workflows.audit import WorkflowAuditLogger

APPROVAL_DECISION_AUDIT_ACTION = "workflow.approval_decision_submitted"
APPROVAL_STATE_KEY = "approval_state"
APPROVAL_HISTORY_KEY = "approval_history"

_DECISION_EVENT_TYPES: Mapping[ApprovalDecisionType, str] = {
    ApprovalDecisionType.APPROVE: APPROVAL_APPROVED_EVENT,
    ApprovalDecisionType.REJECT: APPROVAL_REJECTED_EVENT,
    ApprovalDecisionType.REQUEST_CHANGES: APPROVAL_CHANGES_REQUESTED_EVENT,
}

_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "password",
    "provider_payload",
    "raw_provider_payload",
    "request_payload",
    "secret",
    "state_payload",
    "token",
)


class ApprovalService:
    """Approval use cases backed by existing workflow state, events, and audit logs."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        workflow_service: WorkflowService | None = None,
        workflow_event_service: WorkflowEventService | None = None,
    ) -> None:
        self.session = session
        self.workflow_service = workflow_service or WorkflowService(session)
        self.workflow_event_service = workflow_event_service or WorkflowEventService(
            session,
        )
        self.workflow_audit_logger = WorkflowAuditLogger(session)

    async def submit_approval_decision(
        self,
        workflow_id: UUID,
        request: ApprovalDecisionRequest,
        actor: User,
    ) -> ApprovalDecisionResponse:
        """Record one human approval decision for a workflow."""
        current_state = await self.workflow_service.get_workflow(workflow_id)
        if current_state is None:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} was not found")
        existing_records = _approval_records_from_payload(current_state.approval)
        actor_roles = tuple(sorted(get_user_role_names(actor)))
        if not can_submit_approval_decision(actor_roles, request.decision):
            raise ApprovalPermissionDeniedError(
                "Actor is not permitted to submit approval decisions.",
            )
        if is_final_approval_decision(request.decision) and has_final_approval_decision(
            existing_records,
        ):
            raise DuplicateFinalApprovalDecisionError(
                "Workflow already has a final approval decision.",
            )

        validate_approval_decision_allowed(
            status=current_state.status,
            decision=request.decision,
            records=existing_records,
        )

        previous_status = current_state.status
        next_status = get_next_status_for_decision(request.decision) or previous_status
        persisted_state = current_state
        if next_status is not previous_status:
            persisted_state = await self.workflow_service.transition_workflow_status(
                workflow_id,
                next_status,
                actor_type="user",
                actor_id=actor.id,
                reason=f"Approval decision: {request.decision.value}",
            )

        approval_record = ApprovalRecord(
            decision_id=uuid4(),
            workflow_id=workflow_id,
            decision=request.decision,
            actor_id=actor.id,
            actor_email=actor.email,
            actor_roles=actor_roles,
            comment=request.comment,
            decided_at=datetime.now(UTC),
            previous_status=previous_status,
            next_status=next_status,
            request_id=request.request_id,
            metadata=_sanitize_json_mapping(request.metadata),
        )
        updated_records = (*existing_records, approval_record)
        can_resume = get_resume_allowed_after_decision(
            status=next_status,
            records=updated_records,
        )
        updated_state = persisted_state.model_copy(
            update={
                "approval": _build_approval_payload(
                    persisted_state.approval,
                    records=updated_records,
                    can_resume=can_resume,
                ),
            },
        )
        await self.workflow_service.update_workflow_state(
            workflow_id,
            updated_state,
            actor_type="user",
            actor_id=actor.id,
            reason="Approval decision recorded.",
        )

        await self.workflow_event_service.append_event(
            WorkflowEventCreate(
                workflow_id=workflow_id,
                event_type=_DECISION_EVENT_TYPES[request.decision],
                actor_type="user",
                actor_id=actor.id,
                status=WorkflowEventStatus.COMPLETED,
                message=_event_message(request.decision),
                payload=_approval_event_payload(
                    approval_record,
                    can_resume=can_resume,
                ),
            ),
        )
        self.workflow_audit_logger.append_audit_log(
            action=APPROVAL_DECISION_AUDIT_ACTION,
            workflow_id=workflow_id,
            actor_type="user",
            actor_id=actor.id,
            resource_type="workflow",
            resource_id=workflow_id,
            payload=_approval_audit_payload(approval_record, can_resume=can_resume),
        )
        await self.session.flush()

        return ApprovalDecisionResponse(
            workflow_id=workflow_id,
            approval=approval_record,
            previous_status=previous_status,
            next_status=next_status,
            can_resume=can_resume,
            resume_recommended=can_resume,
        )

    async def get_approval_history(self, workflow_id: UUID) -> ApprovalHistoryResponse:
        """Return persisted approval history for one workflow."""
        state = await self.workflow_service.get_workflow(workflow_id)
        if state is None:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} was not found")
        records = _approval_records_from_payload(state.approval)
        can_resume = get_resume_allowed_after_decision(
            status=state.status,
            records=records,
        )
        return ApprovalHistoryResponse(
            workflow_id=workflow_id,
            approvals=records,
            has_final_decision=any(
                record.decision
                in (ApprovalDecisionType.APPROVE, ApprovalDecisionType.REJECT)
                for record in records
            ),
            can_resume=can_resume,
        )


def _approval_records_from_payload(
    payload: Mapping[str, Any],
) -> tuple[ApprovalRecord, ...]:
    raw_records = payload.get(APPROVAL_HISTORY_KEY, ())
    if not isinstance(raw_records, list | tuple):
        return ()
    return tuple(ApprovalRecord.model_validate(record) for record in raw_records)


def _build_approval_payload(
    existing_payload: Mapping[str, Any],
    *,
    records: tuple[ApprovalRecord, ...],
    can_resume: bool,
) -> dict[str, Any]:
    payload = dict(existing_payload)
    latest_record = records[-1]
    payload[APPROVAL_HISTORY_KEY] = [
        record.model_dump(mode="json") for record in records
    ]
    payload[APPROVAL_STATE_KEY] = {
        "latest_decision": latest_record.decision.value,
        "latest_decision_id": str(latest_record.decision_id),
        "latest_decided_at": latest_record.decided_at.isoformat(),
        "has_final_decision": latest_record.decision
        in (ApprovalDecisionType.APPROVE, ApprovalDecisionType.REJECT),
        "can_resume": can_resume,
    }
    return payload


def _approval_event_payload(
    record: ApprovalRecord,
    *,
    can_resume: bool,
) -> dict[str, Any]:
    payload = {
        "decision_id": str(record.decision_id),
        "decision": record.decision.value,
        "actor_id": str(record.actor_id),
        "actor_email": record.actor_email,
        "actor_roles": list(record.actor_roles),
        "previous_status": record.previous_status.value,
        "next_status": record.next_status.value if record.next_status else None,
        "can_resume": can_resume,
        "resume_recommended": can_resume,
    }
    if record.comment is not None:
        payload["comment"] = record.comment
    if record.request_id is not None:
        payload["request_id"] = record.request_id
    return payload


def _approval_audit_payload(
    record: ApprovalRecord,
    *,
    can_resume: bool,
) -> dict[str, Any]:
    payload = _approval_event_payload(record, can_resume=can_resume)
    payload["workflow_id"] = str(record.workflow_id)
    return payload


def _event_message(decision: ApprovalDecisionType) -> str:
    if decision is ApprovalDecisionType.APPROVE:
        return "Workflow approval accepted."
    if decision is ApprovalDecisionType.REJECT:
        return "Workflow approval rejected."
    return "Workflow changes requested."


def _sanitize_json_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: _sanitize_json_value(item)
        for key, item in value.items()
        if not _is_sensitive_key(key)
    }


def _sanitize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _sanitize_json_mapping(value)
    if isinstance(value, list):
        return [_sanitize_json_value(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)
