"""API tests for workflow approval and resume boundary endpoints."""

from collections.abc import AsyncIterator, Sequence
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.approvals import (
    APPROVAL_APPROVED_EVENT,
    APPROVAL_CHANGES_REQUESTED_EVENT,
    APPROVAL_DECISION_AUDIT_ACTION,
    APPROVAL_REJECTED_EVENT,
    WORKFLOW_RESUME_FAILED_EVENT,
    WORKFLOW_RESUME_REQUESTED_EVENT,
    WORKFLOW_RESUMED_EVENT,
    ApprovalService,
)
from app.auth import create_access_token, hash_password
from app.auth.rbac import RoleName
from app.config import Settings, get_settings
from app.core.dependencies import (
    provide_approval_service,
    provide_db_session,
    provide_workflow_event_service,
)
from app.db import create_database_engine, create_session_factory
from app.main import create_app
from app.models import AuditLog, Role, User, Workflow, WorkflowEvent
from app.models.enums import WorkflowStatus
from app.workflows import (
    WorkflowEventService,
    WorkflowService,
    WorkflowState,
    WorkflowStateCreate,
)

TEST_EMAIL_PREFIX = "workflow-api-approval"
TEST_DOMAIN_PREFIX = "workflow-api-approval-domain"
TEST_ROLE_DESCRIPTION = "Workflow API approval endpoint test role"


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a database session and clean committed approval API test rows."""
    engine = create_database_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            try:
                yield session
            finally:
                await cleanup_test_records(session)
    finally:
        await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Provide an HTTP client with database and approval dependencies overridden."""
    app = create_app(Settings())

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    def override_approval_service() -> ApprovalService:
        workflow_service = WorkflowService(db_session)
        workflow_event_service = WorkflowEventService(db_session, publisher=None)
        return ApprovalService(
            db_session,
            workflow_service=workflow_service,
            workflow_event_service=workflow_event_service,
        )

    def override_workflow_event_service() -> WorkflowEventService:
        return WorkflowEventService(db_session, publisher=None)

    app.dependency_overrides[provide_db_session] = override_db_session
    app.dependency_overrides[provide_approval_service] = override_approval_service
    app.dependency_overrides[provide_workflow_event_service] = (
        override_workflow_event_service
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("role_name", [RoleName.ADMIN, RoleName.MANAGER])
async def test_admin_and_manager_can_approve_workflow(
    client: AsyncClient,
    db_session: AsyncSession,
    role_name: RoleName,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[role_name])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-approve-{role_name.value}",
    )

    response = await client.post(
        f"/api/v1/workflows/{workflow_id}/approval",
        headers=auth_headers(user),
        json={
            "decision": "approve",
            "comment": "Approved for customer response.",
            "request_id": "approval-api-approve",
        },
    )
    data = response.json()

    assert not db_session.in_transaction()

    workflow = await db_session.get(Workflow, workflow_id)
    events = await list_workflow_events(db_session, workflow_id)
    audit_logs = await list_audit_logs(db_session, workflow_id)

    assert response.status_code == 200
    assert data["workflow_id"] == str(workflow_id)
    assert data["approval"]["decision"] == "approve"
    assert data["previous_status"] == WorkflowStatus.WAITING_APPROVAL
    assert data["next_status"] == WorkflowStatus.APPROVED
    assert data["can_resume"] is True
    assert workflow is not None
    assert workflow.status is WorkflowStatus.APPROVED
    assert events[-1].event_type == APPROVAL_APPROVED_EVENT
    assert audit_logs[-1].action == APPROVAL_DECISION_AUDIT_ACTION


