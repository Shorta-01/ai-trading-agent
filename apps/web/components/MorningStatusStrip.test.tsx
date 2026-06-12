import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";

const getMarketHoursNow = vi.fn();
const getIbkrSyncStatus = vi.fn();
const getSchedulerJobs = vi.fn();
const getActiveSystemEvents = vi.fn();
const getReconciliationStatus = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getMarketHoursNow: (...a: unknown[]) => getMarketHoursNow(...a),
    getIbkrSyncStatus: (...a: unknown[]) => getIbkrSyncStatus(...a),
    getSchedulerJobs: (...a: unknown[]) => getSchedulerJobs(...a),
    getActiveSystemEvents: (...a: unknown[]) => getActiveSystemEvents(...a),
    getReconciliationStatus: (...a: unknown[]) => getReconciliationStatus(...a),
  },
}));

import { MorningStatusStrip } from "./MorningStatusStrip";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const ok = <T,>(data: T) => ({ ok: true as const, data });

beforeEach(() => {
  getMarketHoursNow.mockReset();
  getIbkrSyncStatus.mockReset();
  getSchedulerJobs.mockReset();
  getActiveSystemEvents.mockReset();
  getReconciliationStatus.mockReset();
  getReconciliationStatus.mockResolvedValue(
    ok({
      ibkr_account_id: "DU1",
      latest_run: null,
      drafts_healed_last_24h: 0,
      pending_manual_review_count: 0,
      unresolved_unmatched_count: 0,
    }),
  );
});

afterEach(() => cleanup());

describe("MorningStatusStrip", () => {
  it("renders five chips: date, market, sync, briefing, alerts", async () => {
    getMarketHoursNow.mockResolvedValue(
      ok({
        now_utc: "2026-06-12T08:00:00Z",
        universe_codes_selected: ["EURONEXT"],
        markets: [
          {
            market_code: "EURONEXT",
            market_label_nl: "Euronext",
            timezone: "Europe/Brussels",
            open_at_utc: "",
            close_at_utc: "",
            open_local_hhmm: "09:00",
            close_local_hhmm: "17:30",
            state: "open",
            state_nl: "Open",
            next_event_kind: null,
            next_event_at_utc: null,
          },
        ],
        help_nl: "",
      }),
    );
    getIbkrSyncStatus.mockResolvedValue(
      ok({
        configured: true,
        last_sync_at: "2026-06-12T05:30:00Z",
      }),
    );
    getSchedulerJobs.mockResolvedValue(
      ok({
        status: "ok",
        scheduler_enabled: true,
        scheduler_timezone: "Europe/Brussels",
        scheduler_daily_briefing_cron: "0 7 * * *",
        items: [{ next_run_at: "2026-06-13T05:00:00Z" }],
      }),
    );
    getActiveSystemEvents.mockResolvedValue(ok({ events: [] }));

    render(<MorningStatusStrip />);
    await waitFor(() => {
      expect(
        screen.getByTestId("morning-status-strip-market"),
      ).toHaveTextContent("Markt open");
    });
    expect(
      screen.getByTestId("morning-status-strip-sync"),
    ).toHaveTextContent("IBKR-sync");
    expect(
      screen.getByTestId("morning-status-strip-briefing"),
    ).toHaveTextContent("Volgende briefing");
    expect(
      screen.getByTestId("morning-status-strip-alerts"),
    ).toHaveTextContent("Geen actieve meldingen");
    expect(screen.getByTestId("morning-status-strip-date")).toBeInTheDocument();
  });

  it("shows alert count and elevates tone when events exist", async () => {
    getMarketHoursNow.mockResolvedValue(ok({ markets: [], help_nl: "", now_utc: "", universe_codes_selected: [] }));
    getIbkrSyncStatus.mockResolvedValue(ok({ configured: false }));
    getSchedulerJobs.mockResolvedValue(ok({ status: "error", items: [] }));
    getActiveSystemEvents.mockResolvedValue(
      ok({
        events: [
          { event_id: "e1" },
          { event_id: "e2" },
          { event_id: "e3" },
        ],
      }),
    );
    render(<MorningStatusStrip />);
    await waitFor(() => {
      expect(
        screen.getByTestId("morning-status-strip-alerts"),
      ).toHaveTextContent("3 actieve meldingen");
    });
  });

  it("falls back to 'IBKR-sync ontbreekt' when no sync has been done", async () => {
    getMarketHoursNow.mockResolvedValue(ok({ markets: [], help_nl: "", now_utc: "", universe_codes_selected: [] }));
    getIbkrSyncStatus.mockResolvedValue(ok({ configured: true, last_sync_at: null }));
    getSchedulerJobs.mockResolvedValue(ok({ status: "ok", items: [] }));
    getActiveSystemEvents.mockResolvedValue(ok({ events: [] }));
    render(<MorningStatusStrip />);
    await waitFor(() => {
      expect(
        screen.getByTestId("morning-status-strip-sync"),
      ).toHaveTextContent("IBKR-sync ontbreekt");
    });
  });

  it("shows reconciliation mismatch count when any are pending", async () => {
    getMarketHoursNow.mockResolvedValue(ok({ markets: [], help_nl: "", now_utc: "", universe_codes_selected: [] }));
    getIbkrSyncStatus.mockResolvedValue(ok({ configured: true, last_sync_at: null }));
    getSchedulerJobs.mockResolvedValue(ok({ status: "ok", items: [] }));
    getActiveSystemEvents.mockResolvedValue(ok({ events: [] }));
    getReconciliationStatus.mockResolvedValue(
      ok({
        ibkr_account_id: "DU1",
        latest_run: null,
        drafts_healed_last_24h: 0,
        pending_manual_review_count: 2,
        unresolved_unmatched_count: 1,
      }),
    );
    render(<MorningStatusStrip />);
    await waitFor(() => {
      expect(
        screen.getByTestId("morning-status-strip-reconciliation"),
      ).toHaveTextContent("Reconciliation: 3 mismatches");
    });
  });
});
