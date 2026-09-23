import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import ChangeStage, Decision, RiskLevel, Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(SAEnum(Role, name="user_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    change_requests: Mapped[list["ChangeRequest"]] = relationship(back_populates="requester")
    approvals: Mapped[list["Approval"]] = relationship(back_populates="reviewer")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="actor")


class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ticket_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    vehicle_program: Mapped[str] = mapped_column(Text, nullable=False)
    subsystem: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel, name="risk_level"), nullable=False
    )
    current_stage: Mapped[ChangeStage] = mapped_column(
        SAEnum(ChangeStage, name="change_stage"), nullable=False, index=True
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    requester: Mapped["User"] = relationship(back_populates="change_requests")
    approvals: Mapped[list["Approval"]] = relationship(back_populates="change_request")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="change_request")


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    change_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("change_requests.id"), nullable=False, index=True
    )
    stage: Mapped[ChangeStage] = mapped_column(
        SAEnum(ChangeStage, name="change_stage"), nullable=False
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    decision: Mapped[Decision] = mapped_column(SAEnum(Decision, name="decision"), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    change_request: Mapped["ChangeRequest"] = relationship(back_populates="approvals")
    reviewer: Mapped["User"] = relationship(back_populates="approvals")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_change_request_id_created_at", "change_request_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    change_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("change_requests.id"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    from_stage: Mapped[ChangeStage | None] = mapped_column(
        SAEnum(ChangeStage, name="change_stage"), nullable=True
    )
    to_stage: Mapped[ChangeStage | None] = mapped_column(
        SAEnum(ChangeStage, name="change_stage"), nullable=True
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    change_request: Mapped["ChangeRequest"] = relationship(back_populates="audit_events")
    actor: Mapped["User"] = relationship(back_populates="audit_events")
