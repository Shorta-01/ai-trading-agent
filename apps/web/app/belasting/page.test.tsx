import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type {
  TaxRealisedTrade,
  TaxYearReportResponse,
} from "@/lib/apiClient";

const getTaxYearReport = vi.fn();
const taxYearReportCsvUrl = vi.fn();
const listDividenden = vi.fn();
const createDividend = vi.fn();
const deleteDividend = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getTaxYearReport: (...a: unknown[]) => getTaxYearReport(...a),
    taxYearReportCsvUrl: (...a: unknown[]) => taxYearReportCsvUrl(...a),
    listDividenden: (...a: unknown[]) => listDividenden(...a),
    createDividend: (...a: unknown[]) => createDividend(...a),
    deleteDividend: (...a: unknown[]) => deleteDividend(...a),
  },
}));

import BelastingPage from "./page";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function makeTrade(
  overrides: Partial<TaxRealisedTrade> = {},
): TaxRealisedTrade {
  return {
    symbol: "AAPL",
    account_id: "DU1",
    currency_local: "USD",
    quantity: "10",
    buy_date: "2026-01-10",
    buy_price_local: "100",
    buy_exec_id: "b1",
    sell_date: "2026-03-15",
    sell_price_local: "110",
    sell_exec_id: "s1",
    gross_local: "100.00",
    tob_buy_local: "3.50",
    tob_sell_local: "3.85",
    net_local: "92.65",
    hold_days: 64,
    net_pct_on_cost: "9.27",
    buy_action_draft_id: "ad-buy",
    sell_action_draft_id: "ad-sell",
    ...overrides,
  };
}

function makeReport(
  overrides: Partial<TaxYearReportResponse> = {},
): TaxYearReportResponse {
  const monthlyPoints = Array.from({ length: 12 }, (_, i) => ({
    month: `2026-${String(i + 1).padStart(2, "0")}`,
    net_local_by_currency: {},
    cumulative_net_local_by_currency: {},
  }));
  return {
    title_nl: "Belastingoverzicht 2026",
    help_nl: "help",
    year: 2026,
    realised_trades: [],
    year_totals: {
      trade_count: 0,
      gross_local_by_currency: {},
      tob_local_by_currency: {},
      net_local_by_currency: {},
      average_hold_days: 0,
      hit_rate_pct: 0,
      earliest_close: null,
      latest_close: null,
    },
    monthly_points: monthlyPoints,
    good_householder: {
      trades_per_year: 0,
      average_hold_days: 0,
      trading_capital_share_pct: null,
      uses_leverage: false,
      uses_shorts: false,
      summary_nl: "0 trades per jaar, geen hefboom, geen short-posities.",
    },
    dividends: [],
    fx_conversion_available: false,
    notes_nl: ["EUR-conversie nog niet beschikbaar."],
    ...overrides,
  };
}

beforeEach(() => {
  getTaxYearReport.mockReset();
  taxYearReportCsvUrl.mockReturnValue("/belasting/jaaroverzicht.csv");
  listDividenden.mockReset();
  listDividenden.mockResolvedValue({
    ok: true as const,
    data: {
      title_nl: "Dividenden 2026",
      help_nl: "help",
      year: 2026,
      items: [],
      totals: {
        gross_by_currency: {},
        withholding_by_currency: {},
        net_by_currency: {},
        count: 0,
      },
      treaty_defaults_pct_by_country: { US: "15" },
    },
  });
  createDividend.mockReset();
  deleteDividend.mockReset();
});

afterEach(() => cleanup());

