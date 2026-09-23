import { ChangeStage, Role, WorkflowAction } from "./generated/graphql";

export function allowedActions(
  role: Role | undefined,
  stage: ChangeStage,
  requesterId: string,
  currentUserId: string | undefined,
): WorkflowAction[] {
  const isOwner = currentUserId !== undefined && currentUserId === requesterId;
  const isReviewer = role === Role.Reviewer || role === Role.Admin;

  switch (stage) {
    case ChangeStage.Draft:
      return isOwner ? [WorkflowAction.Submit] : [];
    case ChangeStage.Submitted:
      return isReviewer && !isOwner ? [WorkflowAction.Approve] : [];
    case ChangeStage.EngineeringReview:
    case ChangeStage.ManufacturingReview: {
      if (!isReviewer) {
        return [];
      }
      const actions = [WorkflowAction.RequestChanges, WorkflowAction.Reject];
      if (!isOwner) {
        actions.unshift(WorkflowAction.Approve);
      }
      return actions;
    }
    default:
      return [];
  }
}

export const ACTION_LABELS: Record<WorkflowAction, string> = {
  [WorkflowAction.Submit]: "Submit",
  [WorkflowAction.Approve]: "Approve",
  [WorkflowAction.RequestChanges]: "Request Changes",
  [WorkflowAction.Reject]: "Reject",
};
