import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  WatchlistConfirmationStateResponse,
  WatchlistItemResponse,
} from "@/lib/apiClient";

const getWatchlistConfirmationState = vi.fn();
const listWatchlistItems = vi.fn();
const getMarketDataLatestSnapshotStatus = vi.fn();
const getForecastsByAccount = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getWatchlistConfirmationState: (...a: unknown[]) =>
      getWatchlistConfirmationState(...a),
    getForecastsByAccount: (...a: unknown[]) => getForecastsByAccount(...a),
    getLatestDecisionPackage: vi.fn(),
    createActionDraft: vi.fn(),
  },
  listWatchlistItems: (...a: unknown[]) => listWatchlistItems(...a),
  getMarketDataLatestSnapshotStatus: (...a: unknown[]) =>
    getMarketDataLatestSnapshotStatus(...a),
  archiveWatchlistItem: vi.fn(),
  createWatchlistItem: vi.fn(),
  importIbkrWatchlist: vi.fn(),
  listIbkrWatchlistInstruments: vi.fn(),
  listIbkrWatchlists: vi.fn(),
  searchIbkrContracts: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/components/ExportSuggestionsButton", () => ({
  ExportSuggestionsButton: () => null,
}));
vi.mock("@/components/ForecastExplanationPanel", () => ({
  ForecastExplanationPanel: () => null,
}));
vi.mock("@/components/VolglijstColdStartFlow", () => ({
  VolglijstColdStartFlow: () => <div data-testid="cold-start-stub" />,
}));

import Page from "./page";

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

const CONFIRMED = {
  account_id: "DU1",
  state: "confirmed",
  banner_text: null,
} as unknown as WatchlistConfirmationStateResponse;

const UNCONFIRMED = {
  account_id: "DU1",
  state: "unconfirmed",
  banner_text: "x",
} as unknown as WatchlistConfirmationStateResponse;

const WATCH_ITEM = {
  item: { watchlist_item_id: "wi1", symbol: "ASML", ibkr_conid: "100" },
  ibkr_status_label_nl: "Gevalideerd",
  asset_listing_readiness: { status_nl: "Klaar", next_step_nl: "Geen actie." },
} as unknown as WatchlistItemResponse;

beforeEach(() => {
  getWatchlistConfirmationState.mockReset();
  listWatchlistItems.mockReset();
  getMarketDataLatestSnapshotStatus.mockReset();
  getForecastsByAccount.mockReset();
});
afterEach(() => cleanup());

describe("Volglijst page", () => {
  it("shows the loading gate before confirmation state arrives", () => {
    getWatchlistConfirmationState.mockReturnValue(ok(CONFIRMED));
    render(<Page />);
    expect(screen.getByTestId("volglijst-loading")).toBeInTheDocument();
  });

  it("renders the cold-start flow when unconfirmed", async () => {
    getWatchlistConfirmationState.mockReturnValue(ok(UNCONFIRMED));
    render(<Page />);
    expect(await screen.findByTestId("cold-start-stub")).toBeInTheDocument();
  });

  it("renders the confirmed view with watchlist rows", async () => {
    getWatchlistConfirmationState.mockReturnValue(ok(CONFIRMED));
    listWatchlistItems.mockReturnValue(ok({ items: [WATCH_ITEM] }));
    getMarketDataLatestSnapshotStatus.mockReturnValue(
      ok({ status: "missing_snapshot", next_step_nl: "x" }),
    );
    getForecastsByAccount.mockReturnValue(ok({ items: [] }));
    render(<Page />);
    expect(await screen.findByTestId("volglijst-row-ASML")).toBeInTheDocument();
  });

  it("renders the /suggesties link banner for actionable view", async () => {
    getWatchlistConfirmationState.mockReturnValue(ok(CONFIRMED));
    listWatchlistItems.mockReturnValue(ok({ items: [WATCH_ITEM] }));
    getMarketDataLatestSnapshotStatus.mockReturnValue(
      ok({ status: "missing_snapshot", next_step_nl: "x" }),
    );
    getForecastsByAccount.mockReturnValue(ok({ items: [] }));
    render(<Page />);
    const link = await screen.findByTestId("volglijst-suggesties-link");
    expect(link).toHaveAttribute("href", "/suggesties");
    expect(
      screen.getByTestId("volglijst-suggesties-link-banner"),
    ).toHaveTextContent("actie");
  });

  it("does NOT render the action label or Maak actie button on watchlist rows", async () => {
    getWatchlistConfirmationState.mockReturnValue(ok(CONFIRMED));
    listWatchlistItems.mockReturnValue(ok({ items: [WATCH_ITEM] }));
    getMarketDataLatestSnapshotStatus.mockReturnValue(
      ok({ status: "missing_snapshot", next_step_nl: "x" }),
    );
    getForecastsByAccount.mockReturnValue(
      ok({
        items: [
          {
            conid: "100",
            label: "Kopen",
            p10_log_return: "-0.02",
            p50_log_return: "0.05",
            p90_log_return: "0.10",
            prob_positive: "0.72",
            horizon_trading_days: 21,
            confidence_level: "Hoog",
          },
        ],
      }),
    );
    render(<Page />);
    await screen.findByTestId("volglijst-row-ASML");
    // Action label test id is gone; suggestions live on /suggesties.
    expect(
      screen.queryByTestId("volglijst-forecast-label-ASML"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("volglijst-maak-actie-ASML"),
    ).not.toBeInTheDocument();
    // The informational quantile band still renders.
    expect(
      screen.getByTestId("volglijst-forecast-interval-ASML"),
    ).toBeInTheDocument();
  });
});
