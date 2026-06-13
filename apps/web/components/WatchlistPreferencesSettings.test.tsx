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
  WatchlistExclusionsResponse,
  WatchlistFavoritesResponse,
} from "@/lib/apiClient";

const listFavorieten = vi.fn();
const listUitsluitingen = vi.fn();
const saveWatchlistPreference = vi.fn();
const deleteWatchlistPreference = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    listFavorieten: (...a: unknown[]) => listFavorieten(...a),
    listUitsluitingen: (...a: unknown[]) => listUitsluitingen(...a),
    saveWatchlistPreference: (...a: unknown[]) =>
      saveWatchlistPreference(...a),
    deleteWatchlistPreference: (...a: unknown[]) =>
      deleteWatchlistPreference(...a),
  },
}));

import { WatchlistPreferencesSettings } from "./WatchlistPreferencesSettings";

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

function favoritesResponse(
  symbols: string[],
): WatchlistFavoritesResponse {
  return {
    title_nl: "Favorieten",
    help_nl: "help",
    account_id: "default",
    items: symbols.map((symbol) => ({
      watchlist_preference_id: `pref-${symbol}`,
      symbol,
      note: null,
      created_at: "2026-06-13T08:00:00Z",
      latest_decision: null,
      latest_blocking_reason: null,
      latest_summary_nl: null,
      latest_generated_at: null,
      latest_confidence: null,
    })),
  };
}

function exclusionsResponse(
  symbols: string[],
): WatchlistExclusionsResponse {
  return {
    title_nl: "Uitsluitingen",
    help_nl: "help",
    account_id: "default",
    items: symbols.map((symbol) => ({
      watchlist_preference_id: `pref-${symbol}`,
      symbol,
      note: null,
      created_at: "2026-06-13T08:00:00Z",
    })),
  };
}

beforeEach(() => {
  listFavorieten.mockReset();
  listUitsluitingen.mockReset();
  saveWatchlistPreference.mockReset();
  deleteWatchlistPreference.mockReset();
});

afterEach(() => cleanup());