describe("BelastingPage", () => {
  it("renders the year selector and CSV download link", async () => {
    getTaxYearReport.mockResolvedValue({
      ok: true as const,
      data: makeReport(),
    });
    render(<BelastingPage />);
    expect(await screen.findByTestId("tax-year-select")).toBeInTheDocument();
    expect(screen.getByTestId("tax-csv-download")).toBeInTheDocument();
  });

  it("renders the empty-trade message when no realised trades", async () => {
    getTaxYearReport.mockResolvedValue({
      ok: true as const,
      data: makeReport(),
    });
    render(<BelastingPage />);
    expect(
      await screen.findByTestId("tax-realised-trades-empty"),
    ).toBeInTheDocument();
  });

  it("renders one row per realised trade", async () => {
    getTaxYearReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        realised_trades: [makeTrade(), makeTrade({ buy_exec_id: "b2", sell_exec_id: "s2" })],
      }),
    });
    render(<BelastingPage />);
    expect(await screen.findByTestId("tax-realised-trades-table")).toBeInTheDocument();
    expect(screen.getByTestId("tax-trade-row-b1-s1")).toBeInTheDocument();
    expect(screen.getByTestId("tax-trade-row-b2-s2")).toBeInTheDocument();
  });

  it("renders year totals with hit-rate and trade count", async () => {
    getTaxYearReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        year_totals: {
          trade_count: 3,
          gross_local_by_currency: { USD: "300.00" },
          tob_local_by_currency: { USD: "7.00" },
          net_local_by_currency: { USD: "293.00" },
          average_hold_days: 50,
          hit_rate_pct: 66.7,
          earliest_close: "2026-02-10",
          latest_close: "2026-05-10",
        },
      }),
    });
    render(<BelastingPage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("tax-year-totals-trade-count").textContent,
      ).toBe("3");
    });
    expect(screen.getByTestId("tax-year-totals-hit-rate").textContent).toContain(
      "66,7",
    );
    expect(
      screen.getByTestId("tax-year-totals-net").textContent,
    ).toContain("USD");
  });

  it("renders the 'goed huisvader' summary block", async () => {
    getTaxYearReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        good_householder: {
          trades_per_year: 7,
          average_hold_days: 95,
          trading_capital_share_pct: 0.8,
          uses_leverage: false,
          uses_shorts: false,
          summary_nl:
            "7 trades per jaar, gemiddelde hold 95 dagen, trading-kapitaal 0.8% van totaal vermogen, geen hefboom, geen short-posities.",
        },
      }),
    });
    render(<BelastingPage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("tax-good-householder").textContent,
      ).toContain("7 trades");
    });
    expect(
      screen.getByTestId("tax-good-householder").textContent,
    ).toContain("geen hefboom");
  });

  it("renders the monthly chart when there is data", async () => {
    getTaxYearReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        monthly_points: Array.from({ length: 12 }, (_, i) => ({
          month: `2026-${String(i + 1).padStart(2, "0")}`,
          net_local_by_currency:
            (i === 2 ? { USD: "92.65" } : {}) as Record<string, string>,
          cumulative_net_local_by_currency:
            (i >= 2 ? { USD: "92.65" } : {}) as Record<string, string>,
        })),
      }),
    });
    render(<BelastingPage />);
    expect(await screen.findByTestId("tax-monthly-chart")).toBeInTheDocument();
    expect(screen.getAllByTestId(/tax-monthly-bar-/)).toHaveLength(12);
  });

  it("falls back to the empty-chart message when cumulative is all zero", async () => {
    getTaxYearReport.mockResolvedValue({
      ok: true as const,
      data: makeReport(),
    });
    render(<BelastingPage />);
    expect(
      await screen.findByTestId("tax-monthly-chart-empty"),
    ).toBeInTheDocument();
  });

  it("renders the notes section listing FX/dividend caveats", async () => {
    getTaxYearReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        notes_nl: ["EUR-conversie note", "Dividenden note"],
      }),
    });
    render(<BelastingPage />);
    const notes = await screen.findByTestId("tax-notes");
    expect(notes.textContent).toContain("EUR-conversie");
    expect(notes.textContent).toContain("Dividenden");
  });

  it("requests the report again when the year changes", async () => {
    getTaxYearReport.mockResolvedValue({
      ok: true as const,
      data: makeReport(),
    });
    render(<BelastingPage />);
    await waitFor(() => {
      expect(getTaxYearReport).toHaveBeenCalled();
    });
    const callsBefore = getTaxYearReport.mock.calls.length;
    fireEvent.change(screen.getByTestId("tax-year-select"), {
      target: { value: "2025" },
    });
    await waitFor(() => {
      expect(getTaxYearReport.mock.calls.length).toBeGreaterThan(callsBefore);
    });
    const lastCall = getTaxYearReport.mock.calls.at(-1)?.[0];
    expect(lastCall.year).toBe(2025);
  });

  it("renders the dividends placeholder section", async () => {
    getTaxYearReport.mockResolvedValue({
      ok: true as const,
      data: makeReport(),
    });
    render(<BelastingPage />);
    expect(
      await screen.findByTestId("tax-dividends-info"),
    ).toBeInTheDocument();
  });
});
