import { expect, test, type Route } from "@playwright/test";

/**
 * Task 126b smoke: visit /portefeuille, mock the API responses,
 * assert the AccountModeBadge appears, the cash card renders, the
 * positions grid has the locked Dutch headers, and the empty +
 * disconnected states surface the right Dutch microcopy.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function mockRoute(json: object) {
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

const DISCONNECTED_STATUS = {
  connected: false,
  account_id: null,
  account_mode: "unknown" as const,
  verified_at: null,
  error: null,
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const ONE_POSITION = {
  items: [
    {
      ibkr_account_id: "DU•••4567",
      conid: "265598",
      symbol: "AAPL",
      exchange: "SMART",
      primary_exchange: "NASDAQ",
      currency: "USD",
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

const EMPTY_POSITIONS = {
  items: [],
  sync_run_id: "sync-1",
  as_of: "2026-05-25T07:00:00+00:00",
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const ONE_CASH = {
  items: [
    {
      ibkr_account_id: "DU•••4567",
      currency: "EUR",
      cash: "12345.67",
      available_funds: "11000.00",
      buying_power: "44000.00",
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

async function mockOtherEndpointsAsEmpty(context: import("@playwright/test").BrowserContext) {
  // The Portefeuille page calls many other endpoints that aren't the
  // focus of this smoke. Mock the most expensive ones as empty/404 so
  // the page doesn't hang on real network calls.
  await context.route(`${API_BASE}/**`, async (route) => {
    const url = route.request().url();
    // The four /ibkr/connection + /ibkr/sync endpoints are handled by
    // per-test routes installed before this catch-all; the
    // catch-all only fires for everything else.
    if (
      url.includes("/ibkr/connection/status") ||
      url.includes("/ibkr/connection/audit") ||
      url.includes("/ibkr/sync/positions/latest") ||
      url.includes("/ibkr/sync/cash/latest")
    ) {
      return route.fallback();
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [] }),
    });
  });
}

test.describe("Portefeuille — Task 126b realtime section", () => {
  test("badge + cash card + positions grid render when connected", async ({
    page,
    context,
  }) => {
    await page.route(
      `${API_BASE}/ibkr/connection/status`,
      mockRoute(PAPER_STATUS),
    );
    await page.route(
      `${API_BASE}/ibkr/sync/positions/latest`,
      mockRoute(ONE_POSITION),
    );
    await page.route(
      `${API_BASE}/ibkr/sync/cash/latest`,
      mockRoute(ONE_CASH),
    );
    await mockOtherEndpointsAsEmpty(context);

    await page.goto("/portefeuille");

    // Badge present + paper state.
    const badge = page.getByTestId("account-mode-badge");
    await expect(badge).toBeVisible();
    await expect(badge).toHaveAttribute("data-mode", "paper");
    await expect(badge).toContainText("Paper-rekening: DU•••4567");

    // Realtime section in "connected" state.
    const section = page.getByTestId("portefeuille-realtime-section");
    await expect(section).toHaveAttribute("data-state", "connected");

    // Cash summary card.
    const cash = page.getByTestId("cash-summary-card");
    await expect(cash).toHaveAttribute("data-state", "populated");
    await expect(cash).toContainText("EUR");
    await expect(cash).toContainText("11000.00");

    // Positions grid with Dutch headers + Decimal precision preserved.
    const grid = page.getByTestId("positions-grid");
    await expect(grid).toHaveAttribute("data-state", "populated");
    await expect(grid).toContainText("Symbool");
    await expect(grid).toContainText("Beurs");
    await expect(grid).toContainText("Gem. kostprijs");
    await expect(grid).toContainText("640.123456");
    await expect(grid).toContainText("12.5");
  });

  test("empty-state Dutch message renders when no positions exist", async ({
    page,
    context,
  }) => {
    await page.route(
      `${API_BASE}/ibkr/connection/status`,
      mockRoute(PAPER_STATUS),
    );
    await page.route(
      `${API_BASE}/ibkr/sync/positions/latest`,
      mockRoute(EMPTY_POSITIONS),
    );
    await page.route(
      `${API_BASE}/ibkr/sync/cash/latest`,
      mockRoute(ONE_CASH),
    );
    await mockOtherEndpointsAsEmpty(context);

    await page.goto("/portefeuille");

    const grid = page.getByTestId("positions-grid");
    await expect(grid).toHaveAttribute("data-state", "empty");
    await expect(grid).toContainText("Geen posities in deze rekening.");
  });

  test("disconnected banner renders when the worker is not connected", async ({
    page,
    context,
  }) => {
    await page.route(
      `${API_BASE}/ibkr/connection/status`,
      mockRoute(DISCONNECTED_STATUS),
    );
    await page.route(
      `${API_BASE}/ibkr/sync/positions/latest`,
      mockRoute(EMPTY_POSITIONS),
    );
    await page.route(
      `${API_BASE}/ibkr/sync/cash/latest`,
      async (route) => {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Opslag is niet beschikbaar." }),
        });
      },
    );
    await mockOtherEndpointsAsEmpty(context);

    await page.goto("/portefeuille");

    const section = page.getByTestId("portefeuille-realtime-section");
    await expect(section).toHaveAttribute("data-state", "disconnected");
    await expect(section).toContainText("IBKR-verbinding ontbreekt.");

    // Badge shows disconnected state across the page.
    const badge = page.getByTestId("account-mode-badge");
    await expect(badge).toHaveAttribute("data-mode", "disconnected");
    await expect(badge).toContainText("Geen IBKR-verbinding");
  });
});
