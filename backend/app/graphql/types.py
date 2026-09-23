from datetime import datetime

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.enums import ChangeStage, Decision, RiskLevel, Role
from app.graphql.context import Context
from app.workflow import WorkflowAction

ChangeStageEnum = strawberry.enum(ChangeStage)
RiskLevelEnum = strawberry.enum(RiskLevel)
RoleEnum = strawberry.enum(Role)
DecisionEnum = strawberry.enum(Decision)
WorkflowActionEnum = strawberry.enum(WorkflowAction)


@strawberry.type
class UserType:
    id: strawberry.ID
    email: str
    full_name: str
    role: RoleEnum
    created_at: datetime


@strawberry.type
class ChangeRequestType:
    id: strawberry.ID
    ticket_key: str
    title: str
    description: str
    vehicle_program: str
    subsystem: str
    risk_level: RiskLevelEnum
    current_stage: ChangeStageEnum
    requester_id: strawberry.ID
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def requester(self, info: Info[Context, None]) -> UserType:
        return await info.context.loaders.users.load(self.requester_id)

    @strawberry.field
    async def approvals(self, info: Info[Context, None]) -> list["ApprovalType"]:
        return await info.context.loaders.approvals.load(self.id)

    @strawberry.field
    async def audit_events(self, info: Info[Context, None]) -> list["AuditEventType"]:
        return await info.context.loaders.audit_events.load(self.id)


@strawberry.type
class ApprovalType:
    id: strawberry.ID
    stage: ChangeStageEnum
    decision: DecisionEnum
    comment: str | None
    decided_at: datetime

    @strawberry.field
    async def reviewer(self, info: Info[Context, None]) -> UserType:
        return await info.context.loaders.users.load(self.reviewer_id)


@strawberry.type
class AuditEventType:
    id: strawberry.ID
    from_stage: ChangeStageEnum | None
    to_stage: ChangeStageEnum | None
    action: str
    created_at: datetime

    @strawberry.field
    def metadata(self) -> JSON:
        return self.meta

    @strawberry.field
    async def actor(self, info: Info[Context, None]) -> UserType:
        return await info.context.loaders.users.load(self.actor_id)


@strawberry.type
class PageInfo:
    has_next_page: bool
    has_previous_page: bool
    start_cursor: str | None
    end_cursor: str | None


@strawberry.type
class ChangeRequestEdge:
    cursor: str
    node: ChangeRequestType


@strawberry.type
class ChangeRequestConnection:
    edges: list[ChangeRequestEdge]
    page_info: PageInfo
    total_count: int


@strawberry.type
class StageMetric:
    stage: ChangeStageEnum
    average_hours: float | None
    median_hours: float | None
    samples: int


@strawberry.type
class StageCount:
    stage: ChangeStageEnum
    count: int


@strawberry.type
class CycleTimeAnalytics:
    stage_metrics: list[StageMetric]
    current_stage_counts: list[StageCount]
    end_to_end_average_hours: float | None
    top_slowest_stages: list[StageMetric]


@strawberry.input
class ChangeRequestInput:
    title: str
    description: str
    vehicle_program: str
    subsystem: str
    risk_level: RiskLevelEnum


@strawberry.input
class ChangeRequestUpdateInput:
    title: str | None = None
    description: str | None = None
    vehicle_program: str | None = None
    subsystem: str | None = None
    risk_level: RiskLevelEnum | None = None
