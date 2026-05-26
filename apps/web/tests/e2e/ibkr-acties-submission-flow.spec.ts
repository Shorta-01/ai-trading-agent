import { expect, test, type Route } from "@playwright/test";

/**
 * Task 134c Playwright: full Te keuren → Actief bij IBKR → Historiek
 * navigation flow.
 *
 * Mocks the API surface so the test runs without a live backend.
 * Verifies:
 *   1. Te keuren tab shows a `user_approved` draft.
 *   2. Switching to "Actief bij IBKR" shows the same draft after
 *      we have moved it server-side to `working`.
 *   3. Switching to "Historiek" shows the draft after it has been
 *      moved to `filled`.
 *   4. Clicking the lifecycle button opens the SubmissionLifecycleDrawer
 *      with the events in Dutch.
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

const BASE_DRAFT = {
  action_draft_id: "draft-e2e-1",
  decision_package_id: "dp-e2e-1",
  forecast_run_id: "fcst-e2e-1",
  created_at: "2026-05-26T07:05:00+00:00",
  created_by: "user",
  ibkr_account_id: "DU1234567",
  conid: "12345",
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
  status: "user_approved",
  last_edited_at: null,
  user_approved_at: "2026-05-26T07:10:00+00:00",
  dismissed_at: null,
  deleted_at: null,
  dismissed_reason: null,
  user_note: null,
  superseded_by_decision_package_id: null,
  audit_trail_hash: "h-e2e-1",
  previous_draft_hash: null,
  safe_for_submission: false,
  submission_block_reason: null,
  submission_started_at: null,
  terminal_state_at: null,
};

const LIFECYCLE_EVENTS = [
  {
    id: 1,
    action_draft_id: "draft-e2e-1",
    event_at: "2026-05-26T07:11:00+00:00",
    ibkr_perm_id: 100100,
    event_type: "status_change",
    from_status: "submitted",
    to_status: "accepted",
    ibkr_raw_status: "Submitted",
    fill_price_local: null,
    fill_quantity: null,
    commission: null,
    commission_currency: null,
    raw_callback_json: {},
  },
  {
    id: 2,
    action_draft_id: "draft-e2e-1",
    event_at: "2026-05-26T07:11:05+00:00",
    ibkr_perm_id: 100100,
    event_type: "fill",
    from_status: "working",
    to_status: "filled",
    ibkr_raw_status: null,
    fill_price_local: "638.72",
    fill_quantity: "6",
    commission: null,
    commission_currency: null,
    raw_callback_json: {},
  },
];

test.describe("Task 134c — IBKR Acties three-tab flow", () => {
  test.beforeEach(async ({ context, page }) => {
    await context.route("**/*", async (route) => {
      const url = route.request().url();
      const isApi =
        url.includes("/action-draft/") ||
        url.includes("/ibkr-submission/") ||
        url.startsWith("http://127.0.0.1:3100") ||
        url.startsWith("http://localhost:3100");
      if (isApi) return route.fallback();
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Mock catch-all: 503." }),
      });
    });
    await context.route(
      "**/action-draft/te-keuren**",
      fulfillJson({
        ibkr_account_id: "DU1234567",
        drafts: [BASE_DRAFT],
        safe_for_submission: false,
      }),
    );
    await context.route(
      "**/ibkr-submission/active**",
      fulfillJson({
        ibkr_account_id: "DU1234567",
        drafts: [
          {
            ...BASE_DRAFT,
            status: "working",
            submission_started_at: "2026-05-26T07:11:00+00:00",
          },
        ],
      }),
    );
    await context.route(
      "**/ibkr-submission/historiek**",
      fulfillJson({
        ibkr_account_id: "DU1234567",
        drafts: [
          {
            ...BASE_DRAFT,
            status: "filled",
            submission_started_at: "2026-05-26T07:11:00+00:00",
            terminal_state_at: "2026-05-26T07:11:05+00:00",
          },
        ],
      }),
    );
    await context.route(
      "**/ibkr-submission/lifecycle/**",
      fulfillJson({
        action_draft_id: "draft-e2e-1",
        events: LIFECYCLE_EVENTS,
      }),
    );

    page.on("dialog", async (dialog) => {
      await dialog.accept();
    });
  });

  test("Te keuren tab shows the user-approved draft", async ({
    page,
  }) => {
    await page.goto("/ibkr-acties");
    await expect(
      page.getByTestId("action-draft-row-draft-e2e-1"),
    ).toBeVisible();
    await expect(
      page.getByTestId("action-draft-status-draft-e2e-1"),
    ).toHaveText("Goedgekeurd");
  });

  test("Actief bij IBKR tab shows the same draft in working status", async ({
    page,
  }) => {
    await page.goto("/ibkr-acties");
    await page.getByTestId("ibkr-acties-tab-actief").click();
    await expect(
      page.getByTestId("ibkr-actief-row-draft-e2e-1"),
    ).toBeVisible();
    await expect(
      page.getByTestId("ibkr-grid-status-working"),
    ).toBeVisible();
  });

  test("Historiek tab shows the filled draft", async ({ page }) => {
    await page.goto("/ibkr-acties");
    await page.getByTestId("ibkr-acties-tab-historiek").click();
    await expect(
      page.getByTestId("ibkr-historiek-row-draft-e2e-1"),
    ).toBeVisible();
    await expect(
      page.getByTestId("ibkr-grid-status-filled"),
    ).toBeVisible();
  });

  test("clicking Lifecycle opens the drawer with Dutch events", async ({
    page,
  }) => {
    await page.goto("/ibkr-acties");
    await page.getByTestId("ibkr-acties-tab-actief").click();
    await page
      .getByTestId("ibkr-actief-lifecycle-draft-e2e-1")
      .click();
    await expect(
      page.getByTestId("submission-lifecycle-drawer"),
    ).toBeVisible();
    await expect(
      page.getByTestId("submission-lifecycle-events"),
    ).toBeVisible();
    // Dutch labels rendered for at least one status change + the fill.
    await expect(page.getByText("Statuswijziging").first()).toBeVisible();
    await expect(page.getByText("Uitvoering").first()).toBeVisible();
  });
});
