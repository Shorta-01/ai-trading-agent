import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  IbkrCashLatestResponse,
  IbkrConnectionStatusResponse,
  IbkrPositionsLatestResponse,
  MarketDataByAccountResponse,
} from "@/lib/apiClient";

const getIbkrConnectionStatus = vi.fn();
const getIbkrSyncPositionsLatest = vi.fn();
const getIbkrSyncCashLatest = vi.fn();
const getMarketDataByAccount = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getIbkrConnectionStatus: (...a: unknown[]) => getIbkrConnectionStatus(...a),
    getIbkrSyncPositionsLatest: (...a: unknown[]) =>
      getIbkrSyncPositionsLatest(...a),
    getIbkrSyncCashLatest: (...a: unknown[]) => getIbkrSyncCashLatest(...a),
    getMarketDataByAccount: (...a: unknown[]) => getMarketDataByAccount(...a),
  },
}));

import { PortefeuilleRealtimeSection } from "./PortefeuilleRealtimeSection";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const CONNECTED = {
  connected: true,
  account_id: "DU•••4567",
  account_mode: "paper",
} as unknown as IbkrConnectionStatusResponse;

const POSITIONS = {
  items: [
    {
      symbol: "ASML",
      conid: "100",
      exchange: "AEB",
      quantity: "10",
      avg_cost: "600.00",
      market_price: "640.00",
      market_value: "6400.00",
      unrealized_pnl: "400.00",
      as_of: "2026-05-28T10:00:00+00:00",
    },
  ],
} as unknown as IbkrPositionsLatestResponse;

const CASH = {
  as_of: "2026-05-28T10:00:00+00:00",
  items: [
    {
      currency: "EUR",
      available_funds: "1000.00",
      net_liquidation_value: "7400.00",
      total_cash_value: "1000.00",
      buying_power: "2000.00",
    },
  ],
} as unknown as IbkrCashLatestResponse;

const MARKET = {
  as_of_date: "2026-05-28",
  fetched_via: "snapshot",
  items: [],
} as unknown as MarketDataByAccountResponse;

function ok<T>(data: T) {
  return Promise.resolve({ ok: true as const, data });
}
function fail() {
  return Promise.resolve({ ok: false as const, reason: "not_reachable" });
}

beforeEach(() => {
  getIbkrConnectionStatus.mockReset();
  getIbkrSyncPositionsLatest.mockReset();
  getIbkrSyncCashLatest.mockReset();
  getMarketDataByAccount.mockReset();
});
afterEach(() => cleanup());

describe("PortefeuilleRealtimeSection", () => {
  it("shows the loading skeleton on first render", () => {
    getIbkrConnectionStatus.mockReturnValue(ok(CONNECTED));
    getIbkrSyncPositionsLatest.mockReturnValue(ok(POSITIONS));
    getIbkrSyncCashLatest.mockReturnValue(ok(CASH));
    getMarketDataByAccount.mockReturnValue(ok(MARKET));
    render(<PortefeuilleRealtimeSection />);
    expect(
      screen.getByTestId("portefeuille-realtime-section").dataset.state,
    ).toBe("loading");
  });

  it("renders the connected state with cash and positions", async () => {
    getIbkrConnectionStatus.mockReturnValue(ok(CONNECTED));
    getIbkrSyncPositionsLatest.mockReturnValue(ok(POSITIONS));
    getIbkrSyncCashLatest.mockReturnValue(ok(CASH));
    getMarketDataByAccount.mockReturnValue(ok(MARKET));
    render(<PortefeuilleRealtimeSection />);
    // cash-summary-card only renders in the connected state.
    await screen.findByTestId("cash-summary-card");
    expect(
      screen.getByTestId("portefeuille-realtime-section").dataset.state,
    ).toBe("connected");
    expect(screen.getByTestId("cash-summary-card").dataset.state).toBe(
      "populated",
    );
    expect(screen.getByTestId("positions-grid").dataset.state).toBe(
      "populated",
    );
    expect(screen.getByText("ASML")).toBeInTheDocument();
  });

  it("renders the disconnected banner when not connected", async () => {
    getIbkrConnectionStatus.mockReturnValue(
      ok({ connected: false } as unknown as IbkrConnectionStatusResponse),
    );
    getIbkrSyncPositionsLatest.mockReturnValue(ok(POSITIONS));
    getIbkrSyncCashLatest.mockReturnValue(ok(CASH));
    getMarketDataByAccount.mockReturnValue(ok(MARKET));
    render(<PortefeuilleRealtimeSection />);
    await screen.findByText(/IBKR-verbinding ontbreekt/);
    expect(
      screen.getByTestId("portefeuille-realtime-section").dataset.state,
    ).toBe("disconnected");
  });

  it("surfaces the storage-error note when a read fails", async () => {
    getIbkrConnectionStatus.mockReturnValue(fail());
    getIbkrSyncPositionsLatest.mockReturnValue(fail());
    getIbkrSyncCashLatest.mockReturnValue(fail());
    getMarketDataByAccount.mockReturnValue(fail());
    render(<PortefeuilleRealtimeSection />);
    expect(
      await screen.findByText("De opslag is momenteel niet bereikbaar."),
    ).toBeInTheDocument();
  });
});
