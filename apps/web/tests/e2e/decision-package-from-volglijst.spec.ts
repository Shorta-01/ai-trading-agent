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
    // Task 132 hot-fix v3: scope route patterns to the API host
    // (localhost:8000) so the mocks do NOT intercept the Next.js
    // page navigation (127.0.0.1:3100). Previously the regex
    // ``/\/decision-package\/dp-e2e-1$/`` matched both:
    //   * API call:        http://localhost:8000/decision-package/dp-e2e-1
    //   * Page navigation: http://127.0.0.1:3100/decision-package/dp-e2e-1
    // The click on "Bekijk Decision Package" got the JSON response
    // back instead of the Next.js page HTML — the browser rendered
    // the JSON as text content. Anchoring to the API host fixes it.
    const API_HOST = "localhost:8000";
    await context.route(
      new RegExp(`^https?://${API_HOST}/forecast/latest\\?conid=ASML\\.AS`),
      fulfillJson(FORECAST_LATEST),
    );
    await context.route(
      new RegExp(
        `^https?://${API_HOST}/decision-package/latest\\?conid=ASML\\.AS`,
      ),
      fulfillJson(DECISION_PACKAGE),
    );
    await context.route(
      new RegExp(
        `^https?://${API_HOST}/decision-package/${DECISION_PACKAGE.decision_package_id}$`,
      ),
      fulfillJson(DECISION_PACKAGE),
    );
  });

  test("Volglijst → Waarom? → Bekijk Decision Package → all seven sections render", async ({
    page,
  }) => {
    await page.goto("/volglijst");

    // Volglijst-cleanup PR: action labels no longer render on
    // Volglijst rows (those moved to /suggesties). The forecast
    // band + "Waarom?" button still live here for tracking.
    await expect(
      page.getByTestId("volglijst-forecast-interval-ASML"),
    ).toBeVisible();

    await page.getByTestId("volglijst-forecast-why-ASML").click();

    const bekijkButton = page.getByTestId("forecast-bekijk-decision-package");
    await expect(bekijkButton).toBeVisible();
    await bekijkButton.click();

    await expect(page).toHaveURL(/\/decision-package\/dp-e2e-1/);

    // Task 132 hot-fix regression assertion: surface the stuck-loading
    // failure mode as a distinct error rather than burying it in the
    // per-section visibility timeouts below. The original bug was
    // ``use(params)`` suspending without a Suspense boundary, leaving
    // the page rendering only the loading state forever.
    await expect(
      page.getByTestId("decision-package-loading"),
    ).toHaveCount(0, { timeout: 10_000 });

    // All seven sections render.
    await expect(page.getByTestId("dp-section-header")).toBeVisible();
    await expect(page.getByTestId("dp-section-forecast")).toBeVisible();
    await expect(page.getByTestId("dp-section-current")).toBeVisible();
    await expect(page.getByTestId("dp-section-gates")).toBeVisible();
    await expect(page.getByTestId("dp-section-evidence")).toBeVisible();
    await expect(page.getByTestId("dp-section-explanation")).toBeVisible();
    await expect(page.getByTestId("dp-section-audit")).toBeVisible();

    // Confirm at least one section carries real text content from the
    // API mock — catches the failure mode where test IDs exist but
    // the page is otherwise broken (e.g. rendered with default
    // placeholders instead of the mocked DECISION_PACKAGE).
    await expect(page.getByTestId("dp-section-header")).toContainText(
      "ASML",
    );
    await expect(
      page.getByTestId("dp-explanation-text"),
    ).toContainText("Voor ASML");

    // Label badge color-coded.
    await expect(page.getByTestId("dp-label-badge")).toHaveText("Bekijken");
  });

  test("Suggesties page renders the v1 grid header", async ({ page }) => {
    await page.goto("/suggesties");
    await expect(page.getByTestId("suggesties-page")).toBeVisible();
    // Page header is locked to the v1 grid title; either the loading
    // placeholder or the final status copy is acceptable as the test
    // runs with whatever storage state the dev fixture provides.
    await expect(page.getByRole("heading", { level: 2 })).toContainText(
      "Suggesties",
    );
  });
});
