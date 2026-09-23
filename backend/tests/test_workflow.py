import uuid

import pytest

from app.enums import ChangeStage, Decision, RiskLevel, Role
from app.workflow import (
    ActorSnapshot,
    ApprovalRecord,
    InvalidTransition,
    PermissionDenied,
    RequestSnapshot,
    WorkflowAction,
    apply_transition,
    assert_can_edit,
)

REQUESTER_ID = uuid.uuid4()
REVIEWER_ID = uuid.uuid4()
ADMIN_ID = uuid.uuid4()


def requester() -> ActorSnapshot:
    return ActorSnapshot(id=REQUESTER_ID, role=Role.REQUESTER)


def reviewer() -> ActorSnapshot:
    return ActorSnapshot(id=REVIEWER_ID, role=Role.REVIEWER)


def admin() -> ActorSnapshot:
    return ActorSnapshot(id=ADMIN_ID, role=Role.ADMIN)


def request(
    stage: ChangeStage = ChangeStage.DRAFT,
    risk: RiskLevel = RiskLevel.MEDIUM,
    owner: uuid.UUID = REQUESTER_ID,
) -> RequestSnapshot:
    return RequestSnapshot(current_stage=stage, risk_level=risk, requester_id=owner)


def approval(
    stage: ChangeStage,
    decision: Decision = Decision.APPROVE,
    reviewer_id: uuid.UUID = REVIEWER_ID,
) -> ApprovalRecord:
    return ApprovalRecord(stage=stage, decision=decision, reviewer_id=reviewer_id)


def test_requester_submits_own_draft():
    result = apply_transition(request(), requester(), WorkflowAction.SUBMIT)
    assert result.from_stage is ChangeStage.DRAFT
    assert result.to_stage is ChangeStage.SUBMITTED
    assert result.decision is None


def test_submit_requires_draft_stage():
    with pytest.raises(InvalidTransition):
        apply_transition(request(stage=ChangeStage.SUBMITTED), requester(), WorkflowAction.SUBMIT)


def test_non_owner_cannot_submit():
    with pytest.raises(PermissionDenied):
        apply_transition(request(), admin(), WorkflowAction.SUBMIT)


def test_requester_cannot_review():
    with pytest.raises(PermissionDenied):
        apply_transition(request(stage=ChangeStage.SUBMITTED), requester(), WorkflowAction.APPROVE)


def test_approve_submitted_moves_to_engineering_review():
    result = apply_transition(
        request(stage=ChangeStage.SUBMITTED), reviewer(), WorkflowAction.APPROVE
    )
    assert result.to_stage is ChangeStage.ENGINEERING_REVIEW
    assert result.decision is Decision.APPROVE


def test_request_changes_at_submitted_is_invalid():
    with pytest.raises(InvalidTransition):
        apply_transition(
            request(stage=ChangeStage.SUBMITTED),
            reviewer(),
            WorkflowAction.REQUEST_CHANGES,
        )


def test_reject_at_submitted_is_invalid():
    with pytest.raises(InvalidTransition):
        apply_transition(request(stage=ChangeStage.SUBMITTED), reviewer(), WorkflowAction.REJECT)


def test_medium_risk_single_approval_advances_engineering_review():
    result = apply_transition(
        request(stage=ChangeStage.ENGINEERING_REVIEW),
        reviewer(),
        WorkflowAction.APPROVE,
    )
    assert result.to_stage is ChangeStage.MANUFACTURING_REVIEW


def test_admin_can_approve_engineering_review():
    result = apply_transition(
        request(stage=ChangeStage.ENGINEERING_REVIEW), admin(), WorkflowAction.APPROVE
    )
    assert result.to_stage is ChangeStage.MANUFACTURING_REVIEW


def test_request_changes_returns_engineering_review_to_draft():
    result = apply_transition(
        request(stage=ChangeStage.ENGINEERING_REVIEW),
        reviewer(),
        WorkflowAction.REQUEST_CHANGES,
    )
    assert result.to_stage is ChangeStage.DRAFT
    assert result.decision is Decision.REQUEST_CHANGES


