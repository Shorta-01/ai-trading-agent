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
  EarningsRefreshResponse,
  IbkrPositionSnapshot,
} from "@/lib/apiClient";

const getIbkrPositions = vi.fn();
const refreshEarnings = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getIbkrPositions: (...a: unknown[]) => getIbkrPositions(...a),
    refreshEarnings: (...a: unknown[]) => refreshEarnings(...a),
  },
}));

import { EarningsRefreshButton } from "./EarningsRefreshButton";

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

const ok = <T,>(data: T) => ({ ok: true as const, data });

function pos(
  symbol: string,
  exchange: string,
  quantity: string,
): IbkrPositionSnapshot {
  return {
    sync_run_id: "sr",
    account_ref: "DU1",
    symbol,
    security_type: "STK",
    currency: "USD",
    quantity,
    average_cost: null,
    exchange,
    timestamp: "2026-06-12T05:00:00Z",
  };
}

const REFRESH_OK: EarningsRefreshResponse = {
  status: "ok",
  fetched_count: 2,
  upserted_count: 2,
  symbols_requested: 2,
  window_days: 21,
  error_text: null,
  safe_for_orders: false,
};

beforeEach(() => {
  getIbkrPositions.mockReset();
  refreshEarnings.mockReset();
});

afterEach(() => cleanup());

describe("EarningsRefreshButton", () => {
  it("disables the button when there are no held positions", async () => {
    getIbkrPositions.mockResolvedValue(ok({ items: [] }));
    render(<EarningsRefreshButton />);
    const button = await screen.findByTestId("earnings-refresh-button");
    await waitFor(() => {
      expect(button).toBeDisabled();
    });
    expect(button).toHaveTextContent("Geen posities");
  });

  it("maps positions to EODHD symbols and skips unmapped exchanges", async () => {
    getIbkrPositions.mockResolvedValue(
      ok({
        items: [
          pos("AAPL", "NASDAQ", "10"),
          pos("ZERO", "NASDAQ", "0"),
          pos("MSFT", "NASDAQ", "5"),
          pos("UNKNOWN", "UNMAPPED", "5"),
        ],
      }),
    );
    refreshEarnings.mockResolvedValue(ok(REFRESH_OK));
    render(<EarningsRefreshButton />);
    const button = await screen.findByTestId("earnings-refresh-button");
    await waitFor(() => {
      expect(button).toHaveTextContent("2 symbolen");
    });
    fireEvent.click(button);
    await waitFor(() => {
      expect(refreshEarnings).toHaveBeenCalledWith({
        symbols: ["AAPL.US", "MSFT.US"],
        window_days: 21,
      });
    });
  });

  it("shows the OK message after a successful refresh", async () => {
    getIbkrPositions.mockResolvedValue(
      ok({ items: [pos("AAPL", "NASDAQ", "10")] }),
    );
    refreshEarnings.mockResolvedValue(ok(REFRESH_OK));
    render(<EarningsRefreshButton />);
    const button = await screen.findByTestId("earnings-refresh-button");
    await waitFor(() => expect(button).not.toBeDisabled());
    fireEvent.click(button);
    expect(
      await screen.findByTestId("earnings-refresh-button-result"),
    ).toHaveTextContent("OK — 2 events bijgewerkt");
  });

  it("surfaces the skipped message when the server short-circuits", async () => {
    getIbkrPositions.mockResolvedValue(
      ok({ items: [pos("AAPL", "NASDAQ", "10")] }),
    );
    refreshEarnings.mockResolvedValue(
      ok({
        ...REFRESH_OK,
        status: "skipped",
        upserted_count: 0,
        error_text: "EODHD key ontbreekt",
      }),
    );
    render(<EarningsRefreshButton />);
    const button = await screen.findByTestId("earnings-refresh-button");
    await waitFor(() => expect(button).not.toBeDisabled());
    fireEvent.click(button);
    expect(
      await screen.findByTestId("earnings-refresh-button-result"),
    ).toHaveTextContent("Overgeslagen");
  });

  it("renders an error chip when the request fails", async () => {
    getIbkrPositions.mockResolvedValue(
      ok({ items: [pos("AAPL", "NASDAQ", "10")] }),
    );
    refreshEarnings.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    render(<EarningsRefreshButton />);
    const button = await screen.findByTestId("earnings-refresh-button");
    await waitFor(() => expect(button).not.toBeDisabled());
    fireEvent.click(button);
    expect(
      await screen.findByTestId("earnings-refresh-button-error"),
    ).toHaveTextContent("not_reachable");
  });
});
