import { expect, test, type Route } from "@playwright/test";

/**
 * Task 132 Playwright: navigate from Volglijst → ForecastExplanationPanel →
 * Decision Package detail page. Mocks every API the path touches so the
 * test runs without a live API.
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

const CONFIRMED = {
  account_id: "DU1234567",
  state: "confirmed" as const,
  banner_text: null,
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const WATCHLIST_ITEMS = {
  items: [
    {
      item: {
        watchlist_item_id: "wi-asml",
        symbol: "ASML",
        ibkr_conid: "ASML.AS",
      },
      ibkr_status_label_nl: "Gevalideerd",
      asset_listing_readiness: {
        status_nl: "Klaar",
        next_step_nl: "Geen actie",
      },
    },
  ],
};

const FORECASTS_BY_ACCOUNT = {
  account_id: "DU1234567",
  items: [
    {
      conid: "ASML.AS",
      label: "Bekijken",
      confidence_level: "Hoog",
      generated_at: "2026-05-25T07:00:00+00:00",
      p50_log_return: "0.02",
      prob_positive: "0.62",
      user_holds_position: false,
    },
  ],
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const DAY_SUMMARY = {
  account_id: "DU1234567",
  as_of_date: "2026-05-25",
  total_forecasts: 1,
  total_blocked: 0,
  label_counts: { Bekijken: 1 },
  block_reasons: {},
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const FORECAST_LATEST = {
  conid: "ASML.AS",
  generated_at: "2026-05-25T07:00:00+00:00",
  forecast_valid_until: "2026-06-22T07:00:00+00:00",
  horizon_trading_days: 20,
  method: "historical_bootstrap_v1",
  current_price_local: "640.00000000",
  currency_local: "EUR",
  p10_log_return: "-0.05",
  p50_log_return: "0.02",
  p90_log_return: "0.08",
  p10_price_local: "608.769000",
  p50_price_local: "652.929000",
  p90_price_local: "693.282000",
  p10_price_eur: "608.769000",
  p50_price_eur: "652.929000",
  p90_price_eur: "693.282000",
  prob_positive: "0.62",
  prob_loss_gt_5pct: "0.12",
  expected_volatility_annualized: "0.25",
  confidence_level: "Hoog",
  label: "Bekijken",
  block_reason: null,
  per_asset_coverage: {
    forecasts_evaluated: 0,
    hit_rate_within_band: null,
    sufficient_history: false,
  },
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const DECISION_PACKAGE = {
  decision_package_id: "dp-e2e-1",
  forecast_run_id: "fcst-e2e-1",
  composed_at: "2026-05-25T07:00:30+00:00",
  valid_until: "2026-06-22T07:00:00+00:00",
  ibkr_account_id: "DU1234567",
  conid: "ASML.AS",
  symbol: "ASML",
  exchange: "AEB",
  currency_local: "EUR",
  asset_class: "STK",
  user_holds_position: false,
  held_quantity: null,
  held_avg_cost_local: null,
  current_price_local: "640.00000000",
  current_price_eur: "640.00000000",
  as_of_market_data_ts: "2026-05-24T20:00:00+00:00",
  freshness_state: "fresh",
  data_age_trading_days: 0,
  forecast_method: "historical_bootstrap_v1",
  p10_log_return: "-0.05",
  p50_log_return: "0.02",
  p90_log_return: "0.08",
  p10_price_eur: "608.769000",
  p50_price_eur: "652.929000",
  p90_price_eur: "693.282000",
  prob_positive: "0.62",
  prob_loss_gt_5pct: "0.12",
  expected_volatility_annualized: "0.25",
  forecast_confidence_level: "Hoog",
  suggested_action_label: "Bekijken",
  block_reason: null,
  gate_outcomes: [
    { gate_name: "forecast_valid", passed: true, reason_nl: "" },
    { gate_name: "data_fresh", passed: true, reason_nl: "" },
    { gate_name: "asset_listing_resolved", passed: true, reason_nl: "" },
    { gate_name: "freshness_within_sla", passed: true, reason_nl: "" },
    { gate_name: "confidence_at_least_medium", passed: true, reason_nl: "" },
  ],
  evidence_references: [
    {
      source_id: "snap-1",
      source_type: "market_data_snapshot",
      claim_summary: "EOD-snapshot voor ASML op 24 mei 2026",
    },
  ],
  deterministic_dutch_explanation:
    "Voor ASML duidt de voorspelling op een signaal om te bekijken (label: Bekijken) over de komende 20 handelsdagen.",
  audit_trail_hash:
    "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
  previous_package_hash: null,
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const MARKET_DATA_STATUS = {
  status: "snapshot_available",
  status_nl: "Snapshot beschikbaar",
  price_basis_nl: "Snapshot",
  valuation_readiness_status: "ready_for_status_only",
};


test.describe("Decision Package navigation from Volglijst", () => {
  test.beforeEach(async ({ context }) => {
    await context.route("**/*", async (route) => {
      const url = route.request().url();
      const isApi =
        url.includes("/watchlist/") ||
        url.includes("/forecast/") ||
        url.includes("/decision-package/") ||
        url.includes("/market-data/") ||
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
      "**/watchlist/confirmation-state",
      fulfillJson(CONFIRMED),
    );
    await context.route(
      "**/watchlist/items",
      fulfillJson(WATCHLIST_ITEMS),
    );
    await context.route(
      "**/market-data/eod/snapshots/latest**",
      fulfillJson(MARKET_DATA_STATUS),
    );
    await context.route(
      "**/forecast/by-account**",
      fulfillJson(FORECASTS_BY_ACCOUNT),
    );
    await context.route(
      "**/forecast/day-summary**",
      fulfillJson(DAY_SUMMARY),
    );
    await context.route(
      "**/forecast/latest?conid=ASML.AS",
      fulfillJson(FORECAST_LATEST),
    );
    await context.route(
      "**/decision-package/latest?conid=ASML.AS**",
      fulfillJson(DECISION_PACKAGE),
    );
    await context.route(
      `**/decision-package/${DECISION_PACKAGE.decision_package_id}`,
      fulfillJson(DECISION_PACKAGE),
    );
  });

  test("Volglijst → Waarom? → Bekijk Decision Package → all seven sections render", async ({
    page,
  }) => {
    await page.goto("/volglijst");

    await expect(
      page.getByTestId("volglijst-forecast-label-ASML"),
    ).toHaveText("Bekijken");

    await page.getByTestId("volglijst-forecast-why-ASML").click();

    const bekijkButton = page.getByTestId("forecast-bekijk-decision-package");
    await expect(bekijkButton).toBeVisible();
    await bekijkButton.click();

    await expect(page).toHaveURL(/\/decision-package\/dp-e2e-1/);

    // All seven sections render.
    await expect(page.getByTestId("dp-section-header")).toBeVisible();
    await expect(page.getByTestId("dp-section-forecast")).toBeVisible();
    await expect(page.getByTestId("dp-section-current")).toBeVisible();
    await expect(page.getByTestId("dp-section-gates")).toBeVisible();
    await expect(page.getByTestId("dp-section-evidence")).toBeVisible();
    await expect(page.getByTestId("dp-section-explanation")).toBeVisible();
    await expect(page.getByTestId("dp-section-audit")).toBeVisible();

    // Label badge color-coded.
    await expect(page.getByTestId("dp-label-badge")).toHaveText("Bekijken");
  });

  test("Suggesties page shows the explainer-only empty state", async ({
    page,
  }) => {
    await page.goto("/suggesties");
    await expect(
      page.getByTestId("suggesties-empty-state-explainer"),
    ).toContainText("Suggesties komen binnenkort");
    await expect(
      page.getByTestId("suggesties-empty-state-explainer"),
    ).toContainText("Bekijk Decision Package");
  });
});
