import base64
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

import strawberry
from sqlalchemy.orm import Session
from strawberry.exceptions import GraphQLError
from strawberry.types import Info

from app.graphql.context import Context
from app.graphql.types import (
    ChangeRequestConnection,
    ChangeRequestEdge,
    ChangeRequestInput,
    ChangeRequestType,
    ChangeRequestUpdateInput,
    ChangeStageEnum,
    CycleTimeAnalytics,
    PageInfo,
    RiskLevelEnum,
    StageCount,
    StageMetric,
    UserType,
    WorkflowActionEnum,
)
from app.models import User
from app.repositories import analytics as analytics_repository
from app.repositories import change_requests as change_requests_repository
from app.schemas.change_requests import ChangeRequestCreate, ChangeRequestUpdate
from app.workflow import (
    InvalidTransition,
    PermissionDenied,
    WorkflowAction,
    assert_can_edit,
)

DEFAULT_FIRST = 20
MAX_FIRST = 100


def require_user(info: Info[Context, None]) -> User:
    if info.context.user is None:
        raise GraphQLError(
            "Not authenticated",
            extensions={"code": "UNAUTHENTICATED", "statusCode": 401},
        )
    return info.context.user


@contextmanager
def workflow_errors() -> Iterator[None]:
    try:
        yield
    except InvalidTransition as exc:
        raise GraphQLError(
            str(exc),
            extensions={"code": "INVALID_TRANSITION", "statusCode": 409},
        ) from exc
    except PermissionDenied as exc:
        raise GraphQLError(
            str(exc),
            extensions={"code": "PERMISSION_DENIED", "statusCode": 403},
        ) from exc


def parse_id(raw_id: strawberry.ID) -> uuid.UUID:
    try:
        return uuid.UUID(str(raw_id))
    except ValueError as exc:
        raise GraphQLError("Invalid id", extensions={"code": "BAD_USER_INPUT"}) from exc


def encode_cursor(updated_at: datetime, change_request_id: uuid.UUID) -> str:
    raw = f"{updated_at.isoformat()}|{change_request_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        updated_at_raw, id_raw = raw.split("|", 1)
        return datetime.fromisoformat(updated_at_raw), uuid.UUID(id_raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise GraphQLError("Invalid cursor", extensions={"code": "BAD_USER_INPUT"}) from exc


def build_connection(
    db: Session,
    *,
    stage: ChangeStageEnum | None,
    risk_level: RiskLevelEnum | None,
    subsystem: str | None,
    first: int | None,
    after: str | None,
) -> ChangeRequestConnection:
    decoded_after = decode_cursor(after) if after is not None else None
    page_size = first if first is not None else DEFAULT_FIRST
    items, has_next_page = change_requests_repository.list_change_requests_cursor(
        db,
        stage=stage,
        risk_level=risk_level,
        subsystem=subsystem,
        first=page_size,
        after=decoded_after,
    )
    edges = [
        ChangeRequestEdge(cursor=encode_cursor(item.updated_at, item.id), node=item)
        for item in items
    ]
    return ChangeRequestConnection(
        edges=edges,
        page_info=PageInfo(
            has_next_page=has_next_page,
            has_previous_page=after is not None,
            start_cursor=edges[0].cursor if edges else None,
            end_cursor=edges[-1].cursor if edges else None,
        ),
        total_count=change_requests_repository.count_change_requests(
            db, stage=stage, risk_level=risk_level, subsystem=subsystem
        ),
    )


@strawberry.type
class Query:
    @strawberry.field
    def me(self, info: Info[Context, None]) -> UserType:
        return require_user(info)

    @strawberry.field
    def change_request(
        self, info: Info[Context, None], id: strawberry.ID
    ) -> ChangeRequestType | None:
        require_user(info)
        return change_requests_repository.get_change_request(info.context.db, parse_id(id))

    @strawberry.field
    def change_requests(
        self,
        info: Info[Context, None],
        stage: ChangeStageEnum | None = None,
        risk_level: RiskLevelEnum | None = None,
        subsystem: str | None = None,
        first: int | None = None,
        after: str | None = None,
    ) -> ChangeRequestConnection:
        require_user(info)
        return build_connection(
            info.context.db,
            stage=stage,
            risk_level=risk_level,
            subsystem=subsystem,
            first=first,
            after=after,
        )

    @strawberry.field
    def cycle_time_analytics(self, info: Info[Context, None]) -> CycleTimeAnalytics:
        require_user(info)
        report = analytics_repository.cycle_time_report(info.context.db)
        return CycleTimeAnalytics(
            stage_metrics=[StageMetric(**metric.model_dump()) for metric in report.stage_metrics],
            current_stage_counts=[
                StageCount(stage=stage, count=count)
                for stage, count in report.current_stage_counts.items()
            ],
            end_to_end_average_hours=report.end_to_end_average_hours,
            top_slowest_stages=[
                StageMetric(**metric.model_dump()) for metric in report.top_slowest_stages
            ],
        )


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_change_request(
        self, info: Info[Context, None], input: ChangeRequestInput
    ) -> ChangeRequestType:
        user = require_user(info)
        payload = ChangeRequestCreate(**strawberry.asdict(input))
        return change_requests_repository.create_change_request(info.context.db, payload, user)

    @strawberry.mutation
    def update_change_request(
        self,
        info: Info[Context, None],
        id: strawberry.ID,
        input: ChangeRequestUpdateInput,
    ) -> ChangeRequestType:
        user = require_user(info)
        change_request = change_requests_repository.get_change_request(
            info.context.db, parse_id(id), for_update=True
        )
        if change_request is None:
            raise GraphQLError("Change request not found", extensions={"code": "NOT_FOUND"})
        with workflow_errors():
            assert_can_edit(
                requester_id=change_request.requester_id,
                actor_id=user.id,
                current_stage=change_request.current_stage,
            )
        payload = ChangeRequestUpdate(
            **{
                field: value
                for field, value in strawberry.asdict(input).items()
                if value is not None
            }
        )
        return change_requests_repository.update_change_request(
            info.context.db, change_request, payload
        )

    @strawberry.mutation
    def transition_change_request(
        self,
        info: Info[Context, None],
        id: strawberry.ID,
        action: WorkflowActionEnum,
        comment: str | None = None,
    ) -> ChangeRequestType:
        user = require_user(info)
        change_request = change_requests_repository.get_change_request(
            info.context.db, parse_id(id), for_update=True
        )
        if change_request is None:
            raise GraphQLError("Change request not found", extensions={"code": "NOT_FOUND"})
        with workflow_errors():
            return change_requests_repository.transition_change_request(
                info.context.db, change_request, user, WorkflowAction(action.value), comment
            )
