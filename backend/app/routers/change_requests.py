import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.enums import ChangeStage, RiskLevel
from app.models import User
from app.repositories import change_requests as change_requests_repository
from app.schemas import (
    AuditEventOut,
    AuditTrailResponse,
    ChangeRequestCreate,
    ChangeRequestOut,
    ChangeRequestPage,
    ChangeRequestUpdate,
    TransitionRequest,
)
from app.workflow import assert_can_edit

router = APIRouter(prefix="/api/v1/change-requests", tags=["change-requests"])


@router.get("", response_model=ChangeRequestPage)
def list_change_requests(
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    stage: Annotated[ChangeStage | None, Query()] = None,
    risk_level: Annotated[RiskLevel | None, Query()] = None,
    requester_id: Annotated[uuid.UUID | None, Query()] = None,
    subsystem: Annotated[str | None, Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ChangeRequestPage:
    items, total = change_requests_repository.list_change_requests(
        db,
        stage=stage,
        risk_level=risk_level,
        requester_id=requester_id,
        subsystem=subsystem,
        offset=offset,
        limit=limit,
    )
    return ChangeRequestPage(items=items, total=total, offset=offset, limit=limit)


@router.post("", response_model=ChangeRequestOut, status_code=status.HTTP_201_CREATED)
def create_change_request(
    payload: ChangeRequestCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChangeRequestOut:
    return change_requests_repository.create_change_request(db, payload, current_user)


@router.get("/{change_request_id}", response_model=ChangeRequestOut)
def get_change_request(
    change_request_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> ChangeRequestOut:
    change_request = change_requests_repository.get_change_request(db, change_request_id)
    if change_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found",
        )
    return change_request


@router.patch("/{change_request_id}", response_model=ChangeRequestOut)
def patch_change_request(
    change_request_id: uuid.UUID,
    payload: ChangeRequestUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChangeRequestOut:
    change_request = change_requests_repository.get_change_request(
        db, change_request_id, for_update=True
    )
    if change_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found",
        )
    assert_can_edit(
        requester_id=change_request.requester_id,
        actor_id=current_user.id,
        current_stage=change_request.current_stage,
    )
    return change_requests_repository.update_change_request(db, change_request, payload)


@router.post("/{change_request_id}/transitions", response_model=ChangeRequestOut)
def transition_change_request(
    change_request_id: uuid.UUID,
    payload: TransitionRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChangeRequestOut:
    change_request = change_requests_repository.get_change_request(
        db, change_request_id, for_update=True
    )
    if change_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found",
        )
    return change_requests_repository.transition_change_request(
        db, change_request, current_user, payload.action, payload.comment
    )


@router.get("/{change_request_id}/audit", response_model=AuditTrailResponse)
def get_audit_trail(
    change_request_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> AuditTrailResponse:
    change_request = change_requests_repository.get_change_request(db, change_request_id)
    if change_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change request not found",
        )
    events = change_requests_repository.list_audit_events(db, change_request_id)
    return AuditTrailResponse(
        change_request_id=change_request_id,
        items=[AuditEventOut.from_model(event) for event in events],
    )
