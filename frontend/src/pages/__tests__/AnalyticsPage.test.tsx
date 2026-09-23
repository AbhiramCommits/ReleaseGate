import { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import AnalyticsPage from "../AnalyticsPage";
import { server } from "../../test/mocks/server";
import { gql, okResponse } from "../../test/mocks/handlers";
import { renderWithProviders } from "../../test/utils";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children?: ReactNode }) => (
    <div>{children}</div>
  ),
  BarChart: ({ children }: { children?: ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}));

describe("AnalyticsPage", () => {
  it("renders stat tiles, slowest-stage callout, and chart with mocked data", async () => {
    server.use(
      gql.query("CycleTime", () =>
        okResponse({
          cycleTimeAnalytics: {
            stageMetrics: [
              { stage: "DRAFT", averageHours: 24, medianHours: 24, samples: 2 },
              {
                stage: "SUBMITTED",
                averageHours: 10,
                medianHours: 10,
                samples: 1,
              },
              {
                stage: "ENGINEERING_REVIEW",
                averageHours: 8,
                medianHours: 8,
                samples: 1,
              },
              {
                stage: "MANUFACTURING_REVIEW",
                averageHours: 6,
                medianHours: 6,
                samples: 1,
              },
              {
                stage: "APPROVED",
                averageHours: null,
                medianHours: null,
                samples: 0,
              },
              {
                stage: "REJECTED",
                averageHours: null,
                medianHours: null,
                samples: 0,
              },
            ],
            currentStageCounts: [
              { stage: "DRAFT", count: 1 },
              { stage: "SUBMITTED", count: 2 },
              { stage: "ENGINEERING_REVIEW", count: 3 },
              { stage: "MANUFACTURING_REVIEW", count: 4 },
              { stage: "APPROVED", count: 5 },
              { stage: "REJECTED", count: 1 },
            ],
            endToEndAverageHours: 36,
            topSlowestStages: [
              {
                stage: "ENGINEERING_REVIEW",
                averageHours: 8,
                medianHours: 8,
                samples: 1,
              },
            ],
          },
        }),
      ),
    );

    renderWithProviders(<AnalyticsPage />, "/analytics");

    expect(await screen.findByText("36.0 h")).toBeInTheDocument();
    expect(screen.getByText("Avg end-to-end approval")).toBeInTheDocument();

    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("In-flight requests")).toBeInTheDocument();

    expect(screen.getByText("16")).toBeInTheDocument();
    expect(screen.getByText("Total requests")).toBeInTheDocument();

    const callout = screen.getByText(/Slowest stage:/).parentElement;
    expect(callout).not.toBeNull();
    expect(callout).toHaveTextContent("Engineering Review");
    expect(callout).toHaveTextContent("8.0 h");
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });
});
