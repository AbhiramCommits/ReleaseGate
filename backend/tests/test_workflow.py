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


class TestAllowedTransitions:
    def test_requester_submits_own_draft(self):
        result = apply_transition(request(), requester(), WorkflowAction.SUBMIT)
        assert (result.from_stage, result.to_stage) == (
            ChangeStage.DRAFT,
            ChangeStage.SUBMITTED,
        )
        assert result.action == "SUBMITTED"
        assert result.decision is None

    def test_reviewer_approve_submitted_to_engineering_review(self):
        result = apply_transition(
            request(stage=ChangeStage.SUBMITTED), reviewer(), WorkflowAction.APPROVE
        )
        assert result.to_stage is ChangeStage.ENGINEERING_REVIEW
        assert result.decision is Decision.APPROVE

    def test_admin_approve_submitted_to_engineering_review(self):
        result = apply_transition(
            request(stage=ChangeStage.SUBMITTED), admin(), WorkflowAction.APPROVE
        )
        assert result.to_stage is ChangeStage.ENGINEERING_REVIEW

    def test_reviewer_approve_engineering_to_manufacturing(self):
        result = apply_transition(
            request(stage=ChangeStage.ENGINEERING_REVIEW), reviewer(), WorkflowAction.APPROVE
        )
        assert result.to_stage is ChangeStage.MANUFACTURING_REVIEW
        assert result.action == "MOVED_TO_MANUFACTURING_REVIEW"

    def test_admin_approve_engineering_to_manufacturing(self):
        result = apply_transition(
            request(stage=ChangeStage.ENGINEERING_REVIEW), admin(), WorkflowAction.APPROVE
        )
        assert result.to_stage is ChangeStage.MANUFACTURING_REVIEW

    @pytest.mark.parametrize("actor", [reviewer(), admin()])
    def test_request_changes_from_engineering_to_draft(self, actor):
        result = apply_transition(
            request(stage=ChangeStage.ENGINEERING_REVIEW),
            actor,
            WorkflowAction.REQUEST_CHANGES,
        )
        assert result.to_stage is ChangeStage.DRAFT
        assert result.decision is Decision.REQUEST_CHANGES

    @pytest.mark.parametrize("actor", [reviewer(), admin()])
    def test_request_changes_from_manufacturing_to_draft(self, actor):
        result = apply_transition(
            request(stage=ChangeStage.MANUFACTURING_REVIEW),
            actor,
            WorkflowAction.REQUEST_CHANGES,
        )
        assert result.to_stage is ChangeStage.DRAFT

    @pytest.mark.parametrize("actor", [reviewer(), admin()])
    def test_reject_from_engineering_review(self, actor):
        result = apply_transition(
            request(stage=ChangeStage.ENGINEERING_REVIEW), actor, WorkflowAction.REJECT
        )
        assert result.to_stage is ChangeStage.REJECTED
        assert result.decision is Decision.REJECT

    @pytest.mark.parametrize("actor", [reviewer(), admin()])
    def test_reject_from_manufacturing_review(self, actor):
        result = apply_transition(
            request(stage=ChangeStage.MANUFACTURING_REVIEW), actor, WorkflowAction.REJECT
        )
        assert result.to_stage is ChangeStage.REJECTED

    @pytest.mark.parametrize("actor", [reviewer(), admin()])
    def test_approve_manufacturing_to_approved(self, actor):
        result = apply_transition(
            request(stage=ChangeStage.MANUFACTURING_REVIEW), actor, WorkflowAction.APPROVE
        )
        assert result.to_stage is ChangeStage.APPROVED
        assert result.action == "APPROVED"
        assert result.decision is Decision.APPROVE

    def test_high_risk_first_engineering_approval_stays_in_stage(self):
        result = apply_transition(
            request(stage=ChangeStage.ENGINEERING_REVIEW, risk=RiskLevel.HIGH),
            reviewer(),
            WorkflowAction.APPROVE,
        )
        assert (result.from_stage, result.to_stage) == (
            ChangeStage.ENGINEERING_REVIEW,
            ChangeStage.ENGINEERING_REVIEW,
        )
        assert result.decision is Decision.APPROVE

    def test_high_risk_second_distinct_approval_advances(self):
        result = apply_transition(
            request(stage=ChangeStage.ENGINEERING_REVIEW, risk=RiskLevel.HIGH),
            admin(),
            WorkflowAction.APPROVE,
            approvals=[approval(ChangeStage.ENGINEERING_REVIEW, reviewer_id=REVIEWER_ID)],
        )
        assert result.to_stage is ChangeStage.MANUFACTURING_REVIEW


