import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import RequestDetailPage from "../RequestDetailPage";
import { server } from "../../test/mocks/server";
import {
  detailFixture,
  detailHandler,
  meHandler,
} from "../../test/mocks/handlers";
import { renderWithProviders } from "../../test/utils";
import { Role } from "../../generated/graphql";

function renderDetail(
  detail: Record<string, unknown>,
  meRole: string,
  meId = "me-1",
) {
  server.use(meHandler(meRole, meId), detailHandler(detail));
  renderWithProviders(
    <Routes>
      <Route path="/requests/:id" element={<RequestDetailPage />} />
    </Routes>,
    "/requests/req-1",
  );
}

describe("RequestDetailPage action bar", () => {
  it("shows Submit for the owner while DRAFT", async () => {
    renderDetail(detailFixture(), Role.Requester, "owner-1");
    expect(
      await screen.findByRole("button", { name: "Submit" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Approve" }),
    ).not.toBeInTheDocument();
  });

  it("shows only Approve for a reviewer while SUBMITTED", async () => {
    renderDetail(detailFixture({ currentStage: "SUBMITTED" }), Role.Reviewer);
    expect(
      await screen.findByRole("button", { name: "Approve" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Request Changes" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Reject" }),
    ).not.toBeInTheDocument();
  });

  it("shows all review actions for a reviewer during ENGINEERING_REVIEW", async () => {
    renderDetail(
      detailFixture({ currentStage: "ENGINEERING_REVIEW" }),
      Role.Reviewer,
    );
    expect(
      await screen.findByRole("button", { name: "Approve" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Request Changes" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
  });

  it("hides Approve from the owner-reviewer during ENGINEERING_REVIEW", async () => {
    renderDetail(
      detailFixture({
        currentStage: "ENGINEERING_REVIEW",
        requesterId: "me-1",
      }),
      Role.Reviewer,
      "me-1",
    );
    expect(
      await screen.findByRole("button", { name: "Request Changes" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Approve" }),
    ).not.toBeInTheDocument();
  });

  it("renders no action bar on a terminal stage", async () => {
    renderDetail(detailFixture({ currentStage: "APPROVED" }), Role.Admin);
    await screen.findByText("Approval History");
    expect(
      screen.queryByRole("button", { name: "Approve" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Submit" }),
    ).not.toBeInTheDocument();
  });

  it("renders no action bar for a requester viewing a review stage", async () => {
    renderDetail(
      detailFixture({ currentStage: "MANUFACTURING_REVIEW" }),
      Role.Requester,
      "owner-1",
    );
    await screen.findByText("Approval History");
    expect(
      screen.queryByRole("button", { name: "Approve" }),
    ).not.toBeInTheDocument();
  });
});
