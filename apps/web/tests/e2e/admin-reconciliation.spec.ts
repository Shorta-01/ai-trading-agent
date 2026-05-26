import { expect, test, type Route } from "@playwright/test";

/**
 * Task 135b Playwright: /admin/reconciliation page renders the four
 * locked Dutch sections and the acknowledge action flips a pending
 * manual-review row to acknowledged on subsequent reloads.
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

const RUN_COMPLETED = {
  id: 1,
  reconciliation_run_id: "run-e2e-1",
  started_at: "2026-05-27T11:50:00+00:00",
  completed_at: "2026-05-27T11:50:30+00:00",
  account_id: "DU1234567",
  pass_a_orphaned_count: 1,
  pass_b_stale_count: 0,
  pass_c_timeout_count: 2,
  divergences_found: 3,
  mode_detected: "completed",
  error_details_json: null,
};

const PENDING_REVIEW = {
  id: 42,
  flagged_at: "2026-05-27T11:55:00+00:00",
  action_draft_id: "draft-timeout-1",
  reason: "timeout_24h_no_data",
  details_dutch:
    "Action Draft is langer dan 24 uur in awaiting_reply_timeout zonder dat IBKR een uitvoering, status-update of annulering heeft teruggemeld. Handmatige beoordeling vereist.",
  resolution_status: "pending",
  resolved_at: null,
  resolution_note: null,
};

const UNMATCHED_EXEC = {
  id: 7,
  event_at: "2026-05-27T11:30:00+00:00",
  ibkr_perm_id: 900900,
  ibkr_exec_id: "tws-e2e-1",
  account_id: "DU1234567",
  conid: "67890",
  side: "BUY",
  fill_price_local: "100.50",
  fill_quantity: "10",
  fill_time: "2026-05-27T11:25:00+00:00",
  raw_execution_json: { source: "TWS" },
  resolution_status: "unresolved",
};

test.describe("Task 135b — /admin/reconciliation page", () => {
  test.beforeEach(async ({ context, page }) => {
    await context.route("**/*", async (route) => {
      const url = route.request().url();
      const isApi =
        url.includes("/reconciliation/") ||
        url.startsWith("http://127.0.0.1:3100") ||
        url.startsWith("http://localhost:3100");
      if (isApi) return route.fallback();
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Mock catch-all: 503." }),
      });
    });

    let acknowledged = false;

    await context.route(
      "**/reconciliation/status**",
      fulfillJson({
        ibkr_account_id: "DU1234567",
        latest_run: RUN_COMPLETED,
        drafts_healed_last_24h: 1,
        pending_manual_review_count: acknowledged ? 0 : 1,
        unresolved_unmatched_count: 1,
      }),
    );
    await context.route("**/reconciliation/runs**", fulfillJson({
      ibkr_account_id: "DU1234567",
      runs: [RUN_COMPLETED],
    }));
    await context.route(
      "**/reconciliation/manual-review**",
      async (route) => {
        if (route.request().method() === "POST") {
          acknowledged = true;
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              ...PENDING_REVIEW,
              resolution_status: "acknowledged",
              resolved_at: "2026-05-27T12:00:00+00:00",
              resolution_note: "Door gebruiker bevestigd.",
            }),
          });
          return;
        }
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ibkr_account_id: "DU1234567",
            rows: acknowledged ? [] : [PENDING_REVIEW],
          }),
        });
      },
    );
    await context.route(
      "**/reconciliation/unmatched-executions**",
      fulfillJson({
        ibkr_account_id: "DU1234567",
        rows: [UNMATCHED_EXEC],
      }),
    );

    // The admin page may call other endpoints from the layout (e.g.
    // navbar status). Stub a permissive fallback in case the layout
    // pulls from any other route.
    void page;
  });

  test("renders all four sections with seed data", async ({ page }) => {
    await page.goto("/admin/reconciliation");
    await expect(page.locator("h1")).toContainText("IBKR-reconciliatie");
    await expect(page.getByTestId("reconciliation-status-card")).toContainText(
      "Voltooid",
    );
    await expect(
      page.getByTestId("reconciliation-pending-review-table"),
    ).toContainText("draft-timeout-1");
    await expect(
      page.getByTestId("reconciliation-unmatched-table"),
    ).toContainText("tws-e2e-1");
    await expect(
      page.getByTestId("reconciliation-runs-table"),
    ).toContainText("run-e2e-1");
  });

  test("acknowledging a pending row hides it on reload", async ({ page }) => {
    page.on("dialog", (dialog) => {
      void dialog.accept("Door gebruiker bevestigd.");
    });

    await page.goto("/admin/reconciliation");
    await page
      .getByTestId("reconciliation-acknowledge-42")
      .click();

    await expect(
      page.getByTestId("reconciliation-no-pending-review"),
    ).toContainText("Geen openstaande rijen.");
  });
});
