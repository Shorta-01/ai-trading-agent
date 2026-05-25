import { expect, test, type Route } from "@playwright/test";

/**
 * Task 126b smoke: visit /portefeuille, mock the API responses,
 * assert the AccountModeBadge appears, the cash card renders, the
 * positions grid has the locked Dutch headers, and the empty +
 * disconnected states surface the right Dutch microcopy.
 *
 * Routes use glob patterns (``**​/ibkr/...``) so the mocks match
 * regardless of the configured ``NEXT_PUBLIC_API_BASE_URL`` host. A
 * catch-all returns HTTP 503 for every other API endpoint so the
 * legacy Portefeuille panels (which call ~20 other endpoints)
 * degrade gracefully via ``apiClient``'s not-reachable handling
 * instead of crashing the page.
 */

function mockRoute(json: object) {
  return async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(json),
    });
  };
}

async function mockOtherEndpointsAsUnreachable(
  context: import("@playwright/test").BrowserContext,
) {
  // Any /ibkr/... endpoint not handled by a per-test page.route() falls
  // through to here and gets a 503. The apiClient maps that to
  // ``{ok: false, reason: "not_reachable"}`` which the legacy
  // Portefeuille panels render as "Niet beschikbaar" without crashing.
  await context.route("**/*", async (route) => {
    const url = route.request().url();
    if (
      url.includes("/ibkr/connection/status") ||
      url.includes("/ibkr/connection/audit") ||
      url.includes("/ibkr/sync/positions/latest") ||
      url.includes("/ibkr/sync/cash/latest") ||
      // Same-origin Next.js page resources (HTML / JS / CSS / favicons)
      // must pass through to the dev/prod server.
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

test.describe("Portefeuille — Task 126b realtime section", () => {
  test.beforeEach(async ({ context }) => {
    await mockOtherEndpointsAsUnreachable(context);
  });

  test("badge + cash card + positions grid render when connected", async ({
    page,
  }) => {
    await page.route("**/ibkr/connection/status", mockRoute(PAPER_STATUS));
    await page.route(
      "**/ibkr/sync/positions/latest",
      mockRoute(ONE_POSITION),
    );
    await page.route("**/ibkr/sync/cash/latest", mockRoute(ONE_CASH));

    await page.goto("/portefeuille");

    const badge = page.getByTestId("account-mode-badge");
    await expect(badge).toBeVisible();
    await expect(badge).toHaveAttribute("data-mode", "paper");
    await expect(badge).toContainText("Paper-rekening: DU•••4567");

    const section = page.getByTestId("portefeuille-realtime-section");
    await expect(section).toHaveAttribute("data-state", "connected");

    const cash = page.getByTestId("cash-summary-card");
    await expect(cash).toHaveAttribute("data-state", "populated");
    await expect(cash).toContainText("EUR");
    await expect(cash).toContainText("11000.00");

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
  }) => {
    await page.route("**/ibkr/connection/status", mockRoute(PAPER_STATUS));
    await page.route(
      "**/ibkr/sync/positions/latest",
      mockRoute(EMPTY_POSITIONS),
    );
    await page.route("**/ibkr/sync/cash/latest", mockRoute(ONE_CASH));

    await page.goto("/portefeuille");

    const grid = page.getByTestId("positions-grid");
    await expect(grid).toHaveAttribute("data-state", "empty");
    await expect(grid).toContainText("Geen posities in deze rekening.");
  });

  test("disconnected banner renders when the worker is not connected", async ({
    page,
  }) => {
    await page.route(
      "**/ibkr/connection/status",
      mockRoute(DISCONNECTED_STATUS),
    );
    await page.route(
      "**/ibkr/sync/positions/latest",
      mockRoute(EMPTY_POSITIONS),
    );
    await page.route("**/ibkr/sync/cash/latest", async (route) => {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Opslag is niet beschikbaar." }),
      });
    });

    await page.goto("/portefeuille");

    const section = page.getByTestId("portefeuille-realtime-section");
    await expect(section).toHaveAttribute("data-state", "disconnected");
    await expect(section).toContainText("IBKR-verbinding ontbreekt.");

    const badge = page.getByTestId("account-mode-badge");
    await expect(badge).toHaveAttribute("data-mode", "disconnected");
    await expect(badge).toContainText("Geen IBKR-verbinding");
  });
});
