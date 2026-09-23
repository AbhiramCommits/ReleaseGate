import enum
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from app.enums import ChangeStage, Decision, RiskLevel, Role

REVIEW_STAGES = (ChangeStage.ENGINEERING_REVIEW, ChangeStage.MANUFACTURING_REVIEW)


class WorkflowError(Exception):
    pass


class InvalidTransition(WorkflowError):
    pass


class PermissionDenied(WorkflowError):
    pass


class WorkflowAction(str, enum.Enum):
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    REJECT = "REJECT"


@dataclass(frozen=True)
class RequestSnapshot:
    current_stage: ChangeStage
    risk_level: RiskLevel
    requester_id: uuid.UUID


@dataclass(frozen=True)
class ActorSnapshot:
    id: uuid.UUID
    role: Role


@dataclass(frozen=True)
class ApprovalRecord:
    stage: ChangeStage
    decision: Decision
    reviewer_id: uuid.UUID


@dataclass(frozen=True)
class Transition:
    from_stage: ChangeStage
    to_stage: ChangeStage
    action: str
    decision: Decision | None


def apply_transition(
    request: RequestSnapshot,
    actor: ActorSnapshot,
    action: WorkflowAction,
    approvals: Sequence[ApprovalRecord] = (),
) -> Transition:
    if action is WorkflowAction.SUBMIT:
        return _submit(request, actor)
    return _review(request, actor, action, approvals)


def _submit(request: RequestSnapshot, actor: ActorSnapshot) -> Transition:
    if request.current_stage is not ChangeStage.DRAFT:
        raise InvalidTransition(f"A request in {request.current_stage.value} cannot be submitted.")
    if actor.id != request.requester_id:
        raise PermissionDenied("Only the requester can submit their own request.")
    return Transition(
        from_stage=ChangeStage.DRAFT,
        to_stage=ChangeStage.SUBMITTED,
        action="SUBMITTED",
        decision=None,
    )


def _review(
    request: RequestSnapshot,
    actor: ActorSnapshot,
    action: WorkflowAction,
    approvals: Sequence[ApprovalRecord],
) -> Transition:
    if actor.role not in (Role.REVIEWER, Role.ADMIN):
        raise PermissionDenied("Only reviewers and admins can perform this action.")
    if action is WorkflowAction.APPROVE and actor.id == request.requester_id:
        raise PermissionDenied("A reviewer cannot approve their own request.")

    stage = request.current_stage

    if stage is ChangeStage.SUBMITTED:
        if action is not WorkflowAction.APPROVE:
            raise InvalidTransition(f"Cannot {action.value} a request that is {stage.value}.")
        return Transition(
            from_stage=stage,
            to_stage=ChangeStage.ENGINEERING_REVIEW,
            action="MOVED_TO_ENGINEERING_REVIEW",
            decision=Decision.APPROVE,
        )

    if stage in REVIEW_STAGES:
        return _review_stage(request, actor, action, approvals)

    raise InvalidTransition(f"No actions are allowed while the request is {stage.value}.")


def _review_stage(
    request: RequestSnapshot,
    actor: ActorSnapshot,
    action: WorkflowAction,
    approvals: Sequence[ApprovalRecord],
) -> Transition:
    stage = request.current_stage

    if action is WorkflowAction.REQUEST_CHANGES:
        return Transition(
            from_stage=stage,
            to_stage=ChangeStage.DRAFT,
            action="REQUESTED_CHANGES",
            decision=Decision.REQUEST_CHANGES,
        )

    if action is WorkflowAction.REJECT:
        return Transition(
            from_stage=stage,
            to_stage=ChangeStage.REJECTED,
            action="REJECTED",
            decision=Decision.REJECT,
        )

    if action is not WorkflowAction.APPROVE:
        raise InvalidTransition(f"Cannot {action.value} a request that is {stage.value}.")

    if stage is ChangeStage.MANUFACTURING_REVIEW:
        _assert_not_approved_before(actor, stage, approvals)
        return Transition(
            from_stage=stage,
            to_stage=ChangeStage.APPROVED,
            action="APPROVED",
            decision=Decision.APPROVE,
        )

    _assert_not_approved_before(actor, stage, approvals)

    distinct_approvers = {
        approval.reviewer_id
        for approval in approvals
        if approval.stage is ChangeStage.ENGINEERING_REVIEW
        and approval.decision is Decision.APPROVE
    }
    if request.risk_level is RiskLevel.HIGH and not distinct_approvers:
        return Transition(
            from_stage=stage,
            to_stage=stage,
            action="APPROVED",
            decision=Decision.APPROVE,
        )
    return Transition(
        from_stage=stage,
        to_stage=ChangeStage.MANUFACTURING_REVIEW,
        action="MOVED_TO_MANUFACTURING_REVIEW",
        decision=Decision.APPROVE,
    )


def _assert_not_approved_before(
    actor: ActorSnapshot,
    stage: ChangeStage,
    approvals: Sequence[ApprovalRecord],
) -> None:
    for approval in approvals:
        if (
            approval.stage is stage
            and approval.decision is Decision.APPROVE
            and approval.reviewer_id == actor.id
        ):
            raise InvalidTransition("A reviewer may only approve a request once per stage.")


def assert_can_edit(
    requester_id: uuid.UUID,
    actor_id: uuid.UUID,
    current_stage: ChangeStage,
) -> None:
    if actor_id != requester_id:
        raise PermissionDenied("Only the requester can edit their own request.")
    if current_stage is not ChangeStage.DRAFT:
        raise InvalidTransition("Only DRAFT requests can be edited.")