@pytest.mark.asyncio
async def test_manager_can_reject_workflow(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[RoleName.MANAGER])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-reject",
    )

    response = await client.post(
        f"/api/v1/workflows/{workflow_id}/approval",
        headers=auth_headers(user),
        json={
            "decision": "reject",
            "comment": "Compliance evidence is incomplete.",
        },
    )
    data = response.json()
    workflow = await db_session.get(Workflow, workflow_id)
    events = await list_workflow_events(db_session, workflow_id)

    assert response.status_code == 200
    assert data["approval"]["decision"] == "reject"
    assert data["next_status"] == WorkflowStatus.REJECTED
    assert data["can_resume"] is False
    assert workflow is not None
    assert workflow.status is WorkflowStatus.REJECTED
    assert events[-1].event_type == APPROVAL_REJECTED_EVENT


@pytest.mark.asyncio
async def test_request_changes_is_non_final_and_history_is_ordered(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[RoleName.ADMIN])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-request-changes",
    )

    changes_response = await client.post(
        f"/api/v1/workflows/{workflow_id}/approval",
        headers=auth_headers(user),
        json={
            "decision": "request_changes",
            "comment": "Add warranty comparison.",
        },
    )
    approve_response = await client.post(
        f"/api/v1/workflows/{workflow_id}/approval",
        headers=auth_headers(user),
        json={
            "decision": "approve",
            "comment": "Revision accepted.",
        },
    )
    history_response = await client.get(
        f"/api/v1/workflows/{workflow_id}/approval/history",
        headers=auth_headers(user),
    )
    history_data = history_response.json()
    events = await list_workflow_events(db_session, workflow_id)

    assert changes_response.status_code == 200
    assert changes_response.json()["next_status"] == WorkflowStatus.WAITING_APPROVAL
    assert approve_response.status_code == 200
    assert history_response.status_code == 200
    assert [item["decision"] for item in history_data["approvals"]] == [
        "request_changes",
        "approve",
    ]
    assert history_data["has_final_decision"] is True
    assert history_data["can_resume"] is True
    assert events[-2].event_type == APPROVAL_CHANGES_REQUESTED_EVENT
    assert events[-1].event_type == APPROVAL_APPROVED_EVENT


@pytest.mark.asyncio
async def test_approval_history_returns_empty_for_workflow_without_decisions(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[RoleName.VIEWER])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-empty-history",
    )

    response = await client.get(
        f"/api/v1/workflows/{workflow_id}/approval/history",
        headers=auth_headers(user),
    )
    data = response.json()

    assert response.status_code == 200
    assert data["workflow_id"] == str(workflow_id)
    assert data["approvals"] == []
    assert data["has_final_decision"] is False
    assert data["can_resume"] is False


@pytest.mark.asyncio
async def test_duplicate_final_approval_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[RoleName.MANAGER])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-duplicate",
    )
    await client.post(
        f"/api/v1/workflows/{workflow_id}/approval",
        headers=auth_headers(user),
        json={"decision": "approve", "comment": "Approved."},
    )

    response = await client.post(
        f"/api/v1/workflows/{workflow_id}/approval",
        headers=auth_headers(user),
        json={"decision": "reject", "comment": "Changed decision."},
    )
    data = response.json()

    assert response.status_code == 409
    assert data["detail"]["code"] == "approval_duplicate_final_decision"


@pytest.mark.asyncio
async def test_approval_for_non_waiting_workflow_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[RoleName.MANAGER])
    workflow = await create_workflow_directly(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-not-waiting",
    )

    response = await client.post(
        f"/api/v1/workflows/{workflow.workflow_id}/approval",
        headers=auth_headers(user),
        json={"decision": "approve", "comment": "Too early."},
    )
    data = response.json()

    assert response.status_code == 409
    assert data["detail"]["code"] == "approval_invalid_state"


@pytest.mark.asyncio
async def test_terminal_workflow_approval_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[RoleName.ADMIN])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-terminal",
    )
    workflow_service = WorkflowService(db_session)
    await workflow_service.transition_workflow_status(
        workflow_id,
        WorkflowStatus.CANCELLED,
    )
    await db_session.commit()

    response = await client.post(
        f"/api/v1/workflows/{workflow_id}/approval",
        headers=auth_headers(user),
        json={"decision": "approve", "comment": "Too late."},
    )
    data = response.json()

    assert response.status_code == 409
    assert data["detail"]["code"] == "approval_terminal_state"


