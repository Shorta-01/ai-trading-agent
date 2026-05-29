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
});
