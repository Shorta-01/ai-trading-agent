import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type {
  IbkrCashSnapshot,
  NavHistoryResponse,
  PortfolioValuationReadinessResponse,
  PortfolioValuationReadinessRow,
} from "@/lib/apiClient";

const getPortfolioValuationReadiness = vi.fn();
const getIbkrCash = vi.fn();
const getNavHistory = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getPortfolioValuationReadiness: (...a: unknown[]) =>
      getPortfolioValuationReadiness(...a),
    getIbkrCash: (...a: unknown[]) => getIbkrCash(...a),
    getNavHistory: (...a: unknown[]) => getNavHistory(...a),
  },
}));

import { PortfolioKpiTiles } from "./PortfolioKpiTiles";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const ok = <T,>(data: T) => ({ ok: true as const, data });

function row(qty: string, symbol: string): PortfolioValuationReadinessRow {
  return {
    conid: "1",
    symbol,
    asset_class: "STK",
    currency: "EUR",
    quantity: qty,
    average_cost: null,
    market_data_status: "ok",
    valuation_status: "ok",
    reason_code: "ok",
    status_nl: "",
    help_nl: "",
    last_market_snapshot_id: null,
    market_price: null,
    market_price_timestamp: null,
    market_value: null,
    unrealized_pnl: null,
    cost_basis_status: "",
    cost_basis_status_nl: "",
    cost_basis_help_nl: "",
    cost_basis_available: false,
    cost_basis: null,
    cost_basis_currency: null,
    unrealized_pl_status: "",
    unrealized_pl_status_nl: "",
    unrealized_pl_help_nl: "",
    unrealized_pl_available: false,
    unrealized_pl: null,
    unrealized_pl_currency: null,
    unrealized_pl_percent_available: false,
    unrealized_pl_percent: null,
    converted_unrealized_pl_available: false,
    converted_unrealized_pl: null,
    missing_cost_basis_inputs: [],
    missing_pl_inputs: [],
    cost_basis_input_trace: null,
    unrealized_pl_input_trace: null,
  };
}

const VALUATION: PortfolioValuationReadinessResponse = {
  conversion_total_status: "conversion_ready",
  conversion_total_status_nl: "",
  conversion_total_help_nl: "",
  base_currency: "EUR",
  total_market_value_available: true,
  total_market_value: "9000",
  total_cash_value_available: true,
  total_cash_value: "1000",
  total_portfolio_value_available: true,
  total_portfolio_value: "10000",
  converted_totals_available: true,
  converted_position_values_available: true,
  converted_cash_values_available: true,
  missing_total_value_inputs: [],
  missing_market_data_conids: [],
  missing_cash_inputs: [],
  missing_fx_pairs: [],
  stale_fx_pairs: [],
  invalid_fx_pairs: [],
  valuation_input_trace: null,
  rows: [row("10", "AAPL"), row("0", "ZERO"), row("5", "MSFT")],
};

const CASH: IbkrCashSnapshot[] = [
  {
    sync_run_id: "r",
    account_ref: "default",
    base_currency: "EUR",
    cash: "1000",
    available_funds: "950",
    buying_power: "1500",
    timestamp: "2026-06-12T08:00:00Z",
  },
];

const NAV: NavHistoryResponse = {
  status: "ready",
  status_nl: "",
  help_nl: "",
  ibkr_account_id: "DU1",
  base_currency: "EUR",
  days_requested: 7,
  points: [
    { recorded_at_utc: "2026-06-11T17:00:00Z", nav_value: "9900" },
    { recorded_at_utc: "2026-06-12T17:00:00Z", nav_value: "10000" },
  ],
};

beforeEach(() => {
  getPortfolioValuationReadiness.mockReset();
  getIbkrCash.mockReset();
  getNavHistory.mockReset();
});

afterEach(() => cleanup());

describe("PortfolioKpiTiles", () => {
  it("renders four tiles with valuation, day delta, cash, position count", async () => {
    getPortfolioValuationReadiness.mockResolvedValue(ok(VALUATION));
    getIbkrCash.mockResolvedValue(ok({ items: CASH }));
    getNavHistory.mockResolvedValue(ok(NAV));
    render(<PortfolioKpiTiles />);
    await waitFor(() => {
      expect(screen.getByTestId("kpi-tile-total-value")).toHaveTextContent(
        "EUR 10000",
      );
    });
    expect(screen.getByTestId("kpi-tile-day-result")).toHaveTextContent("+100");
    expect(screen.getByTestId("kpi-tile-cash")).toHaveTextContent("EUR 950");
    expect(screen.getByTestId("kpi-tile-position-count")).toHaveTextContent("2");
  });

  it("falls back to Niet beschikbaar when valuation is not available", async () => {
    getPortfolioValuationReadiness.mockResolvedValue(
      ok({
        ...VALUATION,
        total_portfolio_value_available: false,
        total_portfolio_value: null,
      }),
    );
    getIbkrCash.mockResolvedValue(ok({ items: [] }));
    getNavHistory.mockResolvedValue(ok({ ...NAV, points: [] }));
    render(<PortfolioKpiTiles />);
    await waitFor(() => {
      expect(screen.getByTestId("kpi-tile-total-value")).toHaveTextContent(
        "Niet beschikbaar",
      );
    });
    expect(screen.getByTestId("kpi-tile-cash")).toHaveTextContent(
      "Niet beschikbaar",
    );
  });
});
