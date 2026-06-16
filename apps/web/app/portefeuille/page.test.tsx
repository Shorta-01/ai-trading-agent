import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitForElementToBeRemoved,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const fns = vi.hoisted(() => ({
  getIbkrSyncStatus: vi.fn(),
  getPortfolioValuationReadiness: vi.fn(),
  getIbkrPositions: vi.fn(),
  getIbkrCash: vi.fn(),
  getIbkrOpenOrders: vi.fn(),
  getIbkrExecutions: vi.fn(),
  getLatestForecasts: vi.fn(),
  getLatestSuggestions: vi.fn(),
  getActiveSystemEvents: vi.fn(),
  resolveSystemEvent: vi.fn(),
  getLatestDecisionPackages: vi.fn(),
  getLatestActionDrafts: vi.fn(),
  getLatestDailyBriefing: vi.fn(),
  getIbkrAccountMode: vi.fn(),
  getSchedulerJobs: vi.fn(),
  getLatestSchedulerRun: vi.fn(),
  getRecentSchedulerRuns: vi.fn(),
}));

vi.mock("@/lib/apiClient", () => ({
  apiClient: new Proxy(fns as Record<string, unknown>, {
    get: (target, prop: string) =>
      target[prop] ?? (() => Promise.resolve({ ok: false, reason: "x" })),
  }),
}));

vi.mock("@/components/PortefeuilleRealtimeSection", () => ({
  PortefeuilleRealtimeSection: () => null,
}));
vi.mock("@/components/PositionPlTraceDetails", () => ({
  PositionPlTraceDetails: () => null,
}));
vi.mock("@/components/ValuationTraceDetails", () => ({
  ValuationTraceDetails: () => null,
}));

import PortfolioPage from "./page";

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
function fail() {
  return Promise.resolve({ ok: false as const, reason: "not_reachable" });
}

function mockAllOk() {
  fns.getIbkrSyncStatus.mockReturnValue(
    ok({ configured: true, status_nl: "Klaar", positions_count: 0 }),
  );
  fns.getPortfolioValuationReadiness.mockReturnValue(
    ok({
      conversion_total_status: "conversion_ready",
      conversion_total_status_nl: "Klaar",
      base_currency: "EUR",
      rows: [],
    }),
  );
  fns.getIbkrPositions.mockReturnValue(ok({ items: [] }));
  fns.getIbkrCash.mockReturnValue(ok({ items: [] }));
  fns.getIbkrOpenOrders.mockReturnValue(ok({ items: [] }));
  fns.getIbkrExecutions.mockReturnValue(ok({ items: [] }));
  fns.getLatestForecasts.mockReturnValue(ok({ items: [] }));
  fns.getLatestSuggestions.mockReturnValue(ok({ items: [] }));
  fns.getLatestDecisionPackages.mockReturnValue(ok({ items: [] }));
  fns.getLatestActionDrafts.mockReturnValue(ok({ items: [] }));
  fns.getLatestDailyBriefing.mockReturnValue(ok({ item: null }));
  fns.getIbkrAccountMode.mockReturnValue(
    ok({ help_nl: "x", label_nl: "Paper", account_mode: "paper" }),
  );
  fns.getSchedulerJobs.mockReturnValue(
    ok({
      status: "ok",
      scheduler_timezone: "UTC",
      scheduler_daily_briefing_cron: "0 7 * * *",
      items: [],
    }),
  );
  fns.getLatestSchedulerRun.mockReturnValue(ok({ item: null }));
  fns.getRecentSchedulerRuns.mockReturnValue(ok({ items: [], limit: 10 }));
}

beforeEach(() => {
  Object.values(fns).forEach((f) => f.mockReset());
});
afterEach(() => cleanup());

