import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ColdStartWatchlistItem } from "@/lib/apiClient";

const getColdStartWatchlistItems = vi.fn();
const deleteColdStartWatchlistItem = vi.fn();
const confirmWatchlist = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getColdStartWatchlistItems: (...a: unknown[]) =>
      getColdStartWatchlistItems(...a),
    deleteColdStartWatchlistItem: (...a: unknown[]) =>
      deleteColdStartWatchlistItem(...a),
    confirmWatchlist: (...a: unknown[]) => confirmWatchlist(...a),
  },
}));

import { VolglijstColdStartFlow } from "./VolglijstColdStartFlow";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const ITEMS = [
  {
    watchlist_item_id: "w1",
    symbol: "ASML",
    name: "ASML Holding",
    exchange: "AEB",
  },
  {
    watchlist_item_id: "w2",
    symbol: "SHELL",
    name: "Shell",
    exchange: "AEB",
  },
] as unknown as ColdStartWatchlistItem[];

function ok<T>(data: T) {
  return Promise.resolve({ ok: true as const, data });
}

beforeEach(() => {
  getColdStartWatchlistItems.mockReset();
  deleteColdStartWatchlistItem.mockReset();
  confirmWatchlist.mockReset();
});
afterEach(() => cleanup());

describe("VolglijstColdStartFlow", () => {
  it("renders the seeded starter rows", async () => {
    getColdStartWatchlistItems.mockReturnValue(ok({ items: ITEMS }));
    render(<VolglijstColdStartFlow onConfirmed={() => {}} />);
    expect(await screen.findByTestId("cold-start-row-ASML")).toBeInTheDocument();
    expect(screen.getByTestId("cold-start-row-SHELL")).toBeInTheDocument();
  });

  it("shows the empty hint when the starter list is empty", async () => {
    getColdStartWatchlistItems.mockReturnValue(ok({ items: [] }));
    render(<VolglijstColdStartFlow onConfirmed={() => {}} />);
    expect(
      await screen.findByTestId("cold-start-empty-list"),
    ).toBeInTheDocument();
  });

  it("removes a row after a successful delete", async () => {
    getColdStartWatchlistItems.mockReturnValue(ok({ items: ITEMS }));
    deleteColdStartWatchlistItem.mockReturnValue(ok({ ok: true }));
    render(<VolglijstColdStartFlow onConfirmed={() => {}} />);
    await screen.findByTestId("cold-start-row-ASML");
    await userEvent.click(screen.getByTestId("cold-start-verwijder-ASML"));
    await waitFor(() =>
      expect(deleteColdStartWatchlistItem).toHaveBeenCalledWith("w1"),
    );
    await waitFor(() =>
      expect(screen.queryByTestId("cold-start-row-ASML")).toBeNull(),
    );
    expect(screen.getByTestId("cold-start-row-SHELL")).toBeInTheDocument();
  });

  it("confirms with the phrase and fires onConfirmed", async () => {
    getColdStartWatchlistItems.mockReturnValue(ok({ items: ITEMS }));
    confirmWatchlist.mockReturnValue(ok({ ok: true }));
    const onConfirmed = vi.fn();
    render(<VolglijstColdStartFlow onConfirmed={onConfirmed} />);
    await screen.findByTestId("cold-start-row-ASML");
    await userEvent.type(
      screen.getByTestId("cold-start-phrase-input"),
      "BEVESTIG",
    );
    await userEvent.click(screen.getByTestId("cold-start-confirm-button"));
    await waitFor(() =>
      expect(confirmWatchlist).toHaveBeenCalledWith("BEVESTIG"),
    );
    expect(onConfirmed).toHaveBeenCalledTimes(1);
  });
});