describe("WatchlistPreferencesSettings", () => {
  it("renders both tabs and starts on Favorieten", async () => {
    listFavorieten.mockResolvedValue({
      ok: true as const,
      data: favoritesResponse(["AAPL"]),
    });
    listUitsluitingen.mockResolvedValue({
      ok: true as const,
      data: exclusionsResponse([]),
    });
    render(<WatchlistPreferencesSettings />);
    expect(
      await screen.findByTestId("watchlist-tab-favorieten"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("watchlist-tab-uitsluitingen")).toBeInTheDocument();
    expect(
      await screen.findByTestId("watchlist-favorieten-row-AAPL"),
    ).toBeInTheDocument();
  });

  it("submits a new favorite and refreshes the listing", async () => {
    listFavorieten.mockResolvedValueOnce({
      ok: true as const,
      data: favoritesResponse([]),
    });
    listFavorieten.mockResolvedValue({
      ok: true as const,
      data: favoritesResponse(["MSFT"]),
    });
    listUitsluitingen.mockResolvedValue({
      ok: true as const,
      data: exclusionsResponse([]),
    });
    saveWatchlistPreference.mockResolvedValue({
      ok: true as const,
      data: {
        accepted: true,
        record_id: "abc",
        explanation_nl: "ok",
      },
    });
    render(<WatchlistPreferencesSettings />);
    await screen.findByTestId("watchlist-favorieten-empty");
    fireEvent.change(
      screen.getByTestId("watchlist-favorite-input-symbol"),
      { target: { value: "MSFT" } },
    );
    fireEvent.click(screen.getByTestId("watchlist-favorite-submit"));
    await waitFor(() => {
      expect(saveWatchlistPreference).toHaveBeenCalledWith({
        symbol: "MSFT",
        kind: "favorite",
        note: null,
      });
    });
    expect(
      await screen.findByTestId("watchlist-favorieten-row-MSFT"),
    ).toBeInTheDocument();
  });

  it("submits a favorite with a note when one is provided", async () => {
    listFavorieten.mockResolvedValue({
      ok: true as const,
      data: favoritesResponse([]),
    });
    listUitsluitingen.mockResolvedValue({
      ok: true as const,
      data: exclusionsResponse([]),
    });
    saveWatchlistPreference.mockResolvedValue({
      ok: true as const,
      data: { accepted: true, record_id: "x", explanation_nl: "ok" },
    });
    render(<WatchlistPreferencesSettings />);
    await screen.findByTestId("watchlist-favorieten-empty");
    fireEvent.change(
      screen.getByTestId("watchlist-favorite-input-symbol"),
      { target: { value: "ASML.AS" } },
    );
    fireEvent.change(
      screen.getByTestId("watchlist-favorite-input-note"),
      { target: { value: "tip van broer" } },
    );
    fireEvent.click(screen.getByTestId("watchlist-favorite-submit"));
    await waitFor(() => {
      expect(saveWatchlistPreference).toHaveBeenCalledWith({
        symbol: "ASML.AS",
        kind: "favorite",
        note: "tip van broer",
      });
    });
  });

  it("disables the submit button when the symbol input is empty", async () => {
    listFavorieten.mockResolvedValue({
      ok: true as const,
      data: favoritesResponse([]),
    });
    listUitsluitingen.mockResolvedValue({
      ok: true as const,
      data: exclusionsResponse([]),
    });
    render(<WatchlistPreferencesSettings />);
    const submit = (await screen.findByTestId(
      "watchlist-favorite-submit",
    )) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
  });

  it("removes a favorite via the verwijder button", async () => {
    listFavorieten.mockResolvedValueOnce({
      ok: true as const,
      data: favoritesResponse(["AAPL"]),
    });
    listFavorieten.mockResolvedValue({
      ok: true as const,
      data: favoritesResponse([]),
    });
    listUitsluitingen.mockResolvedValue({
      ok: true as const,
      data: exclusionsResponse([]),
    });
    deleteWatchlistPreference.mockResolvedValue({
      ok: true as const,
      data: { accepted: true, record_id: null, explanation_nl: "weg" },
    });
    render(<WatchlistPreferencesSettings />);
    await screen.findByTestId("watchlist-favorieten-row-AAPL");
    fireEvent.click(
      screen.getByTestId("watchlist-favorieten-remove-AAPL"),
    );
    await waitFor(() => {
      expect(deleteWatchlistPreference).toHaveBeenCalledWith({
        symbol: "AAPL",
        kind: "favorite",
      });
    });
    expect(
      await screen.findByTestId("watchlist-favorieten-empty"),
    ).toBeInTheDocument();
  });

  it("switches to the uitsluitingen tab and submits an exclusion", async () => {
    listFavorieten.mockResolvedValue({
      ok: true as const,
      data: favoritesResponse([]),
    });
    listUitsluitingen.mockResolvedValueOnce({
      ok: true as const,
      data: exclusionsResponse([]),
    });
    listUitsluitingen.mockResolvedValue({
      ok: true as const,
      data: exclusionsResponse(["TSLA"]),
    });
    saveWatchlistPreference.mockResolvedValue({
      ok: true as const,
      data: { accepted: true, record_id: "x", explanation_nl: "ok" },
    });
    render(<WatchlistPreferencesSettings />);
    fireEvent.click(
      await screen.findByTestId("watchlist-tab-uitsluitingen"),
    );
    await screen.findByTestId("watchlist-uitsluitingen-empty");
    fireEvent.change(
      screen.getByTestId("watchlist-excluded-input-symbol"),
      { target: { value: "TSLA" } },
    );
    fireEvent.click(screen.getByTestId("watchlist-excluded-submit"));
    await waitFor(() => {
      expect(saveWatchlistPreference).toHaveBeenCalledWith({
        symbol: "TSLA",
        kind: "excluded",
        note: null,
      });
    });
    expect(
      await screen.findByTestId("watchlist-uitsluitingen-row-TSLA"),
    ).toBeInTheDocument();
  });

  it("shows an error message when the save mutation fails", async () => {
    listFavorieten.mockResolvedValue({
      ok: true as const,
      data: favoritesResponse([]),
    });
    listUitsluitingen.mockResolvedValue({
      ok: true as const,
      data: exclusionsResponse([]),
    });
    saveWatchlistPreference.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    render(<WatchlistPreferencesSettings />);
    await screen.findByTestId("watchlist-favorieten-empty");
    fireEvent.change(
      screen.getByTestId("watchlist-favorite-input-symbol"),
      { target: { value: "AAPL" } },
    );
    fireEvent.click(screen.getByTestId("watchlist-favorite-submit"));
    expect(
      await screen.findByTestId("watchlist-favorite-error"),
    ).toHaveTextContent("Opslaan mislukt");
  });
});
