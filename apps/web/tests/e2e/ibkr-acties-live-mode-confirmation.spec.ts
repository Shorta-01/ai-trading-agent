import { expect, test, type Route } from "@playwright/test";

/**
 * V1.2 §BZ vervolg — e2e voor het live-mode bulk-submit pad.
 *
 * Bewijst end-to-end (mocked) dat de operator een DUIDELIJK
 * onderscheidbare flow ziet wanneer de IBKR-sessie tegen een live
 * account verbindt:
 *
 *   1. Knop "Verzend alle X orders" toont ⚠️ + LIVE in de tekst en
 *      ``data-account-mode="live"`` op de DOM-node.
 *   2. Klik opent de bulk-submit modal met een rood warning-block
 *      (``action-draft-bulk-submit-live-warning``) dat het masked
 *      account-id en "ECHT geld" toont.
 *   3. Confirm-button noemt LIVE expliciet.
 *
 * Het paper-pad blijft ongewijzigd (geen rode UI bij paper) — getest
 * via de unit-tests in ``ActionDraftGrid.test.tsx``; deze e2e focust
 * specifiek op het live-pad omdat dat het meest impactvol is.
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

const APPROVED_DRAFT = {
  action_draft_id: "draft-live-1",
  decision_package_id: "dp-live-1",
  forecast_run_id: "fcst-live-1",
  created_at: "2026-05-26T07:05:00+00:00",
  created_by: "user",
  ibkr_account_id: "U7654321",
  conid: "12345",
  symbol: "AAPL",
  exchange: "NASDAQ",
  currency_local: "USD",
  side: "BUY",
  quantity: "10",
  order_type: "LMT",
  limit_price_local: "170.00",
  time_in_force: "DAY",
  notional_local: "1700.00",
  notional_eur: "1564.00",
  fx_rate_at_creation: "0.92",
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
  audit_trail_hash: "h-live-1",
  previous_draft_hash: null,
  safe_for_submission: false,
  submission_block_reason: null,
  submission_started_at: null,
  terminal_state_at: null,
};

test.describe("IBKR-acties live-mode confirmation", () => {
  test.beforeEach(async ({ context, page }) => {
    // Catch-all 503 zodat we expliciet alle benodigde routes mocken.
    await context.route("**/*", async (route) => {
      const url = route.request().url();
      const isApi =
        url.includes("/action-draft/")
        || url.includes("/ibkr-submission/")
        || url.includes("/ibkr/account/mode")
        || url.includes("/system/events/active")
        || url.startsWith("http://127.0.0.1:3100")
        || url.startsWith("http://localhost:3100");
      if (isApi) return route.fallback();
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Mock catch-all: 503." }),
      });
    });

    // KERN VAN DE TEST: account-mode endpoint → live.
    await context.route(
      "**/ibkr/account/mode",
      fulfillJson({
        status: "ok",
        mode: "live",
        display_label: "LIVE",
        expected_environment: "paper",
        detected_source: "connected_session",
        hint_account_id_masked: "DU•••4567",
        actual_account_id_masked: "U7•••4321",
        hint_mismatch: true,
        hint_mismatch_nl:
          "De geconfigureerde IBKR_ACCOUNT_ID_HINT (DU•••4567) verschilt van het actueel verbonden account (U7•••4321).",
        help_nl: "",
        safe_for_orders: false,
        blocks_orders: true,
      }),
    );

    // Approved draft in de Te keuren stage.
    await context.route(
      "**/action-draft/te-keuren**",
      fulfillJson({
        ibkr_account_id: "U7654321",
        drafts: [APPROVED_DRAFT],
        safe_for_submission: false,
      }),
    );

    // System events endpoint (de banner gebruikt 'em ook).
    await context.route(
      "**/system/events/active",
      fulfillJson({ events: [] }),
    );

    page.on("dialog", async (dialog) => {
      await dialog.accept();
    });
  });

  test("bulk-submit button reflects LIVE mode with warning indicators", async ({
    page,
  }) => {
    await page.goto("/ibkr-acties");

    const button = page.getByTestId("action-draft-bulk-submit-button");
    await expect(button).toBeVisible();
    await expect(button).toHaveAttribute("data-account-mode", "live");
    await expect(button).toContainText("LIVE");
    await expect(button).toContainText("⚠️");
  });

  test("opening the modal shows the LIVE warning block with masked account-id", async ({
    page,
  }) => {
    await page.goto("/ibkr-acties");

    const button = page.getByTestId("action-draft-bulk-submit-button");
    await expect(button).toBeVisible();
    await button.click();

    // De live-warning block moet zichtbaar zijn en de gemaskeerde
    // U7•••4321 + "ECHT geld" tonen.
    const warning = page.getByTestId(
      "action-draft-bulk-submit-live-warning",
    );
    await expect(warning).toBeVisible();
    await expect(warning).toContainText("LIVE");
    await expect(warning).toContainText("U7•••4321");
    await expect(warning).toContainText("ECHT geld");

    // Confirm-button bevat LIVE.
    const confirm = page.getByTestId(
      "action-draft-bulk-submit-modal-confirm",
    );
    await expect(confirm).toContainText("LIVE");
  });
});
