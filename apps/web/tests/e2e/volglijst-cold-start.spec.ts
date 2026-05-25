import { expect, test, type Route } from "@playwright/test";

/**
 * Task 128 Playwright smoke: cold-start Volglijst confirmation flow.
 *
 * Mocks ``/watchlist/confirmation-state`` + ``/watchlist/cold-start-items``
 * + ``/watchlist/confirm`` so the test runs without a live API.
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

const STARTER_ITEMS = {
  items: [
    {
      watchlist_item_id: "wi-1",
      symbol: "SXR8",
      name: "iShares Core S&P 500 UCITS",
      exchange: "XETRA",
      currency: "EUR",
      security_type: "ETF",
    },
    {
      watchlist_item_id: "wi-2",
      symbol: "VWCE",
      name: "Vanguard FTSE All-World UCITS",
      exchange: "XETRA",
      currency: "EUR",
      security_type: "ETF",
    },
    {
      watchlist_item_id: "wi-3",
      symbol: "ASML",
      name: "ASML Holding (Euronext)",
      exchange: "AEB",
      currency: "EUR",
      security_type: "STK",
    },
  ],
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const UNCONFIRMED = {
  account_id: "DU1234567",
  state: "unconfirmed" as const,
  banner_text:
    "Welkom. Je IBKR-rekening is gesynchroniseerd. Het systeem heeft een startvoorstel voor je Volglijst klaargezet. Bekijk en bevestig in Volglijst voordat suggesties starten.",
  safe_for_action_drafts: false,
  safe_for_orders: false,
};


test.describe("Volglijst — Task 128 cold-start flow", () => {
  test.beforeEach(async ({ context }) => {
    // Catch-all returns 503 so unrelated /ibkr/* / /scheduler/v127/*
    // routes degrade gracefully through the rest of the UI.
    await context.route("**/*", async (route) => {
      const url = route.request().url();
      if (
        url.includes("/watchlist/confirmation-state") ||
        url.includes("/watchlist/cold-start-items") ||
        url.includes("/watchlist/confirm") ||
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

  test("yellow info card + starter rows + Verwijder all visible", async ({
    page,
  }) => {
    await page.route(
      "**/watchlist/confirmation-state",
      fulfillJson(UNCONFIRMED),
    );
    await page.route(
      "**/watchlist/cold-start-items",
      fulfillJson(STARTER_ITEMS),
    );

    await page.goto("/volglijst");

    await expect(
      page.getByTestId("volglijst-cold-start-flow"),
    ).toBeVisible();
    await expect(
      page.getByTestId("cold-start-info-card"),
    ).toContainText("Startvoorstel.");
    await expect(
      page.getByTestId("cold-start-row-SXR8"),
    ).toBeVisible();
    await expect(
      page.getByTestId("cold-start-verwijder-SXR8"),
    ).toBeVisible();
  });

  test("wrong phrase surfaces Dutch error inline", async ({ page }) => {
    await page.route(
      "**/watchlist/confirmation-state",
      fulfillJson(UNCONFIRMED),
    );
    await page.route(
      "**/watchlist/cold-start-items",
      fulfillJson(STARTER_ITEMS),
    );
    await page.route(
      "**/watchlist/confirm",
      fulfillJson({ detail: "Bevestigingscode is onjuist." }, 400),
    );

    await page.goto("/volglijst");
    await page.getByTestId("cold-start-phrase-input").fill("bevestig");
    await page.getByTestId("cold-start-confirm-button").click();

    await expect(
      page.getByTestId("cold-start-error"),
    ).toContainText("Bevestigingscode is onjuist.");
  });

  test("BEVESTIG flips to confirmed and switches to the normal view", async ({
    page,
  }) => {
    // The Volglijst page + the global ColdStartBanner BOTH poll
    // /watchlist/confirmation-state, so a counter-based mock races.
    // Use a flag the confirm endpoint flips so every poll after the
    // confirm sees "confirmed".
    let confirmed = false;
    await page.route(
      "**/watchlist/confirmation-state",
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(
            confirmed
              ? {
                  account_id: "DU1234567",
                  state: "confirmed",
                  banner_text: null,
                  safe_for_action_drafts: false,
                  safe_for_orders: false,
                }
              : UNCONFIRMED,
          ),
        });
      },
    );
    await page.route(
      "**/watchlist/cold-start-items",
      fulfillJson(STARTER_ITEMS),
    );
    await page.route("**/watchlist/confirm", async (route) => {
      confirmed = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          state: "confirmed",
          confirmed_at: "2026-05-25T07:00:00+00:00",
          row_count: 3,
          safe_for_action_drafts: false,
          safe_for_orders: false,
        }),
      });
    });

    await page.goto("/volglijst");
    await expect(
      page.getByTestId("volglijst-cold-start-flow"),
    ).toBeVisible();
    // Wait until the starter rows have loaded so the confirm button
    // is enabled (canSubmit gates on items.length > 0).
    await expect(
      page.getByTestId("cold-start-row-SXR8"),
    ).toBeVisible();

    await page.getByTestId("cold-start-phrase-input").fill("BEVESTIG");
    await expect(
      page.getByTestId("cold-start-confirm-button"),
    ).toBeEnabled();
    await page.getByTestId("cold-start-confirm-button").click();

    // After the confirm endpoint flips the flag and the page reloads
    // state via the onConfirmed callback, the flow component
    // unmounts and the normal Volglijst takes over.
    await expect(
      page.getByTestId("volglijst-cold-start-flow"),
    ).toHaveCount(0, { timeout: 10_000 });
  });
});