describe("PortfolioPage data state machine", () => {
  it("shows the loading state before snapshots arrive", () => {
    mockAllOk();
    render(<PortfolioPage />);
    expect(
      screen.getByText("IBKR snapshots worden opgehaald."),
    ).toBeInTheDocument();
  });

  it("clears the loading state once data resolves", async () => {
    mockAllOk();
    render(<PortfolioPage />);
    await waitForElementToBeRemoved(() =>
      screen.queryByText("IBKR snapshots worden opgehaald."),
    );
  });

  it("shows the sync-failed state when every core read fails", async () => {
    Object.values(fns).forEach((f) => f.mockReturnValue(fail()));
    render(<PortfolioPage />);
    expect(
      await screen.findByText("Sync mislukt. Controleer de IBKR-koppeling."),
    ).toBeInTheDocument();
  });

  it("renders the recent daily-briefing runs tile with rows when present", async () => {
    mockAllOk();
    fns.getRecentSchedulerRuns.mockReturnValue(
      ok({
        items: [
          {
            run_id: "sch_1",
            job_name: "daily_briefing",
            scheduled_at: "2026-05-29T06:30:00+00:00",
            started_at: "2026-05-29T06:30:01+00:00",
            finished_at: "2026-05-29T06:30:42+00:00",
            status: "succeeded",
            error_text: null,
            triggered_by: "scheduler",
          },
          {
            run_id: "sch_2",
            job_name: "daily_briefing",
            scheduled_at: "2026-05-28T06:30:00+00:00",
            started_at: "2026-05-28T06:30:01+00:00",
            finished_at: "2026-05-28T06:30:09+00:00",
            status: "failed",
            error_text: "market_data_sync timeout",
            triggered_by: "scheduler",
          },
        ],
        limit: 10,
      }),
    );
    render(<PortfolioPage />);
    // findByText waits for the query to settle, not just the tile shell.
    expect(await screen.findByText("market_data_sync timeout")).toBeInTheDocument();
    const tile = screen.getByTestId("scheduler-recent-runs");
    expect(tile).toHaveTextContent("Recente daily-briefing runs");
    expect(tile).toHaveTextContent("succeeded");
    expect(tile).toHaveTextContent("failed");
  });

  it("shows the empty hint when no recent runs exist", async () => {
    mockAllOk();
    render(<PortfolioPage />);
    const tile = await screen.findByTestId("scheduler-recent-runs");
    expect(tile).toHaveTextContent("Nog geen runs.");
  });

  it("renders the hint↔actual mismatch warning banner when hint_mismatch=true", async () => {
    // V1.2 §BZ vervolg: wanneer de API rapporteert dat het
    // geconfigureerde hint NIET matcht met het actueel verbonden
    // TWS-account, MOET het dashboard een prominente waarschuwings-
    // banner tonen — anders mist de operator de safety-info.
    mockAllOk();
    fns.getIbkrAccountMode.mockReturnValue(
      ok({
        status: "ok",
        mode: "live",
        display_label: "LIVE",
        expected_environment: "paper",
        detected_source: "connected_session",
        hint_account_id_masked: "DU•••4567",
        actual_account_id_masked: "U7•••4321",
        hint_mismatch: true,
        hint_mismatch_nl:
          "De geconfigureerde IBKR_ACCOUNT_ID_HINT (DU•••4567) verschilt van het actueel verbonden account (U7•••4321).",
        help_nl: "",
        safe_for_orders: false,
        blocks_orders: true,
      }),
    );
    render(<PortfolioPage />);

    const banner = await screen.findByTestId(
      "account-mode-hint-mismatch-banner",
    );
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.textContent).toContain("DU•••4567");
    expect(banner.textContent).toContain("U7•••4321");
    expect(banner.textContent).toContain("mismatch");
  });

  it("does NOT render the mismatch banner when there is no mismatch", async () => {
    // Default mock (hint_mismatch undefined / false) — geen banner.
    mockAllOk();
    render(<PortfolioPage />);
    // findByTestId waits for the page; query for the banner specifically.
    await screen.findByText(/Portefeuille/i);
    expect(
      screen.queryByTestId("account-mode-hint-mismatch-banner"),
    ).toBeNull();
  });

  it("renders the order_session_live_account banner when the event is open", async () => {
    // V1.2 §BZ vervolg: de worker schrijft een
    // ``order_session_live_account`` SystemEvent wanneer de
    // order-sessie tegen een live account verbindt. Dat moet ook
    // bovenaan /portefeuille verschijnen, niet alleen op
    // /systeemmeldingen.
    mockAllOk();
    fns.getActiveSystemEvents = vi.fn().mockReturnValue(
      ok({
        events: [
          {
            system_event_id: "evt-1",
            severity: "warning",
            category: "runtime_event",
            source_service: "worker",
            source_component: "ibkr_order_adapter",
            event_code: "order_session_live_account",
            title_nl: "Order-sessie verbonden met LIVE account",
            message_nl:
              "De order-sessie is verbonden met live-account U7654321.",
            help_nl: "",
            created_at: "2026-06-15T08:00:00+00:00",
            blocks_suggestions: false,
            blocks_writes: false,
            blocks_ai_explanation: false,
            status: "open",
          },
        ],
      }),
    );
    render(<PortfolioPage />);
    const banner = await screen.findByTestId(
      "ibkr-config-event-banner-order_session_live_account",
    );
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.getAttribute("data-event-code")).toBe(
      "order_session_live_account",
    );
    expect(banner.textContent).toContain("LIVE");
    expect(banner.textContent).toContain("U7654321");
  });

  it("renders the account_id_mismatch event banner when open", async () => {
    mockAllOk();
    fns.getActiveSystemEvents = vi.fn().mockReturnValue(
      ok({
        events: [
          {
            system_event_id: "evt-2",
            severity: "warning",
            category: "ibkr_config_mismatch",
            source_service: "api",
            source_component: "ibkr_sync",
            event_code: "account_id_mismatch",
            title_nl: "IBKR account-mismatch gedetecteerd",
            message_nl:
              "Hint DU1234567 verschilt van actueel U7654321.",
            help_nl: "",
            created_at: "2026-06-15T09:00:00+00:00",
            blocks_suggestions: false,
            blocks_writes: false,
            blocks_ai_explanation: false,
            status: "open",
          },
        ],
      }),
    );
    render(<PortfolioPage />);
    const banner = await screen.findByTestId(
      "ibkr-config-event-banner-account_id_mismatch",
    );
    expect(banner.textContent).toContain("mismatch");
    expect(banner.textContent).toContain("DU1234567");
  });

  it("filters out resolved events from the banner", async () => {
    mockAllOk();
    fns.getActiveSystemEvents = vi.fn().mockReturnValue(
      ok({
        events: [
          {
            system_event_id: "evt-1",
            severity: "warning",
            category: "runtime_event",
            source_service: "worker",
            source_component: "ibkr_order_adapter",
            event_code: "order_session_live_account",
            title_nl: "Order-sessie verbonden met LIVE account",
            message_nl: "details",
            help_nl: "",
            created_at: "2026-06-15T08:00:00+00:00",
            blocks_suggestions: false,
            blocks_writes: false,
            blocks_ai_explanation: false,
            // Closed → moet NIET zichtbaar zijn.
            status: "resolved",
          },
        ],
      }),
    );
    render(<PortfolioPage />);
    await screen.findByText(/Portefeuille/i);
    expect(
      screen.queryByTestId(
        "ibkr-config-event-banner-order_session_live_account",
      ),
    ).toBeNull();
  });

  it("dismiss flow opens reason form and confirms with reason_nl payload", async () => {
    // V1.2 §BZ vervolg: operator klikt "Begrepen" → reason-form
    // verschijnt → typt context → "Bevestig" → resolveSystemEvent
    // krijgt ``{ reason_nl: ... }`` payload zodat de audit-trail
    // operator-context heeft.
    const { default: userEvent } = await import("@testing-library/user-event");
    mockAllOk();
    fns.getActiveSystemEvents.mockReturnValue(
      ok({
        events: [
          {
            system_event_id: "evt-dismiss-1",
            severity: "warning",
            category: "ibkr_config_mismatch",
            source_service: "api",
            source_component: "ibkr_sync",
            event_code: "account_id_mismatch",
            title_nl: "IBKR account-mismatch",
            message_nl: "details",
            help_nl: "",
            created_at: "2026-06-15T09:00:00+00:00",
            blocks_suggestions: false,
            blocks_writes: false,
            blocks_ai_explanation: false,
            status: "open",
          },
        ],
      }),
    );
    fns.resolveSystemEvent.mockResolvedValue(ok({ success: true }));
    render(<PortfolioPage />);
    const dismissBtn = await screen.findByTestId(
      "ibkr-config-event-banner-dismiss-account_id_mismatch",
    );
    await userEvent.click(dismissBtn);
    // Reason form verschijnt.
    const reasonInput = await screen.findByTestId(
      "ibkr-config-event-banner-reason-input-account_id_mismatch",
    );
    await userEvent.type(reasonInput, "live is intentional");
    await userEvent.click(
      screen.getByTestId(
        "ibkr-config-event-banner-reason-confirm-account_id_mismatch",
      ),
    );
    expect(fns.resolveSystemEvent).toHaveBeenCalledWith(
      "evt-dismiss-1",
      { reason_nl: "live is intentional" },
    );
  });

  it("dismiss flow without typed reason sends no reason_nl payload", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    mockAllOk();
    fns.getActiveSystemEvents.mockReturnValue(
      ok({
        events: [
          {
            system_event_id: "evt-dismiss-2",
            severity: "warning",
            category: "ibkr_config_mismatch",
            source_service: "api",
            source_component: "ibkr_sync",
            event_code: "account_id_mismatch",
            title_nl: "title",
            message_nl: "msg",
            help_nl: "",
            created_at: "2026-06-15T09:00:00+00:00",
            blocks_suggestions: false,
            blocks_writes: false,
            blocks_ai_explanation: false,
            status: "open",
          },
        ],
      }),
    );
    fns.resolveSystemEvent.mockResolvedValue(ok({ success: true }));
    render(<PortfolioPage />);
    await userEvent.click(
      await screen.findByTestId(
        "ibkr-config-event-banner-dismiss-account_id_mismatch",
      ),
    );
    await userEvent.click(
      await screen.findByTestId(
        "ibkr-config-event-banner-reason-confirm-account_id_mismatch",
      ),
    );
    // Empty reason → no payload (undefined) zodat de API geen
    // lege-string reden persist't.
    expect(fns.resolveSystemEvent).toHaveBeenCalledWith(
      "evt-dismiss-2",
      undefined,
    );
  });

  it("PAPER/LIVE badge is een link naar /admin/audit/ibkr-config", async () => {
    // V1.2 §BZ vervolg: discoverability — operator klikt de badge
    // om snel naar het volledige audit-log te gaan zonder URL te
    // typen of via /belasting te navigeren.
    mockAllOk();
    fns.getIbkrAccountMode.mockReturnValue(
      ok({
        status: "ok",
        mode: "live",
        display_label: "LIVE",
        expected_environment: "live",
        help_nl: "x",
        safe_for_orders: false,
        blocks_orders: true,
      }),
    );
    render(<PortfolioPage />);
    const pill = await screen.findByTestId("account-mode-pill-link");
    expect(pill.getAttribute("href")).toBe("/admin/audit/ibkr-config");
    expect(pill.textContent).toContain("LIVE");
  });
});
