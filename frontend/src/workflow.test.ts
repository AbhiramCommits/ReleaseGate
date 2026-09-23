import { describe, expect, it } from "vitest";
import { ChangeStage, Role, WorkflowAction } from "./generated/graphql";
import { allowedActions, optimisticNextStage } from "./workflow";

describe("optimisticNextStage", () => {
  it("maps SUBMIT to SUBMITTED", () => {
    expect(optimisticNextStage(WorkflowAction.Submit, ChangeStage.Draft)).toBe(
      ChangeStage.Submitted,
    );
  });

  it("maps APPROVE through the review chain", () => {
    expect(optimisticNextStage(WorkflowAction.Approve, ChangeStage.Submitted)).toBe(
      ChangeStage.EngineeringReview,
    );
    expect(optimisticNextStage(WorkflowAction.Approve, ChangeStage.EngineeringReview)).toBe(
      ChangeStage.ManufacturingReview,
    );
    expect(optimisticNextStage(WorkflowAction.Approve, ChangeStage.ManufacturingReview)).toBe(
      ChangeStage.Approved,
    );
  });

  it("maps REQUEST_CHANGES to DRAFT and REJECT to REJECTED", () => {
    expect(optimisticNextStage(WorkflowAction.RequestChanges, ChangeStage.EngineeringReview)).toBe(
      ChangeStage.Draft,
    );
    expect(optimisticNextStage(WorkflowAction.Reject, ChangeStage.ManufacturingReview)).toBe(
      ChangeStage.Rejected,
    );
  });

  it("leaves terminal stages unchanged", () => {
    expect(optimisticNextStage(WorkflowAction.Approve, ChangeStage.Approved)).toBe(
      ChangeStage.Approved,
    );
  });
});

describe("allowedActions", () => {
  it("gives the requester owner only Submit in DRAFT", () => {
    expect(allowedActions(Role.Requester, ChangeStage.Draft, "me", "me")).toEqual([
      WorkflowAction.Submit,
    ]);
  });

  it("hides every action at terminal stages", () => {
    expect(allowedActions(Role.Reviewer, ChangeStage.Approved, "owner", "me")).toEqual([]);
    expect(allowedActions(Role.Admin, ChangeStage.Rejected, "owner", "me")).toEqual([]);
  });
});
