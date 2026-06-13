import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type {
  WatchlistFavoriteRow,
  WatchlistFavoritesResponse,
} from "@/lib/apiClient";

const listFavorieten = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    listFavorieten: (...a: unknown[]) => listFavorieten(...a),
  },
}));

import { FavorietenWidget } from "./FavorietenWidget";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function makeRow(
  overrides: Partial<WatchlistFavoriteRow> & { symbol: string },
): WatchlistFavoriteRow {
  return {
    watchlist_preference_id: `pref-${overrides.symbol}`,
    note: null,
    created_at: "2026-06-13T08:00:00Z",
    latest_decision: null,
    latest_blocking_reason: null,
    latest_summary_nl: null,
    latest_generated_at: null,
    latest_confidence: null,
    ...overrides,
  };
}

function makeResponse(
  items: WatchlistFavoriteRow[],
): WatchlistFavoritesResponse {
  return {
    title_nl: "Favorieten",
    help_nl: "help",
    account_id: "default",
    items,
  };
}

beforeEach(() => {
  listFavorieten.mockReset();
});

afterEach(() => cleanup());

describe("FavorietenWidget", () => {
  it("renders each favorite with its symbol and live confidence", async () => {
    listFavorieten.mockResolvedValue({
      ok: true as const,
      data: makeResponse([
        makeRow({
          symbol: "AAPL",
          latest_decision: "suggest",
          latest_confidence: 0.88,
          latest_summary_nl: "AAPL haalt de drempel",
        }),
        makeRow({
          symbol: "ASML.AS",
          latest_decision: null,
          latest_confidence: null,
        }),
      ]),
    });
    render(<FavorietenWidget />);

    expect(await screen.findByTestId("favoriet-row-AAPL")).toBeInTheDocument();
    expect(screen.getByTestId("favoriet-row-ASML.AS")).toBeInTheDocument();
    expect(screen.getByTestId("favoriet-confidence-AAPL")).toHaveTextContent(
      "88,0 %",
    );
    expect(screen.getByTestId("favoriet-decision-AAPL")).toHaveTextContent(
      "Voorstel",
    );
    expect(screen.getByTestId("favoriet-summary-AAPL")).toHaveTextContent(
      "AAPL haalt de drempel",
    );
  });

  it("shows 'Nog geen score' when a favorite has no orchestrator verdict yet", async () => {
    listFavorieten.mockResolvedValue({
      ok: true as const,
      data: makeResponse([makeRow({ symbol: "NEW" })]),
    });
    render(<FavorietenWidget />);
    expect(
      await screen.findByTestId("favoriet-decision-NEW"),
    ).toHaveTextContent("Nog geen score");
    expect(screen.getByTestId("favoriet-confidence-NEW")).toHaveTextContent(
      "—",
    );
  });

  it("shows 'Geblokkeerd door gate' for skip_* decisions and surfaces the reason", async () => {
    listFavorieten.mockResolvedValue({
      ok: true as const,
      data: makeResponse([
        makeRow({
          symbol: "TSLA",
          latest_decision: "skip_macro_regime",
          latest_blocking_reason: "vix_above_threshold",
          latest_confidence: 0.62,
        }),
      ]),
    });
    render(<FavorietenWidget />);
    expect(
      await screen.findByTestId("favoriet-decision-TSLA"),
    ).toHaveTextContent("Geblokkeerd door gate");
    expect(screen.getByTestId("favoriet-blocking-TSLA")).toHaveTextContent(
      "vix_above_threshold",
    );
  });

  it("renders the operator note when present", async () => {
    listFavorieten.mockResolvedValue({
      ok: true as const,
      data: makeResponse([
        makeRow({ symbol: "AAPL", note: "tip van broer" }),
      ]),
    });
    render(<FavorietenWidget />);
    expect(
      await screen.findByTestId("favoriet-note-AAPL"),
    ).toHaveTextContent("tip van broer");
  });

  it("renders Dutch empty state when no favorites are configured", async () => {
    listFavorieten.mockResolvedValue({
      ok: true as const,
      data: makeResponse([]),
    });
    render(<FavorietenWidget />);
    expect(
      await screen.findByText("Nog geen favorieten"),
    ).toBeInTheDocument();
  });

  it("handles API errors by rendering empty state", async () => {
    listFavorieten.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    render(<FavorietenWidget />);
    expect(
      await screen.findByText("Nog geen favorieten"),
    ).toBeInTheDocument();
  });
});
