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

import type { MonthlyReportResponse } from "@/lib/apiClient";

const getMonthlyReport = vi.fn();
const listArchive = vi.fn();
const generateArchive = vi.fn();
const monthlyReportPdfUrl = vi.fn().mockReturnValue("/rapport.pdf");
const archivePdfUrl = vi.fn().mockReturnValue("/archief.pdf");

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getMonthlyReport: (...a: unknown[]) => getMonthlyReport(...a),
    listArchive: (...a: unknown[]) => listArchive(...a),
    generateArchive: (...a: unknown[]) => generateArchive(...a),
    monthlyReportPdfUrl: (...a: unknown[]) => monthlyReportPdfUrl(...a),
    archivePdfUrl: (...a: unknown[]) => archivePdfUrl(...a),
  },
}));

import RapportenPage from "./page";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function makeReport(
  overrides: Partial<MonthlyReportResponse> = {},
): MonthlyReportResponse {
  return {
    title_nl: "Maandrapport 2026-06",
    help_nl: "help",
    year: 2026,
    month: 6,
    executive_summary: {
      headline_nl: "0 trades in juni 2026.",
      net_local_by_currency: {},
      vs_baseline_eur: null,
      trade_count: 0,
      hit_rate_pct: 0,
    },
    open_positions_count: 0,
    action_draft_activity: {
      proposed: 0,
      user_approved: 0,
      submitted: 0,
      filled: 0,
      dismissed: 0,
    },
    verdict_activity: {
      total: 0,
      by_decision: {},
    },
    income: {
      capital_gains_local_by_currency: {},
      tob_local_by_currency: {},
      net_local_by_currency: {},
      ytd_net_local_by_currency: {},
    },
    software_performance: {
      hit_rate_pct: 0,
      average_hold_days: 0,
      confidence_distribution_pct: {},
      proposals_vs_approved: [0, 0],
    },
    realised_trades: [],
    notes_nl: ["EUR-conversie nog niet beschikbaar."],
    ...overrides,
  };
}

beforeEach(() => {
  getMonthlyReport.mockReset();
  listArchive.mockReset();
  listArchive.mockResolvedValue({
    ok: true as const,
    data: { title_nl: "", help_nl: "", items: [] },
  });
  generateArchive.mockReset();
});

afterEach(() => cleanup());