@pytest.mark.asyncio
async def test_missing_workflow_approval_and_history_return_404(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[RoleName.ADMIN])
    missing_workflow_id = uuid4()

    approval_response = await client.post(
        f"/api/v1/workflows/{missing_workflow_id}/approval",
        headers=auth_headers(user),
        json={"decision": "approve", "comment": "Missing."},
    )
    history_response = await client.get(
        f"/api/v1/workflows/{missing_workflow_id}/approval/history",
        headers=auth_headers(user),
    )

    assert approval_response.status_code == 404
    assert approval_response.json()["detail"]["code"] == "workflow_not_found"
    assert history_response.status_code == 404
    assert history_response.json()["detail"]["code"] == "workflow_not_found"


@pytest.mark.asyncio
async def test_approval_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        f"/api/v1/workflows/{uuid4()}/approval",
        json={"decision": "approve", "comment": "No auth."},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role_name",
    [RoleName.SALES, RoleName.LEGAL, RoleName.FINANCE, RoleName.VIEWER],
)
async def test_non_approval_roles_are_forbidden(
    client: AsyncClient,
    db_session: AsyncSession,
    role_name: RoleName,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[role_name])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-forbidden-{role_name.value}",
    )

    response = await client.post(
        f"/api/v1/workflows/{workflow_id}/approval",
        headers=auth_headers(user),
        json={"decision": "approve", "comment": "Forbidden."},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role_name",
    [
        RoleName.ADMIN,
        RoleName.MANAGER,
        RoleName.SALES,
        RoleName.LEGAL,
        RoleName.FINANCE,
        RoleName.VIEWER,
    ],
)
async def test_read_roles_can_read_approval_history(
    client: AsyncClient,
    db_session: AsyncSession,
    role_name: RoleName,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[role_name])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-history-{role_name.value}",
    )

    response = await client.get(
        f"/api/v1/workflows/{workflow_id}/approval/history",
        headers=auth_headers(user),
    )

    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("role_name", [RoleName.ADMIN, RoleName.MANAGER])
async def test_resume_after_approval_requires_allowed_role_and_completes_workflow(
    client: AsyncClient,
    db_session: AsyncSession,
    role_name: RoleName,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[role_name])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-resume-{role_name.value}",
    )
    await client.post(
        f"/api/v1/workflows/{workflow_id}/approval",
        headers=auth_headers(user),
        json={"decision": "approve", "comment": "Approved for resume."},
    )

    response = await client.post(
        f"/api/v1/workflows/{workflow_id}/resume",
        headers=auth_headers(user),
        json={
            "request_id": "resume-api-success",
            "metadata": {
                "operator_note": "resume through API",
                "api_key": "must-not-persist",
            },
        },
    )
    data = response.json()
    workflow = await db_session.get(Workflow, workflow_id)
    events = await list_workflow_events(db_session, workflow_id)
    event_types = [event.event_type for event in events]

    assert response.status_code == 200
    assert data["workflow_id"] == str(workflow_id)
    assert data["previous_status"] == WorkflowStatus.APPROVED
    assert data["next_status"] == WorkflowStatus.COMPLETED
    assert data["resumed"] is True
    assert data["request_id"] == "resume-api-success"
    assert workflow is not None
    assert workflow.status is WorkflowStatus.COMPLETED
    email_state = cast(dict[str, Any], workflow.state_payload["email"])
    assert email_state["email_sent"] is False
    assert event_types[-4:] == [
        WORKFLOW_RESUME_REQUESTED_EVENT,
        "workflow.node.started",
        "workflow.node.completed",
        WORKFLOW_RESUMED_EVENT,
    ]
    assert events[-4].payload["metadata"] == {"operator_note": "resume through API"}
    assert "must-not-persist" not in str(workflow.state_payload)
    assert "api_key" not in str(events[-4].payload)


