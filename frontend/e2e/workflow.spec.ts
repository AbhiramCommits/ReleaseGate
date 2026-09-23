import { expect, test } from "@playwright/test";

const TITLE = `E2E workflow ${Date.now()}`;

async function login(page: import("@playwright/test").Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/requests$/);
}

test("requester creates and submits; reviewer approves through both review stages", async ({
  page,
}) => {
  await login(page, "requester@releasegate.dev");

  await page.getByRole("link", { name: "New Request" }).click();
  await page.getByLabel("Title").fill(TITLE);
  await page
    .getByLabel("Description")
    .fill("End-to-end workflow verification request.");
  await page.getByLabel("Vehicle Program").fill("Voyager");
  await page.getByLabel("Subsystem").fill("ADAS");
  await page.getByLabel("Risk Level").selectOption("MEDIUM");
  await page.getByRole("button", { name: "Create Request" }).click();

  await expect(page.getByTestId("stage-badge")).toHaveText("Draft");

  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByTestId("stage-badge")).toHaveText("Submitted");

  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await login(page, "reviewer@releasegate.dev");

  await page.getByRole("link", { name: TITLE }).click();
  await expect(page.getByTestId("stage-badge")).toHaveText("Submitted");

  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByTestId("stage-badge")).toHaveText(
    "Engineering Review",
  );

  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByTestId("stage-badge")).toHaveText(
    "Manufacturing Review",
  );

  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByTestId("stage-badge")).toHaveText("Approved");

  await expect(page.getByRole("button", { name: "Approve" })).toHaveCount(0);

  const timeline = page.getByTestId("audit-timeline");
  await expect(timeline.locator("li")).toHaveCount(5);
  await expect(timeline).toContainText("CREATED");
  await expect(timeline).toContainText("SUBMITTED");
  await expect(timeline).toContainText("MOVED_TO_ENGINEERING_REVIEW");
  await expect(timeline).toContainText("MOVED_TO_MANUFACTURING_REVIEW");
  await expect(timeline).toContainText("APPROVED");
});
