"""Audit log repository helpers."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog
from app.repositories.crud import CRUDRepository


class AuditLogRepository(CRUDRepository[AuditLog]):
    """Database access for audit log records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuditLog)

    async def list_by_workflow_id(
        self,
        workflow_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[AuditLog]:
        """Return workflow audit logs in deterministic creation order."""
        statement = (
            select(AuditLog)
            .where(AuditLog.workflow_id == workflow_id)
            .order_by(AuditLog.created_at, AuditLog.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(statement)
        return result.all()

    def create_log(
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
        """Add an audit log record to the current session."""
        audit_log = AuditLog(
            workflow_id=workflow_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=dict(payload or {}),
        )
        return self.add(audit_log)