@pytest.mark.asyncio
async def test_resume_without_final_approval_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[RoleName.MANAGER])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-resume-no-approval",
    )

    response = await client.post(
        f"/api/v1/workflows/{workflow_id}/resume",
        headers=auth_headers(user),
        json={},
    )
    data = response.json()
    events = await list_workflow_events(db_session, workflow_id)

    assert response.status_code == 409
    assert data["detail"]["code"] == "workflow_resume_not_allowed"
    assert events[-1].event_type == WORKFLOW_RESUME_FAILED_EVENT


@pytest.mark.asyncio
async def test_resume_after_reject_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[RoleName.ADMIN])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-resume-rejected",
    )
    await client.post(
        f"/api/v1/workflows/{workflow_id}/approval",
        headers=auth_headers(user),
        json={"decision": "reject", "comment": "Do not continue."},
    )

    response = await client.post(
        f"/api/v1/workflows/{workflow_id}/resume",
        headers=auth_headers(user),
        json={},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "workflow_resume_not_allowed"


@pytest.mark.asyncio
async def test_resume_after_request_changes_only_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[RoleName.MANAGER])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-resume-changes",
    )
    await client.post(
        f"/api/v1/workflows/{workflow_id}/approval",
        headers=auth_headers(user),
        json={"decision": "request_changes", "comment": "Revise the package."},
    )

    response = await client.post(
        f"/api/v1/workflows/{workflow_id}/resume",
        headers=auth_headers(user),
        json={},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "workflow_resume_not_allowed"


@pytest.mark.asyncio
async def test_duplicate_resume_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[RoleName.ADMIN])
    workflow_id = await create_waiting_workflow(
        db_session,
        domain=f"{TEST_DOMAIN_PREFIX}-resume-duplicate",
    )
    await client.post(
        f"/api/v1/workflows/{workflow_id}/approval",
        headers=auth_headers(user),
        json={"decision": "approve", "comment": "Approved."},
    )
    first_response = await client.post(
        f"/api/v1/workflows/{workflow_id}/resume",
        headers=auth_headers(user),
        json={},
    )
    second_response = await client.post(
        f"/api/v1/workflows/{workflow_id}/resume",
        headers=auth_headers(user),
        json={},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json()["detail"]["code"] == "workflow_resume_not_allowed"


@pytest.mark.asyncio
async def test_missing_workflow_resume_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[RoleName.MANAGER])

    response = await client.post(
        f"/api/v1/workflows/{uuid4()}/resume",
        headers=auth_headers(user),
        json={},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "workflow_not_found"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role_name",
    [RoleName.SALES, RoleName.LEGAL, RoleName.FINANCE, RoleName.VIEWER],
)
async def test_resume_boundary_forbids_non_approval_roles(
    client: AsyncClient,
    db_session: AsyncSession,
    role_name: RoleName,
) -> None:
    user = await create_user_with_roles(db_session, role_names=[role_name])

    response = await client.post(
        f"/api/v1/workflows/{uuid4()}/resume",
        headers=auth_headers(user),
        json={},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_resume_boundary_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/workflows/{uuid4()}/resume", json={})

    assert response.status_code == 401


async def create_waiting_workflow(
    db_session: AsyncSession,
    *,
    domain: str,
) -> UUID:
    """Create a committed workflow and transition it to WAITING_APPROVAL."""
    workflow_service = WorkflowService(db_session)
    state = await workflow_service.create_workflow(
        WorkflowStateCreate.model_validate(workflow_create_payload(domain)),
    )
    workflow_id = UUID(state.workflow_id)
    for status in (
        WorkflowStatus.PLANNING,
        WorkflowStatus.RETRIEVING,
        WorkflowStatus.CALCULATING,
        WorkflowStatus.CHECKING_COMPLIANCE,
        WorkflowStatus.VALIDATING,
        WorkflowStatus.WAITING_APPROVAL,
    ):
        await workflow_service.transition_workflow_status(workflow_id, status)
    await db_session.commit()
    return workflow_id


async def create_workflow_directly(
    db_session: AsyncSession,
    *,
    domain: str,
) -> WorkflowState:
    """Create and commit a workflow through the service."""
    workflow_service = WorkflowService(db_session)
    workflow = await workflow_service.create_workflow(
        WorkflowStateCreate.model_validate(workflow_create_payload(domain)),
    )
    await db_session.commit()
    return workflow


async def create_user_with_roles(
    session: AsyncSession,
    *,
    role_names: list[RoleName],
) -> User:
    """Create and commit a user with the requested exact RBAC role names."""
    roles = [await ensure_role(session, role_name) for role_name in role_names]
    user = User(
        email=f"{TEST_EMAIL_PREFIX}-{uuid4()}@example.test",
        hashed_password=hash_password("not-used-in-approval-api-tests"),
        full_name="Workflow Approval API Test User",
        is_active=True,
        roles=roles,
    )
    session.add(user)
    await session.commit()
    return user


async def ensure_role(session: AsyncSession, role_name: RoleName) -> Role:
    """Return an existing role or create one for endpoint tests."""
    role = await session.scalar(select(Role).where(Role.name == role_name.value))
    if role is not None:
        return role

    role = Role(
        name=role_name.value,
        description=TEST_ROLE_DESCRIPTION,
    )
    session.add(role)
    await session.flush()
    return role


def auth_headers(user: User) -> dict[str, str]:
    """Return bearer token authorization headers for a user."""
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def workflow_create_payload(domain: str) -> dict[str, object]:
    """Return a valid workflow creation request payload."""
    return {
        "workflow_type": "procurement_quotation",
        "domain": domain,
        "request": {
            "raw_text": "Need 50 business laptops.",
            "source": "manual_text",
            "uploaded_document_ids": [],
        },
    }


async def list_workflow_events(
    db_session: AsyncSession,
    workflow_id: UUID,
) -> Sequence[WorkflowEvent]:
    """Return workflow events in deterministic order."""
    statement = (
        select(WorkflowEvent)
        .where(WorkflowEvent.workflow_id == workflow_id)
        .order_by(WorkflowEvent.created_at, WorkflowEvent.id)
    )
    return (await db_session.scalars(statement)).all()


async def list_audit_logs(
    db_session: AsyncSession,
    workflow_id: UUID,
) -> Sequence[AuditLog]:
    """Return workflow audit logs in deterministic order."""
    statement = (
        select(AuditLog)
        .where(AuditLog.workflow_id == workflow_id)
        .order_by(AuditLog.created_at, AuditLog.id)
    )
    return (await db_session.scalars(statement)).all()


async def cleanup_test_records(session: AsyncSession) -> None:
    """Remove rows committed by approval API endpoint tests."""
    if session.in_transaction():
        await session.rollback()

    workflow_ids = select(Workflow.id).where(
        Workflow.domain.like(f"{TEST_DOMAIN_PREFIX}%"),
    )
    test_user_ids = select(User.id).where(User.email.like(f"{TEST_EMAIL_PREFIX}-%"))

    await session.execute(
        delete(AuditLog).where(AuditLog.workflow_id.in_(workflow_ids)),
    )
    await session.execute(delete(AuditLog).where(AuditLog.actor_id.in_(test_user_ids)))
    await session.execute(
        delete(Workflow).where(Workflow.domain.like(f"{TEST_DOMAIN_PREFIX}%")),
    )
    await session.execute(delete(User).where(User.email.like(f"{TEST_EMAIL_PREFIX}-%")))
    await session.execute(delete(Role).where(Role.description == TEST_ROLE_DESCRIPTION))
    await session.commit()
