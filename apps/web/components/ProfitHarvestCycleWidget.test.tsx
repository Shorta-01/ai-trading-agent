import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type {
  PortfolioValuationReadinessResponse,
  PortfolioValuationReadinessRow,
} from "@/lib/apiClient";

const getPortfolioValuationReadiness = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getPortfolioValuationReadiness: (...a: unknown[]) =>
      getPortfolioValuationReadiness(...a),
  },
}));

import { ProfitHarvestCycleWidget } from "./ProfitHarvestCycleWidget";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function makeRow(
  overrides: Partial<PortfolioValuationReadinessRow> & {
    symbol: string;
    quantity: string;
  },
): PortfolioValuationReadinessRow {
  return {
    conid: "1",
    asset_class: "STK",
    currency: "EUR",
    average_cost: "100,00",
    market_data_status: "ok",
    valuation_status: "ok",
    reason_code: "ok",
    status_nl: "OK",
    help_nl: "",
    last_market_snapshot_id: "snap-1",
    market_price: "102,00",
    market_price_timestamp: "2026-06-12T09:00:00Z",
    market_value: "1020,00",
    unrealized_pnl: "20,00",
    cost_basis_status: "ready",
    cost_basis_status_nl: "OK",
    cost_basis_help_nl: "",
    cost_basis_available: true,
    cost_basis: "100,00",
    cost_basis_currency: "EUR",
    unrealized_pl_status: "ready",
    unrealized_pl_status_nl: "OK",
    unrealized_pl_help_nl: "",
    unrealized_pl_available: true,
    unrealized_pl: "20,00",
    unrealized_pl_currency: "EUR",
    unrealized_pl_percent_available: true,
    unrealized_pl_percent: "2.00",
    converted_unrealized_pl_available: true,
    converted_unrealized_pl: "20,00",
    missing_cost_basis_inputs: [],
    missing_pl_inputs: [],
    cost_basis_input_trace: null,
    unrealized_pl_input_trace: null,
    ...overrides,
  };
}

function makeResponse(
  rows: PortfolioValuationReadinessRow[],
): PortfolioValuationReadinessResponse {
  return {
    conversion_total_status: "conversion_ready",
    conversion_total_status_nl: "Klaar",
    conversion_total_help_nl: "",
    base_currency: "EUR",
    total_market_value_available: true,
    total_market_value: "1020,00",
    total_cash_value_available: true,
    total_cash_value: "0,00",
    total_portfolio_value_available: true,
    total_portfolio_value: "1020,00",
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
    rows,
  };
}

beforeEach(() => {
  getPortfolioValuationReadiness.mockReset();
});

afterEach(() => cleanup());

describe("ProfitHarvestCycleWidget", () => {
  it("renders one row per held position with current return and target distance", async () => {
    getPortfolioValuationReadiness.mockResolvedValue({
      ok: true as const,
      data: makeResponse([
        makeRow({ symbol: "AAPL", quantity: "10" }),
        makeRow({
          symbol: "MSFT",
          quantity: "5",
          unrealized_pl_percent: "5.00",
        }),
      ]),
    });
    render(<ProfitHarvestCycleWidget />);

    expect(
      await screen.findByTestId("profit-harvest-row-AAPL"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("profit-harvest-row-MSFT")).toBeInTheDocument();
    expect(screen.getByTestId("profit-harvest-row-AAPL-pct")).toHaveTextContent(
      "+2,00 %",
    );
    expect(
      screen.getByTestId("profit-harvest-row-AAPL-distance"),
    ).toHaveTextContent("2,00 pp");
    expect(
      screen.getByTestId("profit-harvest-row-MSFT-distance"),
    ).toHaveTextContent("Doel bereikt");
  });

  it("sorts positions by current return descending (closest to target first)", async () => {
    getPortfolioValuationReadiness.mockResolvedValue({
      ok: true as const,
      data: makeResponse([
        makeRow({ symbol: "LOW", quantity: "1", unrealized_pl_percent: "-1.00" }),
        makeRow({ symbol: "HIGH", quantity: "1", unrealized_pl_percent: "3.50" }),
        makeRow({ symbol: "MID", quantity: "1", unrealized_pl_percent: "1.00" }),
      ]),
    });
    render(<ProfitHarvestCycleWidget />);

    const list = await screen.findByTestId("profit-harvest-cycle-list");
    const rows = Array.from(
      list.querySelectorAll('[data-testid^="profit-harvest-row-"]'),
    ).map((el) => el.getAttribute("data-testid"));
    // First three are the row containers themselves; subsequent are -pct/-distance/-progress per row.
    const containers = rows.filter(
      (id) => id && /^profit-harvest-row-[A-Z]+$/.test(id),
    );
    expect(containers).toEqual([
      "profit-harvest-row-HIGH",
      "profit-harvest-row-MID",
      "profit-harvest-row-LOW",
    ]);
  });

  it("skips zero-quantity rows", async () => {
    getPortfolioValuationReadiness.mockResolvedValue({
      ok: true as const,
      data: makeResponse([
        makeRow({ symbol: "ZERO", quantity: "0" }),
        makeRow({ symbol: "REAL", quantity: "10" }),
      ]),
    });
    render(<ProfitHarvestCycleWidget />);
    await screen.findByTestId("profit-harvest-row-REAL");
    expect(screen.queryByTestId("profit-harvest-row-ZERO")).toBeNull();
  });

  it("renders Dutch empty state when no positions", async () => {
    getPortfolioValuationReadiness.mockResolvedValue({
      ok: true as const,
      data: makeResponse([]),
    });
    render(<ProfitHarvestCycleWidget />);
    expect(
      await screen.findByText("Nog geen posities in cyclus"),
    ).toBeInTheDocument();
  });

  it("renders the +4% doctrine target header", async () => {
    getPortfolioValuationReadiness.mockResolvedValue({
      ok: true as const,
      data: makeResponse([]),
    });
    render(<ProfitHarvestCycleWidget />);
    const widget = await screen.findByTestId("profit-harvest-cycle-widget");
    expect(widget).toHaveTextContent("+4%");
    expect(widget).toHaveTextContent("TOB");
  });
});
