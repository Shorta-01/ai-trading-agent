import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DigestTodayResponse } from "@/lib/apiClient";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const getDigestToday = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getDigestToday: (...a: unknown[]) => getDigestToday(...a),
  },
}));

import Page from "./page";

const ok = <T,>(data: T) => ({ ok: true as const, data });

const SAMPLE: DigestTodayResponse = {
  status: "ready",
  status_nl: "Einde-dag digest beschikbaar",
  help_nl: "Help text.",
  generated_at: "2026-05-31T17:45:00+00:00",
  briefing_date: "2026-05-31",
  market_code: "EURONEXT",
  nav_summary: {
    total_nav: "100000.00",
    delta_abs: "-500.00",
    delta_pct: "-0.50",
    currency: "EUR",
    computed_from: "nav_snapshots",
  },
  positions_summary: {
    position_count: 3,
    by_currency: { EUR: 3 },
    top_winners: [
      { symbol: "GOOG", pnl_pct: "3.00", pnl_abs: "120.00", currency: "USD" },
    ],
    top_losers: [
      {
        symbol: "AMZN",
        pnl_pct: "-6.50",
        pnl_abs: "-200.00",
        currency: "USD",
      },
    ],
  },
  suggestions_summary: {
    total: 5,
    by_action_label: { Houden: 4, Bekijken: 1 },
    new_today: 5,
    high_confidence_count: 1,
  },
  action_drafts_summary: {
    created_today: 1,
    approved_today: 0,
    submitted_today: 0,
    cancelled_today: 0,
    by_state: { draft: 1 },
  },
  alerts: [
    {
      kind: "nav_drop",
      severity_nl: "Waarschuwing",
      title_nl: "NAV daalt -0.50%",
      body_nl: "Bekijk top-losers.",
      reference_kind: "nav",
      reference_id: null,
    },
  ],
  safe_for_orders: false,
};

beforeEach(() => {
  getDigestToday.mockReset();
  getDigestToday.mockReturnValue(ok(SAMPLE));
});

afterEach(() => cleanup());

describe("DigestPage", () => {
  it("renders four cards + alerts when digest is ready", async () => {
    render(<Page />);
    expect(await screen.findByTestId("digest-card-nav")).toBeInTheDocument();
    expect(screen.getByTestId("digest-card-positions")).toBeInTheDocument();
    expect(screen.getByTestId("digest-card-suggestions")).toBeInTheDocument();
    expect(
      screen.getByTestId("digest-card-action-drafts"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("digest-alert-nav_drop")).toHaveTextContent(
      "NAV daalt",
    );
  });

  it("renders empty state when no digest exists", async () => {
    getDigestToday.mockReturnValue(
      ok({
        ...SAMPLE,
        status: "no_digest",
        status_nl: "Nog geen einde-dag digest beschikbaar",
        generated_at: null,
        briefing_date: null,
        market_code: null,
        nav_summary: {},
        positions_summary: {},
        suggestions_summary: {},
        action_drafts_summary: {},
        alerts: [],
      }),
    );
    render(<Page />);
    expect(await screen.findByTestId("digest-empty")).toHaveTextContent(
      "Geen digest beschikbaar",
    );
  });

  it("links to /suggesties from the suggestions card", async () => {
    render(<Page />);
    const link = await screen.findByTestId("digest-card-suggestions-link");
    expect(link).toHaveAttribute("href", "/suggesties");
  });
});
