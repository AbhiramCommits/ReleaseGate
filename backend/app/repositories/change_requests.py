import uuid
from datetime import UTC, datetime

from sqlalchemy import Integer, func, select, text
from sqlalchemy.orm import Session

from app.enums import ChangeStage, RiskLevel
from app.models import Approval, AuditEvent, ChangeRequest, User
from app.schemas.change_requests import ChangeRequestCreate, ChangeRequestUpdate
from app.workflow import (
    ActorSnapshot,
    ApprovalRecord,
    RequestSnapshot,
    WorkflowAction,
    apply_transition,
)

TICKET_KEY_LOCK = 424242


def list_change_requests(
    db: Session,
    *,
    stage: ChangeStage | None = None,
    risk_level: RiskLevel | None = None,
    requester_id: uuid.UUID | None = None,
    subsystem: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[ChangeRequest], int]:
    stmt = select(ChangeRequest)
    if stage is not None:
        stmt = stmt.where(ChangeRequest.current_stage == stage)
    if risk_level is not None:
        stmt = stmt.where(ChangeRequest.risk_level == risk_level)
    if requester_id is not None:
        stmt = stmt.where(ChangeRequest.requester_id == requester_id)
    if subsystem is not None:
        stmt = stmt.where(ChangeRequest.subsystem == subsystem)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.scalars(
            stmt.order_by(ChangeRequest.updated_at.desc(), ChangeRequest.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return items, total


def get_change_request(
    db: Session,
    change_request_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> ChangeRequest | None:
    stmt = select(ChangeRequest).where(ChangeRequest.id == change_request_id)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def _next_ticket_key(db: Session) -> str:
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": TICKET_KEY_LOCK})
    last = db.scalar(
        select(func.max(func.cast(func.substring(ChangeRequest.ticket_key, 5), Integer)))
    )
    return f"ECR-{1000 if last is None else last + 1}"


def create_change_request(
    db: Session,
    payload: ChangeRequestCreate,
    requester: User,
) -> ChangeRequest:
    now = datetime.now(UTC)
    change_request = ChangeRequest(
        ticket_key=_next_ticket_key(db),
        title=payload.title,
        description=payload.description,
        vehicle_program=payload.vehicle_program,
        subsystem=payload.subsystem,
        risk_level=payload.risk_level,
        current_stage=ChangeStage.DRAFT,
        requester_id=requester.id,
        created_at=now,
        updated_at=now,
    )
    db.add(change_request)
    db.flush()
    db.add(
        AuditEvent(
            change_request_id=change_request.id,
            actor_id=requester.id,
            from_stage=None,
            to_stage=ChangeStage.DRAFT,
            action="CREATED",
            meta={},
            created_at=now,
        )
    )
    db.commit()
    return change_request


def update_change_request(
    db: Session,
    change_request: ChangeRequest,
    payload: ChangeRequestUpdate,
) -> ChangeRequest:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(change_request, field, value)
    db.commit()
    return change_request


def transition_change_request(
    db: Session,
    change_request: ChangeRequest,
    actor: User,
    action: WorkflowAction,
    comment: str | None,
) -> ChangeRequest:
    approvals = list(
        db.scalars(select(Approval).where(Approval.change_request_id == change_request.id))
    )
    transition = apply_transition(
        request=RequestSnapshot(
            current_stage=change_request.current_stage,
            risk_level=change_request.risk_level,
            requester_id=change_request.requester_id,
        ),
        actor=ActorSnapshot(id=actor.id, role=actor.role),
        action=action,
        approvals=[
            ApprovalRecord(stage=a.stage, decision=a.decision, reviewer_id=a.reviewer_id)
            for a in approvals
        ],
    )

    now = datetime.now(UTC)
    if transition.decision is not None:
        db.add(
            Approval(
                change_request_id=change_request.id,
                stage=transition.from_stage,
                reviewer_id=actor.id,
                decision=transition.decision,
                comment=comment,
                decided_at=now,
            )
        )
    db.add(
        AuditEvent(
            change_request_id=change_request.id,
            actor_id=actor.id,
            from_stage=transition.from_stage,
            to_stage=transition.to_stage,
            action=transition.action,
            meta={"comment": comment} if comment else {},
            created_at=now,
        )
    )
    change_request.current_stage = transition.to_stage
    change_request.updated_at = now

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return change_request


def list_audit_events(db: Session, change_request_id: uuid.UUID) -> list[AuditEvent]:
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.change_request_id == change_request_id)
            .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        )
    )
