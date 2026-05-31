import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { MarketHoursNowResponse } from "@/lib/apiClient";

const getMarketHoursNow = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getMarketHoursNow: (...a: unknown[]) => getMarketHoursNow(...a),
  },
}));

import { MarketHoursWidget } from "./MarketHoursWidget";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function ok(data: MarketHoursNowResponse) {
  return Promise.resolve({ ok: true as const, data });
}

function fail() {
  return Promise.resolve({ ok: false as const, reason: "not_reachable" });
}

beforeEach(() => getMarketHoursNow.mockReset());
afterEach(() => cleanup());

describe("MarketHoursWidget", () => {
  it("renders one row per followed market with the open/close range", async () => {
    getMarketHoursNow.mockReturnValue(
      ok({
        now_utc: "2026-06-03T10:00:00+00:00",
        universe_codes_selected: ["BEL20", "DAX40"],
        markets: [
          {
            market_code: "EURONEXT",
            market_label_nl: "Euronext — Brussel, Amsterdam, Parijs",
            timezone: "Europe/Brussels",
            open_at_utc: "2026-06-03T07:00:00+00:00",
            close_at_utc: "2026-06-03T15:30:00+00:00",
            open_local_hhmm: "09:00",
            close_local_hhmm: "17:30",
            state: "open",
            state_nl: "Open; sluit om 17:30 (Europe/Brussels).",
            next_event_kind: "close",
            next_event_at_utc: "2026-06-03T15:30:00+00:00",
          },
          {
            market_code: "XETRA",
            market_label_nl: "Deutsche Börse Xetra (Frankfurt)",
            timezone: "Europe/Berlin",
            open_at_utc: "2026-06-03T07:00:00+00:00",
            close_at_utc: "2026-06-03T15:30:00+00:00",
            open_local_hhmm: "09:00",
            close_local_hhmm: "17:30",
            state: "open",
            state_nl: "Open; sluit om 17:30 (Europe/Berlin).",
            next_event_kind: "close",
            next_event_at_utc: "2026-06-03T15:30:00+00:00",
          },
        ],
        help_nl: "Volgt je universe-scan selectie.",
      }),
    );
    render(<MarketHoursWidget />);
    expect(
      await screen.findByTestId("market-hours-row-EURONEXT"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("market-hours-row-XETRA"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Euronext/)).toBeInTheDocument();
    expect(screen.getAllByText(/09:00.*17:30.*Europe/).length).toBeGreaterThan(0);
  });

  it("renders the empty-state message when no markets are selected", async () => {
    getMarketHoursNow.mockReturnValue(
      ok({
        now_utc: "2026-06-03T10:00:00+00:00",
        universe_codes_selected: [],
        markets: [],
        help_nl: "Volgt je universe-scan selectie.",
      }),
    );
    render(<MarketHoursWidget />);
    const empty = await screen.findByTestId("market-hours-empty");
    expect(empty.textContent).toContain("Geen markten gekozen");
  });

  it("shows the error message when the API is unreachable", async () => {
    getMarketHoursNow.mockReturnValue(fail());
    render(<MarketHoursWidget />);
    expect(
      await screen.findByTestId("market-hours-error"),
    ).toBeInTheDocument();
  });

  it("tags each row with the market state for downstream styling", async () => {
    getMarketHoursNow.mockReturnValue(
      ok({
        now_utc: "2026-06-03T06:00:00+00:00",
        universe_codes_selected: ["BEL20"],
        markets: [
          {
            market_code: "EURONEXT",
            market_label_nl: "Euronext",
            timezone: "Europe/Brussels",
            open_at_utc: "2026-06-03T07:00:00+00:00",
            close_at_utc: "2026-06-03T15:30:00+00:00",
            open_local_hhmm: "09:00",
            close_local_hhmm: "17:30",
            state: "pre_open",
            state_nl: "Opent vandaag om 09:00 (Europe/Brussels).",
            next_event_kind: "open",
            next_event_at_utc: "2026-06-03T07:00:00+00:00",
          },
        ],
        help_nl: "x",
      }),
    );
    render(<MarketHoursWidget />);
    const row = await screen.findByTestId("market-hours-row-EURONEXT");
    await waitFor(() =>
      expect(row.getAttribute("data-market-state")).toBe("pre_open"),
    );
  });

  it("falls back to the deterministic state_nl when there's no next event", async () => {
    getMarketHoursNow.mockReturnValue(
      ok({
        now_utc: "2026-06-06T10:00:00+00:00",
        universe_codes_selected: ["BEL20"],
        markets: [
          {
            market_code: "EURONEXT",
            market_label_nl: "Euronext",
            timezone: "Europe/Brussels",
            open_at_utc: "2026-06-06T07:00:00+00:00",
            close_at_utc: "2026-06-06T15:30:00+00:00",
            open_local_hhmm: "09:00",
            close_local_hhmm: "17:30",
            state: "weekend",
            state_nl: "Markt gesloten (weekend).",
            next_event_kind: null,
            next_event_at_utc: null,
          },
        ],
        help_nl: "x",
      }),
    );
    render(<MarketHoursWidget />);
    const row = await screen.findByTestId("market-hours-row-EURONEXT");
    expect(row.textContent).toContain("weekend");
  });
});
