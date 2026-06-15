import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitForElementToBeRemoved,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const fns = vi.hoisted(() => ({
  getIbkrSyncStatus: vi.fn(),
  getPortfolioValuationReadiness: vi.fn(),
  getIbkrPositions: vi.fn(),
  getIbkrCash: vi.fn(),
  getIbkrOpenOrders: vi.fn(),
  getIbkrExecutions: vi.fn(),
  getLatestForecasts: vi.fn(),
  getLatestSuggestions: vi.fn(),
  getLatestDecisionPackages: vi.fn(),
  getLatestActionDrafts: vi.fn(),
  getLatestDailyBriefing: vi.fn(),
  getIbkrAccountMode: vi.fn(),
  getSchedulerJobs: vi.fn(),
  getLatestSchedulerRun: vi.fn(),
  getRecentSchedulerRuns: vi.fn(),
}));

vi.mock("@/lib/apiClient", () => ({
  apiClient: new Proxy(fns as Record<string, unknown>, {
    get: (target, prop: string) =>
      target[prop] ?? (() => Promise.resolve({ ok: false, reason: "x" })),
  }),
}));

vi.mock("@/components/PortefeuilleRealtimeSection", () => ({
  PortefeuilleRealtimeSection: () => null,
}));
vi.mock("@/components/PositionPlTraceDetails", () => ({
  PositionPlTraceDetails: () => null,
}));
vi.mock("@/components/ValuationTraceDetails", () => ({
  ValuationTraceDetails: () => null,
}));

import PortfolioPage from "./page";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function ok<T>(data: T) {
  return Promise.resolve({ ok: true as const, data });
}
function fail() {
  return Promise.resolve({ ok: false as const, reason: "not_reachable" });
}

function mockAllOk() {
  fns.getIbkrSyncStatus.mockReturnValue(
    ok({ configured: true, status_nl: "Klaar", positions_count: 0 }),
  );
  fns.getPortfolioValuationReadiness.mockReturnValue(
    ok({
      conversion_total_status: "conversion_ready",
      conversion_total_status_nl: "Klaar",
      base_currency: "EUR",
      rows: [],
    }),
  );
  fns.getIbkrPositions.mockReturnValue(ok({ items: [] }));
  fns.getIbkrCash.mockReturnValue(ok({ items: [] }));
  fns.getIbkrOpenOrders.mockReturnValue(ok({ items: [] }));
  fns.getIbkrExecutions.mockReturnValue(ok({ items: [] }));
  fns.getLatestForecasts.mockReturnValue(ok({ items: [] }));
  fns.getLatestSuggestions.mockReturnValue(ok({ items: [] }));
  fns.getLatestDecisionPackages.mockReturnValue(ok({ items: [] }));
  fns.getLatestActionDrafts.mockReturnValue(ok({ items: [] }));
  fns.getLatestDailyBriefing.mockReturnValue(ok({ item: null }));
  fns.getIbkrAccountMode.mockReturnValue(
    ok({ help_nl: "x", label_nl: "Paper", account_mode: "paper" }),
  );
  fns.getSchedulerJobs.mockReturnValue(
    ok({
      status: "ok",
      scheduler_timezone: "UTC",
      scheduler_daily_briefing_cron: "0 7 * * *",
      items: [],
    }),
  );
  fns.getLatestSchedulerRun.mockReturnValue(ok({ item: null }));
  fns.getRecentSchedulerRuns.mockReturnValue(ok({ items: [], limit: 10 }));
}

beforeEach(() => {
  Object.values(fns).forEach((f) => f.mockReset());
});
afterEach(() => cleanup());

describe("PortfolioPage data state machine", () => {
  it("shows the loading state before snapshots arrive", () => {
    mockAllOk();
    render(<PortfolioPage />);
    expect(
      screen.getByText("IBKR snapshots worden opgehaald."),
    ).toBeInTheDocument();
  });

  it("clears the loading state once data resolves", async () => {
    mockAllOk();
    render(<PortfolioPage />);
    await waitForElementToBeRemoved(() =>
      screen.queryByText("IBKR snapshots worden opgehaald."),
    );
  });

  it("shows the sync-failed state when every core read fails", async () => {
    Object.values(fns).forEach((f) => f.mockReturnValue(fail()));
    render(<PortfolioPage />);
    expect(
      await screen.findByText("Sync mislukt. Controleer de IBKR-koppeling."),
    ).toBeInTheDocument();
  });

  it("renders the recent daily-briefing runs tile with rows when present", async () => {
    mockAllOk();
    fns.getRecentSchedulerRuns.mockReturnValue(
      ok({
        items: [
          {
            run_id: "sch_1",
            job_name: "daily_briefing",
            scheduled_at: "2026-05-29T06:30:00+00:00",
            started_at: "2026-05-29T06:30:01+00:00",
            finished_at: "2026-05-29T06:30:42+00:00",
            status: "succeeded",
            error_text: null,
            triggered_by: "scheduler",
          },
          {
            run_id: "sch_2",
            job_name: "daily_briefing",
            scheduled_at: "2026-05-28T06:30:00+00:00",
            started_at: "2026-05-28T06:30:01+00:00",
            finished_at: "2026-05-28T06:30:09+00:00",
            status: "failed",
            error_text: "market_data_sync timeout",
            triggered_by: "scheduler",
          },
        ],
        limit: 10,
      }),
    );
    render(<PortfolioPage />);
    // findByText waits for the query to settle, not just the tile shell.
    expect(await screen.findByText("market_data_sync timeout")).toBeInTheDocument();
    const tile = screen.getByTestId("scheduler-recent-runs");
    expect(tile).toHaveTextContent("Recente daily-briefing runs");
    expect(tile).toHaveTextContent("succeeded");
    expect(tile).toHaveTextContent("failed");
  });

  it("shows the empty hint when no recent runs exist", async () => {
    mockAllOk();
    render(<PortfolioPage />);
    const tile = await screen.findByTestId("scheduler-recent-runs");
    expect(tile).toHaveTextContent("Nog geen runs.");
  });

  it("renders the hint↔actual mismatch warning banner when hint_mismatch=true", async () => {
    // V1.2 §BZ vervolg: wanneer de API rapporteert dat het
    // geconfigureerde hint NIET matcht met het actueel verbonden
    // TWS-account, MOET het dashboard een prominente waarschuwings-
    // banner tonen — anders mist de operator de safety-info.
    mockAllOk();
    fns.getIbkrAccountMode.mockReturnValue(
      ok({
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
    render(<PortfolioPage />);

    const banner = await screen.findByTestId(
      "account-mode-hint-mismatch-banner",
    );
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.textContent).toContain("DU•••4567");
    expect(banner.textContent).toContain("U7•••4321");
    expect(banner.textContent).toContain("mismatch");
  });

  it("does NOT render the mismatch banner when there is no mismatch", async () => {
    // Default mock (hint_mismatch undefined / false) — geen banner.
    mockAllOk();
    render(<PortfolioPage />);
    // findByTestId waits for the page; query for the banner specifically.
    await screen.findByText(/Portefeuille/i);
    expect(
      screen.queryByTestId("account-mode-hint-mismatch-banner"),
    ).toBeNull();
  });
});