describe("RapportenPage", () => {
  it("renders year + month selectors", async () => {
    getMonthlyReport.mockResolvedValue({
      ok: true as const,
      data: makeReport(),
    });
    render(<RapportenPage />);
    expect(
      await screen.findByTestId("rapport-year-select"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("rapport-month-select")).toBeInTheDocument();
  });

  it("renders the executive summary headline from the response", async () => {
    getMonthlyReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        executive_summary: {
          headline_nl: "3 trades gesloten in 2026-06; hit-rate +4% = 66,7%.",
          net_local_by_currency: { USD: "200.00" },
          vs_baseline_eur: null,
          trade_count: 3,
          hit_rate_pct: 66.7,
        },
      }),
    });
    render(<RapportenPage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("rapport-executive-headline").textContent,
      ).toContain("3 trades");
    });
  });

  it("shows baseline comparison line when EUR net present", async () => {
    getMonthlyReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        executive_summary: {
          headline_nl: "headline",
          net_local_by_currency: { EUR: "500.00" },
          vs_baseline_eur: "€396 bovenop de termijnrekening-baseline.",
          trade_count: 1,
          hit_rate_pct: 100,
        },
      }),
    });
    render(<RapportenPage />);
    expect(
      await screen.findByTestId("rapport-executive-baseline"),
    ).toHaveTextContent("baseline");
  });

  it("renders action draft activity counts", async () => {
    getMonthlyReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        action_draft_activity: {
          proposed: 7,
          user_approved: 5,
          submitted: 3,
          filled: 2,
          dismissed: 1,
        },
      }),
    });
    render(<RapportenPage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("rapport-activity-proposed").textContent,
      ).toBe("7");
    });
    expect(screen.getByTestId("rapport-activity-approved").textContent).toBe("5");
    expect(screen.getByTestId("rapport-activity-submitted").textContent).toBe("3");
    expect(screen.getByTestId("rapport-activity-filled").textContent).toBe("2");
    expect(screen.getByTestId("rapport-activity-dismissed").textContent).toBe("1");
  });

  it("renders open positions count", async () => {
    getMonthlyReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({ open_positions_count: 11 }),
    });
    render(<RapportenPage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("rapport-open-positions-count").textContent,
      ).toBe("11");
    });
  });

  it("renders income breakdown with YTD", async () => {
    getMonthlyReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        income: {
          capital_gains_local_by_currency: { USD: "300.00" },
          tob_local_by_currency: { USD: "7.00" },
          net_local_by_currency: { USD: "293.00" },
          ytd_net_local_by_currency: { USD: "850.00" },
        },
      }),
    });
    render(<RapportenPage />);
    await waitFor(() => {
      expect(
        screen.getByTestId("rapport-income-net").textContent,
      ).toContain("USD");
    });
    expect(screen.getByTestId("rapport-income-ytd").textContent).toContain(
      "850",
    );
  });

  it("renders confidence distribution buckets", async () => {
    getMonthlyReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        software_performance: {
          hit_rate_pct: 60,
          average_hold_days: 40,
          confidence_distribution_pct: {
            ">=90%": 25,
            "80-90%": 50,
            "70-80%": 25,
          },
          proposals_vs_approved: [12, 7],
        },
      }),
    });
    render(<RapportenPage />);
    expect(
      await screen.findByTestId("rapport-confidence-distribution"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("rapport-confidence-bucket->=90%"),
    ).toHaveTextContent("25,0");
  });

  it("renders verdict activity list when verdicts present", async () => {
    getMonthlyReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        verdict_activity: {
          total: 5,
          by_decision: { suggest: 3, skip_macro_regime: 2 },
        },
      }),
    });
    render(<RapportenPage />);
    expect(
      await screen.findByTestId("rapport-verdict-suggest"),
    ).toHaveTextContent("3");
    expect(
      screen.getByTestId("rapport-verdict-skip_macro_regime"),
    ).toHaveTextContent("2");
  });

  it("renders empty trades message when no realised trades", async () => {
    getMonthlyReport.mockResolvedValue({
      ok: true as const,
      data: makeReport(),
    });
    render(<RapportenPage />);
    expect(
      await screen.findByTestId("rapport-trades-empty"),
    ).toBeInTheDocument();
  });

  it("renders one row per realised trade", async () => {
    getMonthlyReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        realised_trades: [
          {
            symbol: "AAPL",
            currency_local: "USD",
            quantity: "10",
            buy_date: "2026-05-10",
            sell_date: "2026-06-15",
            gross_local: "100.00",
            net_local: "92.65",
            hold_days: 36,
            net_pct_on_cost: "9.27",
          },
        ],
      }),
    });
    render(<RapportenPage />);
    expect(
      await screen.findByTestId("rapport-trades-table"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("rapport-trade-row-AAPL-2026-06-15"),
    ).toBeInTheDocument();
  });

  it("renders the notes banner from the response", async () => {
    getMonthlyReport.mockResolvedValue({
      ok: true as const,
      data: makeReport({
        notes_nl: ["EUR-conversie test", "Dividenden test"],
      }),
    });
    render(<RapportenPage />);
    const notes = await screen.findByTestId("rapport-notes");
    expect(notes.textContent).toContain("EUR-conversie");
    expect(notes.textContent).toContain("Dividenden");
  });

  it("refetches when the month changes", async () => {
    getMonthlyReport.mockResolvedValue({
      ok: true as const,
      data: makeReport(),
    });
    render(<RapportenPage />);
    await waitFor(() => {
      expect(getMonthlyReport).toHaveBeenCalled();
    });
    const callsBefore = getMonthlyReport.mock.calls.length;
    fireEvent.change(screen.getByTestId("rapport-month-select"), {
      target: { value: "3" },
    });
    await waitFor(() => {
      expect(getMonthlyReport.mock.calls.length).toBeGreaterThan(callsBefore);
    });
    const lastCall = getMonthlyReport.mock.calls.at(-1)?.[0];
    expect(lastCall.month).toBe(3);
  });
});
