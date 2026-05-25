import { expect, test, type Route } from "@playwright/test";

/**
 * Task 131 Playwright smoke: multi-asset forecast column +
 * Dashboard summary widget filter routing.
 *
 * Mocks the new ``/forecast/by-account``, ``/forecast/day-summary``,
 * and the existing watchlist/market-data routes so the test runs
 * without a live API.
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
        watchlist_item_id: "wi-1",
        symbol: "ASML",
        ibkr_conid: "conid-asml",
      },
      ibkr_status_label_nl: "Gevalideerd",
      asset_listing_readiness: {
        status_nl: "Klaar",
        next_step_nl: "Geen actie",
      },
    },
    {
      item: {
        watchlist_item_id: "wi-2",
        symbol: "SAP",
        ibkr_conid: "conid-sap",
      },
      ibkr_status_label_nl: "Gevalideerd",
      asset_listing_readiness: {
        status_nl: "Klaar",
        next_step_nl: "Geen actie",
      },
    },
    {
      item: {
        watchlist_item_id: "wi-3",
        symbol: "VWCE",
        ibkr_conid: "conid-vwce",
      },
      ibkr_status_label_nl: "Gevalideerd",
      asset_listing_readiness: {
        status_nl: "Klaar",
        next_step_nl: "Geen actie",
      },
    },
    {
      item: {
        watchlist_item_id: "wi-4",
        symbol: "SXR8",
        ibkr_conid: "conid-sxr8",
      },
      ibkr_status_label_nl: "Gevalideerd",
      asset_listing_readiness: {
        status_nl: "Klaar",
        next_step_nl: "Geen actie",
      },
    },
    {
      item: {
        watchlist_item_id: "wi-5",
        symbol: "NOPE",
        ibkr_conid: "conid-nope",
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
      conid: "conid-asml",
      label: "Kopen",
      confidence_level: "Hoog",
      generated_at: "2026-05-25T07:00:00+00:00",
      p50_log_return: "0.04",
      prob_positive: "0.72",
      user_holds_position: false,
    },
    {
      conid: "conid-sap",
      label: "Bekijken",
      confidence_level: "Gemiddeld",
      generated_at: "2026-05-25T07:00:00+00:00",
      p50_log_return: "0.01",
      prob_positive: "0.55",
      user_holds_position: false,
    },
    {
      conid: "conid-vwce",
      label: "Houden",
      confidence_level: "Hoog",
      generated_at: "2026-05-25T07:00:00+00:00",
      p50_log_return: "0.005",
      prob_positive: "0.51",
      user_holds_position: true,
    },
    {
      conid: "conid-sxr8",
      label: "Geblokkeerd",
      confidence_level: "Laag",
      generated_at: "2026-05-25T07:00:00+00:00",
      p50_log_return: "0",
      prob_positive: "0.5",
      user_holds_position: false,
    },
    // NOPE deliberately omitted — its Voorspelling cell should show "—".
  ],
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const DAY_SUMMARY = {
  account_id: "DU1234567",
  as_of_date: "2026-05-25",
  total_forecasts: 4,
  total_blocked: 1,
  label_counts: { Kopen: 1, Bekijken: 1, Houden: 1, Geblokkeerd: 1 },
  block_reasons: { insufficient_history: 1 },
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const MARKET_DATA_STATUS = {
  status: "snapshot_available",
  status_nl: "Snapshot beschikbaar",
  price_basis_nl: "Snapshot",
  valuation_readiness_status: "ready_for_status_only",
};


test.describe("Volglijst — Task 131 multi-asset forecast column", () => {
  test.beforeEach(async ({ context }) => {
    await context.route("**/*", async (route) => {
      const url = route.request().url();
      const isApi =
        url.includes("/watchlist/") ||
        url.includes("/forecast/") ||
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
  });

  test("Voorspelling column populated for all rows with forecasts, '—' for missing", async ({
    page,
  }) => {
    await page.goto("/volglijst");
    await expect(page.getByTestId("volglijst-forecast-label-ASML")).toHaveText(
      "Kopen",
    );
    await expect(page.getByTestId("volglijst-forecast-label-SAP")).toHaveText(
      "Bekijken",
    );
    await expect(page.getByTestId("volglijst-forecast-label-VWCE")).toHaveText(
      "Houden",
    );
    await expect(
      page.getByTestId("volglijst-forecast-label-SXR8"),
    ).toHaveText("Geblokkeerd");
    // NOPE has no forecast → fallback "—".
    await expect(page.getByTestId("volglijst-forecast-cell-NOPE")).toHaveText(
      "—",
    );
  });

  test("filter=Kopen narrows the table to only Kopen rows", async ({ page }) => {
    await page.goto("/volglijst?filter=Kopen");
    await expect(
      page.getByTestId("volglijst-filter-banner"),
    ).toContainText("Kopen");
    await expect(page.getByTestId("volglijst-row-ASML")).toBeVisible();
    await expect(page.getByTestId("volglijst-row-SAP")).toHaveCount(0);
    await expect(page.getByTestId("volglijst-row-VWCE")).toHaveCount(0);
  });

  test("Dashboard widget pill routes to the filtered Volglijst", async ({
    page,
  }) => {
    await page.goto("/");
    const kopenPill = page.getByTestId("forecast-day-summary-pill-Kopen");
    await expect(kopenPill).toBeVisible();
    await kopenPill.click();
    await expect(page).toHaveURL(/\/volglijst\?filter=Kopen/);
    await expect(
      page.getByTestId("volglijst-filter-banner"),
    ).toBeVisible();
  });

  test("Toon alles button clears the filter", async ({ page }) => {
    await page.goto("/volglijst?filter=Kopen");
    await expect(page.getByTestId("volglijst-filter-banner")).toBeVisible();
    await page.getByTestId("volglijst-filter-clear").click();
    await expect(
      page.getByTestId("volglijst-filter-banner"),
    ).toHaveCount(0);
    // After clearing, all rows are visible again.
    await expect(page.getByTestId("volglijst-row-ASML")).toBeVisible();
    await expect(page.getByTestId("volglijst-row-SAP")).toBeVisible();
  });
});
