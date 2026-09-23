import uuid
from datetime import datetime
from statistics import mean, median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import ChangeStage
from app.models import AuditEvent, ChangeRequest
from app.schemas.analytics import CycleTimeResponse, StageDwellMetric


def cycle_time_report(db: Session) -> CycleTimeResponse:
    rows = db.execute(
        select(
            AuditEvent.change_request_id,
            AuditEvent.from_stage,
            AuditEvent.to_stage,
            AuditEvent.created_at,
        ).order_by(AuditEvent.change_request_id, AuditEvent.created_at, AuditEvent.id)
    ).all()

    timelines: dict[uuid.UUID, list[tuple[ChangeStage | None, ChangeStage | None, datetime]]] = {}
    for change_request_id, from_stage, to_stage, created_at in rows:
        timelines.setdefault(change_request_id, []).append((from_stage, to_stage, created_at))

    dwells: dict[ChangeStage, list[float]] = {stage: [] for stage in ChangeStage}
    end_to_end_hours: list[float] = []

    for events in timelines.values():
        first_created_at = events[0][2]
        if events[-1][1] is ChangeStage.APPROVED:
            end_to_end_hours.append((events[-1][2] - first_created_at).total_seconds() / 3600)

        open_visits: dict[ChangeStage, datetime] = {}
        for from_stage, to_stage, created_at in events:
            if from_stage is not None and to_stage is not None and from_stage is not to_stage:
                opened_at = open_visits.pop(from_stage, None)
                if opened_at is not None:
                    dwells[from_stage].append((created_at - opened_at).total_seconds() / 3600)
            if to_stage is not None and (from_stage is None or from_stage is not to_stage):
                open_visits[to_stage] = created_at

    stage_metrics = [_build_metric(stage, dwells[stage]) for stage in ChangeStage]
    ranked = sorted(
        (metric for metric in stage_metrics if metric.samples > 0),
        key=lambda metric: (metric.average_hours or 0, metric.median_hours or 0),
        reverse=True,
    )
    top_slowest_stages = ranked[:3]

    count_rows = db.execute(
        select(ChangeRequest.current_stage, func.count()).group_by(ChangeRequest.current_stage)
    ).all()
    current_stage_counts = {stage: 0 for stage in ChangeStage}
    current_stage_counts.update({stage: count for stage, count in count_rows})

    return CycleTimeResponse(
        stage_metrics=stage_metrics,
        current_stage_counts=current_stage_counts,
        end_to_end_average_hours=(round(mean(end_to_end_hours), 2) if end_to_end_hours else None),
        top_slowest_stages=top_slowest_stages,
    )


def _build_metric(stage: ChangeStage, values: list[float]) -> StageDwellMetric:
    if not values:
        return StageDwellMetric(stage=stage, average_hours=None, median_hours=None, samples=0)
    return StageDwellMetric(
        stage=stage,
        average_hours=round(mean(values), 2),
        median_hours=round(median(values), 2),
        samples=len(values),
    )
