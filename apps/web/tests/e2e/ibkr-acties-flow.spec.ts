import { expect, test, type Route } from "@playwright/test";

/**
 * Task 133 Playwright: full IBKR Acties Te keuren flow.
 *
 * Mocks the API surface so the test runs without a live backend:
 *   - GET /action-draft/te-keuren returns one proposed BUY draft.
 *   - POST /action-draft/{id}/approve flips the status to user_approved.
 *
 * Exercises:
 *   1. Page renders all three tabs.
 *   2. Te keuren tab shows the draft row.
 *   3. Clicking Goedkeuren with the "JA" confirmation calls the
 *      approve route and the page re-renders with the Goedgekeurd
 *      badge + Dutch info banner (Task 133 product lock §9).
 */

function fulfillJson(json: object, status = 200) {
  return async (route: Route) => {
    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(json),
    });
  };
}

const DRAFT_PROPOSED = {
  action_draft_id: "draft-e2e-1",
  decision_package_id: "dp-e2e-1",
  forecast_run_id: "fcst-e2e-1",
  created_at: "2026-05-26T07:05:00+00:00",
  created_by: "user",
  ibkr_account_id: "DU1234567",
  conid: "ASML.AS",
  symbol: "ASML",
  exchange: "AEB",
  currency_local: "EUR",
  side: "BUY",
  quantity: "6",
  order_type: "LMT",
  limit_price_local: "638.72000000",
  time_in_force: "DAY",
  notional_local: "3832.32000000",
  notional_eur: "3832.32000000",
  fx_rate_at_creation: "1",
  usable_cash_eur_at_creation: "50000",
  held_quantity_at_creation: null,
  status: "proposed",
  last_edited_at: null,
  user_approved_at: null,
  dismissed_at: null,
  deleted_at: null,
  dismissed_reason: null,
  user_note: null,
  superseded_by_decision_package_id: null,
  audit_trail_hash: "h-e2e-1",
  previous_draft_hash: null,
  safe_for_submission: false,
};

const DRAFT_APPROVED = {
  ...DRAFT_PROPOSED,
  status: "user_approved",
  user_approved_at: "2026-05-26T07:10:00+00:00",
};

test.describe("Task 133 — IBKR Acties Te keuren flow", () => {
  test.beforeEach(async ({ context, page }) => {
    let approveCalled = false;
    await context.route("**/*", async (route) => {
      const url = route.request().url();
      const isApi =
        url.includes("/action-draft/") ||
        url.startsWith("http://127.0.0.1:3100") ||
        url.startsWith("http://localhost:3100");
      if (isApi) return route.fallback();
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Mock catch-all: 503." }),
      });
    });
    await context.route("**/action-draft/te-keuren**", async (route) => {
      await fulfillJson({
        ibkr_account_id: "DU1234567",
        drafts: [approveCalled ? DRAFT_APPROVED : DRAFT_PROPOSED],
        safe_for_submission: false,
      })(route);
    });
    await context.route(
      "**/action-draft/draft-e2e-1/approve",
      async (route) => {
        approveCalled = true;
        await fulfillJson(DRAFT_APPROVED)(route);
      },
    );

    // Confirm JA on the approve prompt automatically.
    page.on("dialog", async (dialog) => {
      await dialog.accept("JA");
    });
  });

  test("renders three tabs", async ({ page }) => {
    await page.goto("/ibkr-acties");
    await expect(page.getByTestId("ibkr-acties-tab-te-keuren")).toBeVisible();
    await expect(page.getByTestId("ibkr-acties-tab-actief")).toBeVisible();
    await expect(page.getByTestId("ibkr-acties-tab-historiek")).toBeVisible();
  });

  test("Te keuren tab lists the proposed draft", async ({ page }) => {
    await page.goto("/ibkr-acties");
    await expect(
      page.getByTestId("action-draft-row-draft-e2e-1"),
    ).toBeVisible();
    await expect(
      page.getByTestId("action-draft-side-draft-e2e-1"),
    ).toHaveText("BUY");
    await expect(
      page.getByTestId("action-draft-status-draft-e2e-1"),
    ).toHaveText("Voorgesteld");
  });

  test("approving via JA prompt flips status and shows the Dutch info banner", async ({
    page,
  }) => {
    await page.goto("/ibkr-acties");
    await page
      .getByTestId("action-draft-approve-draft-e2e-1")
      .click();
    await expect(
      page.getByTestId("action-draft-status-draft-e2e-1"),
    ).toHaveText("Goedgekeurd");
    await expect(
      page.getByTestId("action-draft-approved-banner-draft-e2e-1"),
    ).toContainText("IBKR-verzending wordt in een toekomstige update");
  });
});
