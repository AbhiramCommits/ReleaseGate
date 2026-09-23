from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.repositories import analytics as analytics_repository
from app.schemas import CycleTimeResponse

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/cycle-time", response_model=CycleTimeResponse)
def cycle_time(
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> CycleTimeResponse:
    return analytics_repository.cycle_time_report(db)
