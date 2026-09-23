import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.enums import ChangeStage, RiskLevel, Role
from app.models import Approval, AuditEvent, ChangeRequest, User
from app.security import create_access_token


@pytest.fixture
async def client():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest.fixture
def requester(make_user) -> User:
    return make_user(Role.REQUESTER)


@pytest.fixture
def reviewer(make_user) -> User:
    return make_user(Role.REVIEWER)


@pytest.fixture
def admin(make_user) -> User:
    return make_user(Role.ADMIN)


def token_for(user: User) -> str:
    return create_access_token(str(user.id))


def headers_for(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(user)}"}


def create_payload(**overrides) -> dict:
    payload = {
        "title": "Test change request",
        "description": "Detailed description.",
        "vehicle_program": "Voyager",
        "subsystem": "Chassis",
        "risk_level": "MEDIUM",
    }
    payload.update(overrides)
    return payload


async def transition(
    client: AsyncClient, user: User, cr_id: str, action: str, comment: str | None = None
):
    body = {"action": action}
    if comment is not None:
        body["comment"] = comment
    return await client.post(
        f"/api/v1/change-requests/{cr_id}/transitions",
        json=body,
        headers=headers_for(user),
    )


class TestAuthEndpoints:
    async def test_healthz_reports_ok(self, client):
        response = await client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "db": "ok"}

    async def test_login_returns_access_token(self, client, requester):
        response = await client.post(
            "/auth/login",
            json={"email": requester.email, "password": "password123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]

    async def test_login_wrong_password_rejected(self, client, requester):
        response = await client.post(
            "/auth/login",
            json={"email": requester.email, "password": "wrong"},
        )
        assert response.status_code == 401

    async def test_login_unknown_email_rejected(self, client):
        response = await client.post(
            "/auth/login",
            json={"email": "nobody@test.dev", "password": "password123"},
        )
        assert response.status_code == 401

    async def test_missing_token_returns_401(self, client):
        response = await client.get("/api/v1/change-requests")
        assert response.status_code == 401

    async def test_invalid_token_returns_401(self, client):
        response = await client.get(
            "/api/v1/change-requests",
            headers={"Authorization": "Bearer not-a-token"},
        )
        assert response.status_code == 401


class TestChangeRequestLifecycle:
    async def test_full_happy_path_draft_to_approved(self, client, requester, reviewer, admin):
        created = await client.post(
            "/api/v1/change-requests",
            json=create_payload(),
            headers=headers_for(requester),
        )
        assert created.status_code == 201
        cr = created.json()
        assert cr["current_stage"] == "DRAFT"
        assert cr["ticket_key"].startswith("ECR-")
        cr_id = cr["id"]

        patched = await client.patch(
            f"/api/v1/change-requests/{cr_id}",
            json={"title": "Updated title"},
            headers=headers_for(requester),
        )
        assert patched.status_code == 200
        assert patched.json()["title"] == "Updated title"

        step = await transition(client, requester, cr_id, "SUBMIT")
        assert step.status_code == 200
        assert step.json()["current_stage"] == "SUBMITTED"

        step = await transition(client, reviewer, cr_id, "APPROVE", "into eng")
        assert step.status_code == 200
        assert step.json()["current_stage"] == "ENGINEERING_REVIEW"

        step = await transition(client, reviewer, cr_id, "APPROVE")
        assert step.status_code == 200
        assert step.json()["current_stage"] == "MANUFACTURING_REVIEW"

        step = await transition(client, admin, cr_id, "APPROVE", "ship it")
        assert step.status_code == 200
        assert step.json()["current_stage"] == "APPROVED"

        audit = await client.get(
            f"/api/v1/change-requests/{cr_id}/audit", headers=headers_for(requester)
        )
        assert audit.status_code == 200
        actions = [event["action"] for event in audit.json()["items"]]
        assert actions == [
            "CREATED",
            "SUBMITTED",
            "MOVED_TO_ENGINEERING_REVIEW",
            "MOVED_TO_MANUFACTURING_REVIEW",
            "APPROVED",
        ]

    async def test_request_changes_loops_back_to_draft(self, client, requester, reviewer):
        created = await client.post(
            "/api/v1/change-requests",
            json=create_payload(),
            headers=headers_for(requester),
        )
        cr_id = created.json()["id"]

        await transition(client, requester, cr_id, "SUBMIT")
        await transition(client, reviewer, cr_id, "APPROVE")
        back = await transition(client, reviewer, cr_id, "REQUEST_CHANGES", "fix it")
        assert back.status_code == 200
        assert back.json()["current_stage"] == "DRAFT"

        patched = await client.patch(
            f"/api/v1/change-requests/{cr_id}",
            json={"description": "Reworked description."},
            headers=headers_for(requester),
        )
        assert patched.status_code == 200

        resubmitted = await transition(client, requester, cr_id, "SUBMIT")
        assert resubmitted.status_code == 200
        reviewed = await transition(client, reviewer, cr_id, "APPROVE")
        assert reviewed.json()["current_stage"] == "ENGINEERING_REVIEW"

    async def test_requester_reviewer_transition_forbidden(self, client, requester, reviewer):
        created = await client.post(
            "/api/v1/change-requests",
            json=create_payload(),
            headers=headers_for(requester),
        )
        cr_id = created.json()["id"]
        await transition(client, requester, cr_id, "SUBMIT")

        denied = await transition(client, requester, cr_id, "APPROVE")
        assert denied.status_code == 403
        assert "reviewers and admins" in denied.json()["detail"]

        still_submitted = await client.get(
            f"/api/v1/change-requests/{cr_id}", headers=headers_for(requester)
        )
        assert still_submitted.json()["current_stage"] == "SUBMITTED"

        invalid = await transition(client, reviewer, cr_id, "REQUEST_CHANGES")
        assert invalid.status_code == 409

    async def test_high_risk_dual_approval_via_rest(self, client, requester, reviewer, admin):
        created = await client.post(
            "/api/v1/change-requests",
            json=create_payload(risk_level="HIGH"),
            headers=headers_for(requester),
        )
        cr_id = created.json()["id"]
        await transition(client, requester, cr_id, "SUBMIT")
        await transition(client, reviewer, cr_id, "APPROVE")

        first = await transition(client, reviewer, cr_id, "APPROVE")
        assert first.json()["current_stage"] == "ENGINEERING_REVIEW"

        duplicate = await transition(client, reviewer, cr_id, "APPROVE")
        assert duplicate.status_code == 409

        second = await transition(client, admin, cr_id, "APPROVE")
        assert second.json()["current_stage"] == "MANUFACTURING_REVIEW"

    async def test_patch_permissions(self, client, requester, reviewer):
        created = await client.post(
            "/api/v1/change-requests",
            json=create_payload(),
            headers=headers_for(requester),
        )
        cr_id = created.json()["id"]

        forbidden = await client.patch(
            f"/api/v1/change-requests/{cr_id}",
            json={"title": "nope"},
            headers=headers_for(reviewer),
        )
        assert forbidden.status_code == 403

        await transition(client, requester, cr_id, "SUBMIT")
        locked = await client.patch(
            f"/api/v1/change-requests/{cr_id}",
            json={"title": "nope"},
            headers=headers_for(requester),
        )
        assert locked.status_code == 409


class TestListing:
    async def test_list_filters_and_pagination(self, client, requester, make_change_request):
        for index in range(3):
            make_change_request(
                requester,
                title=f"Request {index}",
                stage=ChangeStage.DRAFT if index < 2 else ChangeStage.APPROVED,
                risk_level=RiskLevel.HIGH if index == 0 else RiskLevel.LOW,
                ticket_key=f"ECR-{9000 + index}",
            )

        response = await client.get(
            "/api/v1/change-requests?limit=2&offset=0", headers=headers_for(requester)
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2

        second_page = await client.get(
            "/api/v1/change-requests?limit=2&offset=2", headers=headers_for(requester)
        )
        assert len(second_page.json()["items"]) == 1

        by_stage = await client.get(
            "/api/v1/change-requests?stage=APPROVED", headers=headers_for(requester)
        )
        assert by_stage.json()["total"] == 1
        assert by_stage.json()["items"][0]["current_stage"] == "APPROVED"

        by_risk = await client.get(
            "/api/v1/change-requests?risk_level=HIGH", headers=headers_for(requester)
        )
        assert by_risk.json()["total"] == 1

        by_requester = await client.get(
            f"/api/v1/change-requests?requester_id={requester.id}",
            headers=headers_for(requester),
        )
        assert by_requester.json()["total"] == 3

        by_subsystem = await client.get(
            "/api/v1/change-requests?subsystem=TestSubsystem",
            headers=headers_for(requester),
        )
        assert by_subsystem.json()["total"] == 3

    async def test_list_validation_errors(self, client, requester):
        bad_stage = await client.get(
            "/api/v1/change-requests?stage=BOGUS", headers=headers_for(requester)
        )
        assert bad_stage.status_code == 422

        bad_limit = await client.get(
            "/api/v1/change-requests?limit=0", headers=headers_for(requester)
        )
        assert bad_limit.status_code == 422


class TestNotFoundAndValidation:
    async def test_missing_change_request_returns_404(self, client, requester):
        missing = str(uuid.uuid4())
        response = await client.get(
            f"/api/v1/change-requests/{missing}", headers=headers_for(requester)
        )
        assert response.status_code == 404

        audit = await client.get(
            f"/api/v1/change-requests/{missing}/audit", headers=headers_for(requester)
        )
        assert audit.status_code == 404

        patch = await client.patch(
            f"/api/v1/change-requests/{missing}",
            json={"title": "x"},
            headers=headers_for(requester),
        )
        assert patch.status_code == 404

        trans = await transition(client, requester, missing, "SUBMIT")
        assert trans.status_code == 404

    async def test_create_validation(self, client, requester):
        response = await client.post(
            "/api/v1/change-requests",
            json=create_payload(title=""),
            headers=headers_for(requester),
        )
        assert response.status_code == 422

    async def test_invalid_transition_action(self, client, requester):
        created = await client.post(
            "/api/v1/change-requests",
            json=create_payload(),
            headers=headers_for(requester),
        )
        response = await transition(client, requester, created.json()["id"], "BOGUS")
        assert response.status_code == 422

    async def test_analytics_endpoint(self, client, requester):
        response = await client.get("/api/v1/analytics/cycle-time", headers=headers_for(requester))
        assert response.status_code == 200
        body = response.json()
        assert len(body["stage_metrics"]) == 6
        assert set(body["current_stage_counts"]) == {
            "DRAFT",
            "SUBMITTED",
            "ENGINEERING_REVIEW",
            "MANUFACTURING_REVIEW",
            "APPROVED",
            "REJECTED",
        }

    async def test_analytics_requires_auth(self, client):
        response = await client.get("/api/v1/analytics/cycle-time")
        assert response.status_code == 401

    async def test_graphiql_served_on_get(self, client):
        response = await client.get("/graphql", headers={"Accept": "text/html"})
        assert response.status_code == 200
        assert "graphiql" in response.text.lower()


class TestAuditTrailOrdering:
    async def test_audit_trail_ordered_by_created_at(self, client, requester, make_change_request):
        from datetime import UTC, datetime, timedelta

        from app.models import AuditEvent

        base = datetime(2026, 1, 10, tzinfo=UTC)
        cr = make_change_request(
            requester,
            stage=ChangeStage.SUBMITTED,
            created_at=base,
            audit_events=[
                AuditEvent(
                    actor_id=requester.id,
                    from_stage=None,
                    to_stage=ChangeStage.DRAFT,
                    action="CREATED",
                    meta={},
                    created_at=base,
                ),
                AuditEvent(
                    actor_id=requester.id,
                    from_stage=ChangeStage.DRAFT,
                    to_stage=ChangeStage.SUBMITTED,
                    action="SUBMITTED",
                    meta={},
                    created_at=base + timedelta(hours=2),
                ),
            ],
        )
        response = await client.get(
            f"/api/v1/change-requests/{cr.id}/audit", headers=headers_for(requester)
        )
        assert [event["action"] for event in response.json()["items"]] == [
            "CREATED",
            "SUBMITTED",
        ]


class TestDatabaseStateAfterTransitions:
    async def test_approval_rows_written(self, client, requester, reviewer, admin, db):
        created = await client.post(
            "/api/v1/change-requests",
            json=create_payload(risk_level="HIGH"),
            headers=headers_for(requester),
        )
        cr_id = created.json()["id"]
        await transition(client, requester, cr_id, "SUBMIT")
        await transition(client, reviewer, cr_id, "APPROVE")
        await transition(client, reviewer, cr_id, "APPROVE")
        await transition(client, admin, cr_id, "APPROVE")

        approvals = list(
            db.scalars(select(Approval).where(Approval.change_request_id == uuid.UUID(cr_id)))
        )
        assert [a.stage.value for a in approvals] == [
            "SUBMITTED",
            "ENGINEERING_REVIEW",
            "ENGINEERING_REVIEW",
        ]
        assert [a.decision.value for a in approvals] == ["APPROVE", "APPROVE", "APPROVE"]

        events = list(
            db.scalars(select(AuditEvent).where(AuditEvent.change_request_id == uuid.UUID(cr_id)))
        )
        assert [e.action for e in events] == [
            "CREATED",
            "SUBMITTED",
            "MOVED_TO_ENGINEERING_REVIEW",
            "APPROVED",
            "MOVED_TO_MANUFACTURING_REVIEW",
        ]

        cr = db.get(ChangeRequest, uuid.UUID(cr_id))
        assert cr is not None
        assert cr.current_stage is ChangeStage.MANUFACTURING_REVIEW
