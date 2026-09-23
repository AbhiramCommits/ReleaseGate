from pydantic import BaseModel

from app.enums import ChangeStage


class StageDwellMetric(BaseModel):
    stage: ChangeStage
    average_hours: float | None
    median_hours: float | None
    samples: int


class CycleTimeResponse(BaseModel):
    stage_metrics: list[StageDwellMetric]
    current_stage_counts: dict[ChangeStage, int]
    end_to_end_average_hours: float | None
    top_slowest_stages: list[StageDwellMetric]
