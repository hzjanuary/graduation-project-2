"""Workflow event model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import WorkflowEventStatus

if TYPE_CHECKING:
    from app.models.workflow import Workflow


class WorkflowEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Event emitted during workflow execution."""

    __tablename__ = "workflow_events"

    workflow_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actor_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=True,
    )
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[WorkflowEventStatus | None] = mapped_column(
        Enum(
            WorkflowEventStatus,
            native_enum=False,
            values_callable=lambda values: [item.value for item in values],
            length=32,
        ),
        nullable=True,
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    workflow: Mapped[Workflow] = relationship(
        back_populates="events",
        lazy="selectin",
    )
