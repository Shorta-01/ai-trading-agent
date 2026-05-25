import { expect, test, type Route } from "@playwright/test";

/**
 * Task 129 Playwright smoke: Portefeuille shows EOD prices + EUR
 * conversion + freshness badge when the market-data API returns
 * snapshots. Mocks every endpoint so the test runs without a
 * live API or live EODHD.
 */

function fulfillJson(json: object) {
  return async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(json),
    });
  };
}

const PAPER_STATUS = {
  connected: true,
  account_id: "DU•••4567",
  account_mode: "paper" as const,
  verified_at: "2026-05-25T07:00:00+00:00",
  error: null,
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const ASML_POSITION = {
  items: [
    {
      ibkr_account_id: "DU•••4567",
      conid: "265598",
      symbol: "ASML",
      exchange: "AEB",
      primary_exchange: "AEB",
      currency: "EUR",
      security_type: "STK",
      quantity: "12.5",
      avg_cost: "640.123456",
      market_price: null,
      market_value: null,
      unrealized_pnl: null,
      as_of: "2026-05-25T07:00:00+00:00",
    },
  ],
  sync_run_id: "sync-1",
  as_of: "2026-05-25T07:00:00+00:00",
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const EUR_CASH = {
  items: [
    {
      ibkr_account_id: "DU•••4567",
      currency: "EUR",
      cash: "10000.00",
      available_funds: "10000.00",
      buying_power: "40000.00",
      net_liquidation_value: null,
      total_cash_value: null,
      as_of: "2026-05-25T07:00:00+00:00",
    },
  ],
  sync_run_id: "sync-1",
  as_of: "2026-05-25T07:00:00+00:00",
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const MARKET_DATA_FRESH = {
  account_id: "DU1234567",
  items: [
    {
      ibkr_conid: "265598",
      symbol: "ASML",
      exchange: "AEB",
      as_of_date: "2026-05-24",
      close_local: "640.123456",
      currency_local: "EUR",
      close_eur: "640.123456",
      freshness: "fresh" as const,
    },
  ],
  fetched_via: "eodhd",
  as_of_date: "2026-05-24",
  safe_for_action_drafts: false,
  safe_for_orders: false,
};


test.describe("Portefeuille — Task 129 EOD prices", () => {
  test.beforeEach(async ({ context }) => {
    await context.route("**/*", async (route) => {
      const url = route.request().url();
      if (
        url.includes("/ibkr/connection/status") ||
        url.includes("/ibkr/sync/positions/latest") ||
        url.includes("/ibkr/sync/cash/latest") ||
        url.includes("/market-data/eod/snapshots/by-account") ||
        url.startsWith("http://127.0.0.1:3100") ||
        url.startsWith("http://localhost:3100")
      ) {
        return route.fallback();
      }
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Mock catch-all: 503." }),
      });
    });
  });

  test("ASML price + EUR value + Vers badge render with Decimal precision", async ({
    page,
  }) => {
    await page.route(
      "**/ibkr/connection/status",
      fulfillJson(PAPER_STATUS),
    );
    await page.route(
      "**/ibkr/sync/positions/latest",
      fulfillJson(ASML_POSITION),
    );
    await page.route("**/ibkr/sync/cash/latest", fulfillJson(EUR_CASH));
    await page.route(
      "**/market-data/eod/snapshots/by-account",
      fulfillJson(MARKET_DATA_FRESH),
    );

    await page.goto("/portefeuille");

    const grid = page.getByTestId("positions-grid");
    await expect(grid).toBeVisible();
    await expect(grid).toContainText("Verversingsstatus");
    await expect(grid).toContainText("640.123456");
    await expect(grid).toContainText("Waarde (EUR)");
    const subtitle = page.getByTestId("positions-grid-subtitle");
    await expect(subtitle).toContainText("Prijzen bijgewerkt: 2026-05-24");
    await expect(subtitle).toContainText("eodhd");

    // The badge is green/fresh.
    const badges = page.getByTestId("price-freshness-badge");
    await expect(badges.first()).toHaveAttribute("data-state", "fresh");
    await expect(badges.first()).toContainText("Vers");
  });
});
