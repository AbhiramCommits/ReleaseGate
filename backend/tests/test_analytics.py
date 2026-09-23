from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.enums import ChangeStage, RiskLevel, Role
from app.models import AuditEvent, ChangeRequest
from app.repositories import analytics as analytics_repository

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _add_event(db, cr, requester, from_stage, to_stage, action, at):
    db.add(
        AuditEvent(
            change_request_id=cr.id,
            actor_id=requester.id,
            from_stage=from_stage,
            to_stage=to_stage,
            action=action,
            meta={},
            created_at=at,
        )
    )


def _build_fixture(db, requester):
    cr1 = ChangeRequest(
        ticket_key="ECR-8001",
        title="Analytics one",
        description="d",
        vehicle_program="P",
        subsystem="S",
        risk_level=RiskLevel.MEDIUM,
        current_stage=ChangeStage.APPROVED,
        requester_id=requester.id,
        created_at=BASE,
        updated_at=BASE + timedelta(hours=36),
    )
    db.add(cr1)
    db.flush()

    _add_event(db, cr1, requester, None, ChangeStage.DRAFT, "CREATED", BASE)
    _add_event(
        db,
        cr1,
        requester,
        ChangeStage.DRAFT,
        ChangeStage.SUBMITTED,
        "SUBMITTED",
        BASE + timedelta(hours=12),
    )
    _add_event(
        db,
        cr1,
        requester,
        ChangeStage.SUBMITTED,
        ChangeStage.ENGINEERING_REVIEW,
        "MOVED_TO_ENGINEERING_REVIEW",
        BASE + timedelta(hours=22),
    )
    _add_event(
        db,
        cr1,
        requester,
        ChangeStage.ENGINEERING_REVIEW,
        ChangeStage.MANUFACTURING_REVIEW,
        "MOVED_TO_MANUFACTURING_REVIEW",
        BASE + timedelta(hours=30),
    )
    _add_event(
        db,
        cr1,
        requester,
        ChangeStage.MANUFACTURING_REVIEW,
        ChangeStage.APPROVED,
        "APPROVED",
        BASE + timedelta(hours=36),
    )

    cr2 = ChangeRequest(
        ticket_key="ECR-8002",
        title="Analytics two",
        description="d",
        vehicle_program="P",
        subsystem="S",
        risk_level=RiskLevel.LOW,
        current_stage=ChangeStage.SUBMITTED,
        requester_id=requester.id,
        created_at=BASE,
        updated_at=BASE + timedelta(hours=36),
    )
    db.add(cr2)
    db.flush()
    _add_event(db, cr2, requester, None, ChangeStage.DRAFT, "CREATED", BASE)
    _add_event(
        db,
        cr2,
        requester,
        ChangeStage.DRAFT,
        ChangeStage.SUBMITTED,
        "SUBMITTED",
        BASE + timedelta(hours=36),
    )

    cr3 = ChangeRequest(
        ticket_key="ECR-8003",
        title="Analytics three with change request loop",
        description="d",
        vehicle_program="P",
        subsystem="S",
        risk_level=RiskLevel.MEDIUM,
        current_stage=ChangeStage.DRAFT,
        requester_id=requester.id,
        created_at=BASE,
        updated_at=BASE + timedelta(hours=50),
    )
    db.add(cr3)
    db.flush()
    _add_event(db, cr3, requester, None, ChangeStage.DRAFT, "CREATED", BASE)
    _add_event(
        db,
        cr3,
        requester,
        ChangeStage.DRAFT,
        ChangeStage.SUBMITTED,
        "SUBMITTED",
        BASE + timedelta(hours=10),
    )
    _add_event(
        db,
        cr3,
        requester,
        ChangeStage.SUBMITTED,
        ChangeStage.ENGINEERING_REVIEW,
        "MOVED_TO_ENGINEERING_REVIEW",
        BASE + timedelta(hours=14),
    )
    _add_event(
        db,
        cr3,
        requester,
        ChangeStage.ENGINEERING_REVIEW,
        ChangeStage.ENGINEERING_REVIEW,
        "REQUESTED_CHANGES",
        BASE + timedelta(hours=16),
    )
    _add_event(
        db,
        cr3,
        requester,
        ChangeStage.ENGINEERING_REVIEW,
        ChangeStage.DRAFT,
        "REQUESTED_CHANGES",
        BASE + timedelta(hours=19),
    )
    db.commit()

    return cr1, cr2, cr3


def _metric(report, stage):
    return next(metric for metric in report.stage_metrics if metric.stage is stage)


def test_cycle_time_exact_dwell_hours(db, make_user):
    requester = make_user(Role.REQUESTER)
    _build_fixture(db, requester)

    report = analytics_repository.cycle_time_report(db)

    draft = _metric(report, ChangeStage.DRAFT)
    assert draft.samples == 3
    assert draft.average_hours == 19.33
    assert draft.median_hours == 12.0

    submitted = _metric(report, ChangeStage.SUBMITTED)
    assert submitted.samples == 2
    assert submitted.average_hours == 7.0
    assert submitted.median_hours == 7.0

    engineering = _metric(report, ChangeStage.ENGINEERING_REVIEW)
    assert engineering.samples == 2
    assert engineering.average_hours == 6.5
    assert engineering.median_hours == 6.5

    manufacturing = _metric(report, ChangeStage.MANUFACTURING_REVIEW)
    assert manufacturing.samples == 1
    assert manufacturing.average_hours == 6.0

    assert _metric(report, ChangeStage.APPROVED).samples == 0
    assert _metric(report, ChangeStage.REJECTED).samples == 0

    assert report.end_to_end_average_hours == 36.0

    assert report.current_stage_counts == {
        ChangeStage.DRAFT: 1,
        ChangeStage.SUBMITTED: 1,
        ChangeStage.ENGINEERING_REVIEW: 0,
        ChangeStage.MANUFACTURING_REVIEW: 0,
        ChangeStage.APPROVED: 1,
        ChangeStage.REJECTED: 0,
    }

    assert [metric.stage for metric in report.top_slowest_stages] == [
        ChangeStage.DRAFT,
        ChangeStage.SUBMITTED,
        ChangeStage.ENGINEERING_REVIEW,
    ]


def test_cycle_time_empty_database(db):
    report = analytics_repository.cycle_time_report(db)
    assert all(metric.samples == 0 for metric in report.stage_metrics)
    assert report.end_to_end_average_hours is None
    assert report.top_slowest_stages == []
    assert sum(report.current_stage_counts.values()) == 0


def test_cycle_time_uses_audit_events_not_updated_at(db, make_user):
    requester = make_user(Role.REQUESTER)
    _build_fixture(db, requester)

    bogus_updated_at = BASE + timedelta(hours=9999)
    cr = db.scalar(select(ChangeRequest).where(ChangeRequest.ticket_key == "ECR-8001"))
    assert cr is not None
    cr.updated_at = bogus_updated_at
    db.commit()

    report = analytics_repository.cycle_time_report(db)
    assert report.end_to_end_average_hours == 36.0