def test_request_changes_returns_manufacturing_review_to_draft():
    result = apply_transition(
        request(stage=ChangeStage.MANUFACTURING_REVIEW),
        admin(),
        WorkflowAction.REQUEST_CHANGES,
    )
    assert result.to_stage is ChangeStage.DRAFT


def test_reject_from_engineering_review():
    result = apply_transition(
        request(stage=ChangeStage.ENGINEERING_REVIEW), reviewer(), WorkflowAction.REJECT
    )
    assert result.to_stage is ChangeStage.REJECTED
    assert result.decision is Decision.REJECT


def test_reject_from_manufacturing_review():
    result = apply_transition(
        request(stage=ChangeStage.MANUFACTURING_REVIEW), reviewer(), WorkflowAction.REJECT
    )
    assert result.to_stage is ChangeStage.REJECTED


def test_approve_manufacturing_review_approves():
    result = apply_transition(
        request(stage=ChangeStage.MANUFACTURING_REVIEW),
        reviewer(),
        WorkflowAction.APPROVE,
    )
    assert result.to_stage is ChangeStage.APPROVED
    assert result.decision is Decision.APPROVE


@pytest.mark.parametrize("stage", [ChangeStage.APPROVED, ChangeStage.REJECTED])
@pytest.mark.parametrize(
    "action",
    [
        WorkflowAction.SUBMIT,
        WorkflowAction.APPROVE,
        WorkflowAction.REQUEST_CHANGES,
        WorkflowAction.REJECT,
    ],
)
def test_terminal_stages_reject_all_actions(stage, action):
    with pytest.raises(InvalidTransition):
        apply_transition(request(stage=stage), reviewer(), action)


def test_self_approval_denied():
    with pytest.raises(PermissionDenied):
        apply_transition(
            request(stage=ChangeStage.SUBMITTED, owner=REVIEWER_ID),
            reviewer(),
            WorkflowAction.APPROVE,
        )


def test_high_risk_requires_two_distinct_approvals():
    first = apply_transition(
        request(stage=ChangeStage.ENGINEERING_REVIEW, risk=RiskLevel.HIGH),
        reviewer(),
        WorkflowAction.APPROVE,
    )
    assert first.to_stage is ChangeStage.ENGINEERING_REVIEW

    with pytest.raises(InvalidTransition):
        apply_transition(
            request(stage=ChangeStage.ENGINEERING_REVIEW, risk=RiskLevel.HIGH),
            reviewer(),
            WorkflowAction.APPROVE,
            approvals=[approval(ChangeStage.ENGINEERING_REVIEW)],
        )

    second = apply_transition(
        request(stage=ChangeStage.ENGINEERING_REVIEW, risk=RiskLevel.HIGH),
        admin(),
        WorkflowAction.APPROVE,
        approvals=[approval(ChangeStage.ENGINEERING_REVIEW)],
    )
    assert second.to_stage is ChangeStage.MANUFACTURING_REVIEW


def test_reviewer_cannot_approve_same_stage_twice():
    with pytest.raises(InvalidTransition):
        apply_transition(
            request(stage=ChangeStage.MANUFACTURING_REVIEW),
            reviewer(),
            WorkflowAction.APPROVE,
            approvals=[approval(ChangeStage.MANUFACTURING_REVIEW)],
        )


def test_approve_own_request_denied_even_for_admin():
    with pytest.raises(PermissionDenied):
        apply_transition(
            request(stage=ChangeStage.SUBMITTED, owner=ADMIN_ID),
            admin(),
            WorkflowAction.APPROVE,
        )


def test_assert_can_edit_owner_draft_passes():
    assert_can_edit(REQUESTER_ID, REQUESTER_ID, ChangeStage.DRAFT)


def test_assert_can_edit_non_owner_denied():
    with pytest.raises(PermissionDenied):
        assert_can_edit(REQUESTER_ID, ADMIN_ID, ChangeStage.DRAFT)


def test_assert_can_edit_only_in_draft():
    with pytest.raises(InvalidTransition):
        assert_can_edit(REQUESTER_ID, REQUESTER_ID, ChangeStage.SUBMITTED)
