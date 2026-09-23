import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ChangeStage, RiskLevel
from app.models import AuditEvent
from app.workflow import WorkflowAction


class ChangeRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    vehicle_program: str = Field(min_length=1, max_length=200)
    subsystem: str = Field(min_length=1, max_length=200)
    risk_level: RiskLevel


class ChangeRequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, min_length=1)
    vehicle_program: str | None = Field(default=None, min_length=1, max_length=200)
    subsystem: str | None = Field(default=None, min_length=1, max_length=200)
    risk_level: RiskLevel | None = None


class ChangeRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_key: str
    title: str
    description: str
    vehicle_program: str
    subsystem: str
    risk_level: RiskLevel
    current_stage: ChangeStage
    requester_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ChangeRequestPage(BaseModel):
    items: list[ChangeRequestOut]
    total: int
    offset: int
    limit: int


class TransitionRequest(BaseModel):
    action: WorkflowAction
    comment: str | None = Field(default=None, max_length=2000)


class AuditEventOut(BaseModel):
    id: uuid.UUID
    change_request_id: uuid.UUID
    actor_id: uuid.UUID
    from_stage: ChangeStage | None
    to_stage: ChangeStage | None
    action: str
    metadata: dict
    created_at: datetime

    @classmethod
    def from_model(cls, event: AuditEvent) -> "AuditEventOut":
        return cls(
            id=event.id,
            change_request_id=event.change_request_id,
            actor_id=event.actor_id,
            from_stage=event.from_stage,
            to_stage=event.to_stage,
            action=event.action,
            metadata=event.meta,
            created_at=event.created_at,
        )


class AuditTrailResponse(BaseModel):
    change_request_id: uuid.UUID
    items: list[AuditEventOut]