class TestRejectedTransitions:
    def test_submit_only_from_draft(self):
        with pytest.raises(InvalidTransition):
            apply_transition(
                request(stage=ChangeStage.SUBMITTED), requester(), WorkflowAction.SUBMIT
            )

    def test_non_owner_cannot_submit(self):
        with pytest.raises(PermissionDenied):
            apply_transition(request(), admin(), WorkflowAction.SUBMIT)

    def test_requester_cannot_approve(self):
        with pytest.raises(PermissionDenied):
            apply_transition(
                request(stage=ChangeStage.SUBMITTED), requester(), WorkflowAction.APPROVE
            )

    def test_requester_cannot_request_changes(self):
        with pytest.raises(PermissionDenied):
            apply_transition(
                request(stage=ChangeStage.ENGINEERING_REVIEW),
                requester(),
                WorkflowAction.REQUEST_CHANGES,
            )

    def test_requester_cannot_reject(self):
        with pytest.raises(PermissionDenied):
            apply_transition(
                request(stage=ChangeStage.MANUFACTURING_REVIEW),
                requester(),
                WorkflowAction.REJECT,
            )

    def test_request_changes_at_submitted_is_invalid(self):
        with pytest.raises(InvalidTransition):
            apply_transition(
                request(stage=ChangeStage.SUBMITTED),
                reviewer(),
                WorkflowAction.REQUEST_CHANGES,
            )

    def test_reject_at_submitted_is_invalid(self):
        with pytest.raises(InvalidTransition):
            apply_transition(
                request(stage=ChangeStage.SUBMITTED), reviewer(), WorkflowAction.REJECT
            )

    def test_approve_at_draft_is_invalid(self):
        with pytest.raises(InvalidTransition):
            apply_transition(request(), reviewer(), WorkflowAction.APPROVE)

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
    def test_terminal_stages_reject_all_actions(self, stage, action):
        with pytest.raises(InvalidTransition):
            apply_transition(request(stage=stage), reviewer(), action)

    def test_self_approval_denied_for_reviewer(self):
        with pytest.raises(PermissionDenied):
            apply_transition(
                request(stage=ChangeStage.SUBMITTED, owner=REVIEWER_ID),
                reviewer(),
                WorkflowAction.APPROVE,
            )

    def test_self_approval_denied_for_admin(self):
        with pytest.raises(PermissionDenied):
            apply_transition(
                request(stage=ChangeStage.ENGINEERING_REVIEW, owner=ADMIN_ID),
                admin(),
                WorkflowAction.APPROVE,
            )

    def test_duplicate_approval_same_stage_denied(self):
        with pytest.raises(InvalidTransition):
            apply_transition(
                request(stage=ChangeStage.ENGINEERING_REVIEW),
                reviewer(),
                WorkflowAction.APPROVE,
                approvals=[approval(ChangeStage.ENGINEERING_REVIEW)],
            )

    def test_high_risk_same_reviewer_twice_denied(self):
        with pytest.raises(InvalidTransition):
            apply_transition(
                request(stage=ChangeStage.ENGINEERING_REVIEW, risk=RiskLevel.HIGH),
                reviewer(),
                WorkflowAction.APPROVE,
                approvals=[approval(ChangeStage.ENGINEERING_REVIEW)],
            )

    def test_submit_own_draft_after_review_denied_for_owner(self):
        with pytest.raises(InvalidTransition):
            apply_transition(
                request(stage=ChangeStage.SUBMITTED, owner=REQUESTER_ID),
                requester(),
                WorkflowAction.SUBMIT,
            )

    def test_approve_at_manufacturing_duplicate_denied(self):
        with pytest.raises(InvalidTransition):
            apply_transition(
                request(stage=ChangeStage.MANUFACTURING_REVIEW),
                reviewer(),
                WorkflowAction.APPROVE,
                approvals=[approval(ChangeStage.MANUFACTURING_REVIEW)],
            )


class TestEditPermissions:
    def test_owner_can_edit_draft(self):
        assert_can_edit(REQUESTER_ID, REQUESTER_ID, ChangeStage.DRAFT)

    def test_non_owner_edit_denied(self):
        with pytest.raises(PermissionDenied):
            assert_can_edit(REQUESTER_ID, ADMIN_ID, ChangeStage.DRAFT)

    def test_edit_after_draft_denied(self):
        with pytest.raises(InvalidTransition):
            assert_can_edit(REQUESTER_ID, REQUESTER_ID, ChangeStage.SUBMITTED)
