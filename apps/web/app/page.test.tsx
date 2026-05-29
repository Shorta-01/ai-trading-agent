import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  IbkrStatusResponse,
  IbkrSyncStatusResponse,
  PortfolioValuationReadinessResponse,
  SystemStatusSummary,
} from "@/lib/apiClient";

const getSystemStatus = vi.fn();
const getIbkrStatus = vi.fn();
const getIbkrSyncStatus = vi.fn();
const getPortfolioValuationReadiness = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getSystemStatus: (...a: unknown[]) => getSystemStatus(...a),
    getIbkrStatus: (...a: unknown[]) => getIbkrStatus(...a),
    getIbkrSyncStatus: (...a: unknown[]) => getIbkrSyncStatus(...a),
    getPortfolioValuationReadiness: (...a: unknown[]) =>
      getPortfolioValuationReadiness(...a),
  },
}));

// Stub the child widgets that do their own fetching, so this test only
// exercises the page's four endpoints.
vi.mock("@/components/SchedulerStatusBadge", () => ({
  SchedulerStatusBadge: () => null,
}));
vi.mock("@/components/CalibrationCoverageBadge", () => ({
  CalibrationCoverageBadge: () => null,
}));
vi.mock("@/components/ForecastDaySummaryWidget", () => ({
  ForecastDaySummaryWidget: () => null,
}));
vi.mock("@/components/ReconciliationStatusWidget", () => ({
  ReconciliationStatusWidget: () => null,
}));

import HomePage from "./page";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const SYSTEM = {
  services: [
    {
      key: "api",
      label_nl: "API-service",
      status_key: "active",
      status_nl: "Actief",
      help_nl: "De API draait.",
      blocks_suggestions: false,
      last_checked_at: null,
    },
  ],
} as SystemStatusSummary;

const IBKR_STATUS = {
  configured: true,
  message_nl: "Wacht op gegevens.",
} as unknown as IbkrStatusResponse;

const IBKR_SYNC = {
  positions_count: 2,
  open_orders_count: 1,
  executions_count: 3,
} as unknown as IbkrSyncStatusResponse;

const VALUATION = {
  base_currency: "EUR",
  total_portfolio_value: "1000.00",
  total_portfolio_value_available: true,
  total_cash_value: "200.00",
  total_cash_value_available: true,
  total_market_value: "800.00",
  total_market_value_available: true,
  conversion_total_status: "conversion_ready",
  conversion_total_status_nl: "Omrekening klaar",
} as unknown as PortfolioValuationReadinessResponse;

function ok<T>(data: T) {
  return Promise.resolve({ ok: true as const, data });
}
function fail() {
  return Promise.resolve({ ok: false as const, reason: "not_reachable" });
}

function mockAllOk() {
  getSystemStatus.mockReturnValue(ok(SYSTEM));
  getIbkrStatus.mockReturnValue(ok(IBKR_STATUS));
  getIbkrSyncStatus.mockReturnValue(ok(IBKR_SYNC));
  getPortfolioValuationReadiness.mockReturnValue(ok(VALUATION));
}

beforeEach(() => {
  getSystemStatus.mockReset();
  getIbkrStatus.mockReset();
  getIbkrSyncStatus.mockReset();
  getPortfolioValuationReadiness.mockReset();
});

afterEach(() => cleanup());

describe("HomePage", () => {
  it("shows the loading placeholder before valuation arrives", () => {
    mockAllOk();
    render(<HomePage />);
    expect(screen.getAllByText("Laden...").length).toBeGreaterThan(0);
  });

  it("renders the valuation totals once loaded", async () => {
    mockAllOk();
    render(<HomePage />);
    // The total value renders in both the metric heading and its badge.
    expect((await screen.findAllByText("EUR 1000.00")).length).toBeGreaterThan(
      0,
    );
    expect(screen.getAllByText("EUR 800.00").length).toBeGreaterThan(0);
  });

  it("renders system-status services and IBKR sync counts", async () => {
    mockAllOk();
    render(<HomePage />);
    expect(await screen.findByText("API-service")).toBeInTheDocument();
    expect(
      screen.getByText(/Posities: 2 · Open orders: 1 · Executies: 3/),
    ).toBeInTheDocument();
  });

  it("falls back to Dutch unavailable states when every endpoint fails", async () => {
    getSystemStatus.mockReturnValue(fail());
    getIbkrStatus.mockReturnValue(fail());
    getIbkrSyncStatus.mockReturnValue(fail());
    getPortfolioValuationReadiness.mockReturnValue(fail());
    render(<HomePage />);
    expect(
      await screen.findByText("Waardering niet beschikbaar"),
    ).toBeInTheDocument();
    expect(screen.getByText("Status niet beschikbaar")).toBeInTheDocument();
  });
});
