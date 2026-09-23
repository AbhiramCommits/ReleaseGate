import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.enums import ChangeStage, RiskLevel, Role
from app.models import Approval, AuditEvent, ChangeRequest, User


def headers_for(user: User) -> dict[str, str]:
    from app.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


async def _setup_submitted(client: AsyncClient, requester: User, reviewer: User) -> str:
    created = await client.post(
        "/api/v1/change-requests",
        json={
            "title": "Atomicity probe",
            "description": "Used to verify transaction rollback.",
            "vehicle_program": "Voyager",
            "subsystem": "Chassis",
            "risk_level": "MEDIUM",
        },
        headers=headers_for(requester),
    )
    cr_id = created.json()["id"]
    await client.post(
        f"/api/v1/change-requests/{cr_id}/transitions",
        json={"action": "SUBMIT"},
        headers=headers_for(requester),
    )
    return cr_id


async def test_transition_endpoint_atomic_when_audit_insert_fails(monkeypatch):
    import app.repositories.change_requests as repository
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        from app.database import SessionLocal

        with SessionLocal() as db:
            requester = User(
                email="requester-atomic@test.dev",
                full_name="Requester",
                role=Role.REQUESTER,
                hashed_password="x",
            )
            reviewer = User(
                email="reviewer-atomic@test.dev",
                full_name="Reviewer",
                role=Role.REVIEWER,
                hashed_password="x",
            )
            db.add_all([requester, reviewer])
            db.commit()

        cr_id = await _setup_submitted(client, requester, reviewer)

        def exploding_audit_event(*args, **kwargs):
            raise RuntimeError("forced audit_event insert failure")

        monkeypatch.setattr(repository, "AuditEvent", exploding_audit_event)

        response = await client.post(
            f"/api/v1/change-requests/{cr_id}/transitions",
            json={"action": "APPROVE"},
            headers=headers_for(reviewer),
        )
        assert response.status_code == 500
        assert response.headers.get("x-request-id")

        with SessionLocal() as db:
            cr = db.get(ChangeRequest, uuid.UUID(cr_id))
            assert cr is not None
            assert cr.current_stage is ChangeStage.SUBMITTED

            approval_count = db.scalar(
                select(func.count())
                .select_from(Approval)
                .where(Approval.change_request_id == uuid.UUID(cr_id))
            )
            assert approval_count == 0

            audit_count = db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(AuditEvent.change_request_id == uuid.UUID(cr_id))
            )
            assert audit_count == 2


def test_transition_rolls_back_when_commit_fails(monkeypatch):
    from datetime import UTC, datetime

    from app.database import SessionLocal
    from app.repositories import change_requests as repository
    from app.workflow import WorkflowAction

    with SessionLocal() as session:
        requester = User(
            email="requester-commit@test.dev",
            full_name="Requester",
            role=Role.REQUESTER,
            hashed_password="x",
        )
        reviewer = User(
            email="reviewer-commit@test.dev",
            full_name="Reviewer",
            role=Role.REVIEWER,
            hashed_password="x",
        )
        session.add_all([requester, reviewer])
        session.commit()

        now = datetime.now(UTC)
        cr = ChangeRequest(
            ticket_key="ECR-9500",
            title="Commit failure probe",
            description="probe",
            vehicle_program="P",
            subsystem="S",
            risk_level=RiskLevel.MEDIUM,
            current_stage=ChangeStage.SUBMITTED,
            requester_id=requester.id,
            created_at=now,
            updated_at=now,
        )
        session.add(cr)
        session.flush()
        session.add_all(
            [
                AuditEvent(
                    change_request_id=cr.id,
                    actor_id=requester.id,
                    from_stage=None,
                    to_stage=ChangeStage.DRAFT,
                    action="CREATED",
                    meta={},
                    created_at=now,
                ),
                AuditEvent(
                    change_request_id=cr.id,
                    actor_id=requester.id,
                    from_stage=ChangeStage.DRAFT,
                    to_stage=ChangeStage.SUBMITTED,
                    action="SUBMITTED",
                    meta={},
                    created_at=now,
                ),
            ]
        )
        session.commit()
        cr_id = cr.id
        reviewer_id = reviewer.id

    class ExplodingCommit(Exception):
        pass

    with SessionLocal() as session:
        cr = session.get(ChangeRequest, cr_id)
        reviewer = session.get(User, reviewer_id)

        def failing_commit():
            raise ExplodingCommit("forced commit failure")

        monkeypatch.setattr(session, "commit", failing_commit)

        with pytest.raises(ExplodingCommit):
            repository.transition_change_request(
                session, cr, reviewer, WorkflowAction.APPROVE, None
            )

    with SessionLocal() as verify:
        stored = verify.get(ChangeRequest, cr_id)
        assert stored is not None
        assert stored.current_stage is ChangeStage.SUBMITTED
        approvals = verify.scalar(
            select(func.count()).select_from(Approval).where(Approval.change_request_id == cr_id)
        )
        assert approvals == 0
        events = verify.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.change_request_id == cr_id)
        )
        assert events == 2
