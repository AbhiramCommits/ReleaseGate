import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RequestsPage from "../RequestsPage";
import { server } from "../../test/mocks/server";
import { EMPTY_CONNECTION, gql, okResponse } from "../../test/mocks/handlers";
import { renderWithProviders } from "../../test/utils";

describe("RequestsPage filters", () => {
  it("updates the query variables when stage and risk filters change", async () => {
    const captured: unknown[] = [];
    server.use(
      gql.query("ChangeRequests", ({ variables }) => {
        captured.push(variables);
        return okResponse({ changeRequests: EMPTY_CONNECTION });
      }),
    );

    const user = userEvent.setup();
    renderWithProviders(<RequestsPage />, "/requests");

    await screen.findByText("No change requests match the current filters.");

    await user.selectOptions(
      screen.getByLabelText("Stage filter"),
      "SUBMITTED",
    );
    await waitFor(() => {
      expect(captured[captured.length - 1]).toMatchObject({
        stage: "SUBMITTED",
      });
    });

    await user.selectOptions(screen.getByLabelText("Risk filter"), "HIGH");
    await waitFor(() => {
      expect(captured[captured.length - 1]).toMatchObject({
        stage: "SUBMITTED",
        riskLevel: "HIGH",
      });
    });

    await user.selectOptions(screen.getByLabelText("Stage filter"), "");
    await waitFor(() => {
      expect(captured[captured.length - 1]).toMatchObject({
        riskLevel: "HIGH",
      });
      expect(captured[captured.length - 1]).not.toHaveProperty("stage");
    });
  });
});
