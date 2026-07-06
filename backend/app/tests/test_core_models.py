"""Tests for Phase 1 core SQLAlchemy models."""

from typing import cast

from sqlalchemy import ForeignKeyConstraint, Table
from sqlalchemy.orm import RelationshipProperty

from app.db import Base
from app.models import AuditLog, Role, User, Workflow, WorkflowEvent, user_roles
from app.models.enums import WorkflowEventStatus, WorkflowStatus


def test_core_model_tables_are_registered_in_base_metadata() -> None:
    assert {
        "users",
        "roles",
        "user_roles",
        "workflows",
        "workflow_events",
        "audit_logs",
    }.issubset(Base.metadata.tables)


def test_user_model_columns_and_role_relationship() -> None:
    table = cast(Table, User.__table__)

    assert table.name == "users"
    assert table.c.email.unique is True
    assert table.c.email.index is True
    assert table.c.email.nullable is False
    assert table.c.hashed_password.nullable is False
    assert table.c.full_name.nullable is True
    assert table.c.is_active.default is not None
    assert table.c.is_superuser.default is not None
    assert isinstance(User.roles.property, RelationshipProperty)
    assert User.roles.property.secondary is user_roles
    assert User.roles.property.back_populates == "users"


def test_role_model_columns_and_user_relationship() -> None:
    table = cast(Table, Role.__table__)

    assert table.name == "roles"
    assert table.c.name.unique is True
    assert table.c.name.index is True
    assert table.c.name.nullable is False
    assert table.c.description.nullable is True
    assert isinstance(Role.users.property, RelationshipProperty)
    assert Role.users.property.secondary is user_roles
    assert Role.users.property.back_populates == "roles"


def test_user_roles_association_table_shape() -> None:
    assert user_roles.name == "user_roles"
    assert {column.name for column in user_roles.primary_key.columns} == {
        "user_id",
        "role_id",
    }

    foreign_keys = {
        foreign_key.target_fullname for foreign_key in user_roles.foreign_keys
    }
    assert foreign_keys == {"users.id", "roles.id"}


def test_workflow_model_columns_and_relationships() -> None:
    table = cast(Table, Workflow.__table__)

    assert table.name == "workflows"
    assert table.c.workflow_type.nullable is False
    assert table.c.domain.nullable is True
    assert table.c.status.nullable is False
    assert table.c.created_by_id.nullable is True
    assert table.c.request_payload.nullable is False
    assert table.c.state_payload.nullable is False
    assert table.c.deleted_at.nullable is True
    assert isinstance(Workflow.events.property, RelationshipProperty)
    assert Workflow.events.property.back_populates == "workflow"
    assert isinstance(Workflow.audit_logs.property, RelationshipProperty)
    assert Workflow.audit_logs.property.back_populates == "workflow"


def test_workflow_event_model_columns_and_relationship() -> None:
    table = cast(Table, WorkflowEvent.__table__)

    assert table.name == "workflow_events"
    assert table.c.workflow_id.nullable is False
    assert table.c.event_type.nullable is False
    assert table.c.actor_type.nullable is True
    assert table.c.actor_id.nullable is True
    assert table.c.agent_name.nullable is True
    assert table.c.status.nullable is True
    assert table.c.message.nullable is True
    assert table.c.payload.nullable is False
    assert isinstance(WorkflowEvent.workflow.property, RelationshipProperty)
    assert WorkflowEvent.workflow.property.back_populates == "events"


def test_audit_log_model_columns_and_relationship() -> None:
    table = cast(Table, AuditLog.__table__)

    assert table.name == "audit_logs"
    assert table.c.workflow_id.nullable is True
    assert table.c.actor_type.nullable is True
    assert table.c.actor_id.nullable is True
    assert table.c.action.nullable is False
    assert table.c.resource_type.nullable is True
    assert table.c.resource_id.nullable is True
    assert table.c.payload.nullable is False
    assert isinstance(AuditLog.workflow.property, RelationshipProperty)
    assert AuditLog.workflow.property.back_populates == "audit_logs"


def test_model_foreign_key_constraints() -> None:
    workflow_table = cast(Table, Workflow.__table__)
    workflow_event_table = cast(Table, WorkflowEvent.__table__)
    audit_log_table = cast(Table, AuditLog.__table__)

    workflow_foreign_keys = foreign_key_targets(
        workflow_table.foreign_key_constraints,
    )
    workflow_event_foreign_keys = foreign_key_targets(
        workflow_event_table.foreign_key_constraints,
    )
    audit_log_foreign_keys = foreign_key_targets(
        audit_log_table.foreign_key_constraints,
    )

    assert workflow_foreign_keys == {"users.id"}
    assert workflow_event_foreign_keys == {"workflows.id"}
    assert audit_log_foreign_keys == {"workflows.id"}


def test_core_model_enums_are_stable() -> None:
    assert WorkflowStatus.CREATED.value == "CREATED"
    assert WorkflowStatus.WAITING_APPROVAL.value == "WAITING_APPROVAL"
    assert WorkflowStatus.COMPLETED.value == "COMPLETED"
    assert WorkflowEventStatus.STARTED.value == "STARTED"
    assert WorkflowEventStatus.FAILED.value == "FAILED"


def foreign_key_targets(
    constraints: set[ForeignKeyConstraint],
) -> set[str]:
    """Return foreign key targets for assertions."""
    return {
        element.target_fullname
        for constraint in constraints
        for element in constraint.elements
    }
