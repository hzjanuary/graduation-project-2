"""Workflow model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import WorkflowStatus

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.user import User
    from app.models.workflow_event import WorkflowEvent


class Workflow(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Persisted workflow state envelope."""

    __tablename__ = "workflows"

    workflow_type: Mapped[str] = mapped_column(String(100), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(
            WorkflowStatus,
            native_enum=False,
            values_callable=lambda values: [item.value for item in values],
            length=64,
        ),
        default=WorkflowStatus.CREATED,
        nullable=False,
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    state_payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    created_by: Mapped[User | None] = relationship(lazy="selectin")
    events: Mapped[list[WorkflowEvent]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
