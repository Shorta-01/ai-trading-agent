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

import type { DividendListResponse } from "@/lib/apiClient";

const listDividenden = vi.fn();
const createDividend = vi.fn();
const deleteDividend = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    listDividenden: (...a: unknown[]) => listDividenden(...a),
    createDividend: (...a: unknown[]) => createDividend(...a),
    deleteDividend: (...a: unknown[]) => deleteDividend(...a),
  },
}));

import { DividendenManager } from "./DividendenManager";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function makeResp(
  overrides: Partial<DividendListResponse> = {},
): DividendListResponse {
  return {
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
    treaty_defaults_pct_by_country: {
      US: "15",
      NL: "15",
      FR: "12.8",
      BE: "0",
    },
    ...overrides,
  };
}

beforeEach(() => {
  listDividenden.mockReset();
  createDividend.mockReset();
  deleteDividend.mockReset();
});

afterEach(() => cleanup());

describe("DividendenManager", () => {
  it("renders empty state when no dividends", async () => {
    listDividenden.mockResolvedValue({
      ok: true as const,
      data: makeResp(),
    });
    render(<DividendenManager year={2026} />);
    expect(
      await screen.findByTestId("dividenden-empty-state"),
    ).toBeInTheDocument();
  });

  it("renders a row per dividend with bronbelasting", async () => {
    listDividenden.mockResolvedValue({
      ok: true as const,
      data: makeResp({
        items: [
          {
            dividend_event_id: "d1",
            symbol: "AAPL",
            isin: null,
            pay_date: "2026-05-12",
            currency_local: "USD",
            gross_local: "100",
            withholding_pct: "15",
            withholding_local: "15",
            net_local: "85",
            country_code: "US",
            note: null,
          },
        ],
      }),
    });
    render(<DividendenManager year={2026} />);
    const row = await screen.findByTestId("dividend-row-AAPL-2026-05-12");
    expect(row.textContent).toContain("AAPL");
    expect(row.textContent).toContain("US");
  });

  it("submits the form via createDividend", async () => {
    listDividenden.mockResolvedValue({
      ok: true as const,
      data: makeResp(),
    });
    createDividend.mockResolvedValue({
      ok: true as const,
      data: { accepted: true, record_id: "x", explanation_nl: "ok" },
    });
    render(<DividendenManager year={2026} />);
    await screen.findByTestId("dividenden-form");
    fireEvent.change(screen.getByTestId("dividend-input-symbol"), {
      target: { value: "MSFT" },
    });
    fireEvent.change(screen.getByTestId("dividend-input-date"), {
      target: { value: "2026-04-10" },
    });
    fireEvent.change(screen.getByTestId("dividend-input-gross"), {
      target: { value: "50" },
    });
    fireEvent.click(screen.getByTestId("dividend-add-button"));
    await waitFor(() => {
      expect(createDividend).toHaveBeenCalled();
    });
    const lastCall = createDividend.mock.calls.at(-1)?.[0];
    expect(lastCall.symbol).toBe("MSFT");
    expect(lastCall.gross_local).toBe("50");
  });

  it("shows error when required fields missing", async () => {
    listDividenden.mockResolvedValue({
      ok: true as const,
      data: makeResp(),
    });
    render(<DividendenManager year={2026} />);
    await screen.findByTestId("dividenden-form");
    fireEvent.click(screen.getByTestId("dividend-add-button"));
    expect(
      await screen.findByTestId("dividenden-error"),
    ).toHaveTextContent("Vul symbool");
  });

  it("calls delete when verwijder is clicked", async () => {
    listDividenden.mockResolvedValue({
      ok: true as const,
      data: makeResp({
        items: [
          {
            dividend_event_id: "d1",
            symbol: "AAPL",
            isin: null,
            pay_date: "2026-05-12",
            currency_local: "USD",
            gross_local: "100",
            withholding_pct: "15",
            withholding_local: "15",
            net_local: "85",
            country_code: "US",
            note: null,
          },
        ],
      }),
    });
    deleteDividend.mockResolvedValue({
      ok: true as const,
      data: { accepted: true, record_id: null, explanation_nl: "ok" },
    });
    render(<DividendenManager year={2026} />);
    await screen.findByTestId("dividend-row-AAPL-2026-05-12");
    fireEvent.click(screen.getByTestId("dividend-delete-d1"));
    await waitFor(() => {
      expect(deleteDividend).toHaveBeenCalledWith("d1");
    });
  });

  it("renders the year totals when items are present", async () => {
    listDividenden.mockResolvedValue({
      ok: true as const,
      data: makeResp({
        items: [
          {
            dividend_event_id: "d1",
            symbol: "AAPL",
            isin: null,
            pay_date: "2026-05-12",
            currency_local: "USD",
            gross_local: "100",
            withholding_pct: "15",
            withholding_local: "15",
            net_local: "85",
            country_code: "US",
            note: null,
          },
        ],
        totals: {
          gross_by_currency: { USD: "100" },
          withholding_by_currency: { USD: "15" },
          net_by_currency: { USD: "85" },
          count: 1,
        },
      }),
    });
    render(<DividendenManager year={2026} />);
    expect(
      await screen.findByTestId("dividenden-totals"),
    ).toHaveTextContent("100,00 USD");
  });
});
