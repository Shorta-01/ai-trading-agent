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

const getApiHealth = vi.fn();
const getStorageStatusOnline = vi.fn();
const getSchedulerV127Status = vi.fn();
const getIbkrSyncStatus = vi.fn();
const getActiveSystemEvents = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getApiHealth: (...a: unknown[]) => getApiHealth(...a),
    getStorageStatusOnline: (...a: unknown[]) => getStorageStatusOnline(...a),
    getSchedulerV127Status: (...a: unknown[]) => getSchedulerV127Status(...a),
    getIbkrSyncStatus: (...a: unknown[]) => getIbkrSyncStatus(...a),
    getActiveSystemEvents: (...a: unknown[]) => getActiveSystemEvents(...a),
  },
}));

import { SystemMonitorWidget } from "./SystemMonitorWidget";

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

function fail(reason = "not_reachable") {
  return Promise.resolve({ ok: false as const, reason });
}

function _allGreen() {
  getApiHealth.mockReturnValue(ok({ status: "ok", service: "api" }));
  getStorageStatusOnline.mockReturnValue(
    ok({
      configured: true,
      connected: true,
      safe_to_write: true,
      migration_readiness_status: "migrations_current",
      writes_status_nl: "Opslag schrijfbaar.",
    }),
  );
  getSchedulerV127Status.mockReturnValue(
    ok({
      enabled: true,
      last_outcome: "success",
      next_runs: ["2026-06-01T06:00:00Z"],
    }),
  );
  getIbkrSyncStatus.mockReturnValue(
    ok({
      configured: true,
      status_nl: "IBKR sync OK.",
      help_nl: "IBKR sync OK.",
      positions_count: 5,
      cash_available: true,
      open_orders_count: 0,
      executions_count: 0,
      actions_allowed: true,
    }),
  );
  getActiveSystemEvents.mockReturnValue(ok({ events: [] }));
}

beforeEach(() => {
  getApiHealth.mockReset();
  getStorageStatusOnline.mockReset();
  getSchedulerV127Status.mockReset();
  getIbkrSyncStatus.mockReset();
  getActiveSystemEvents.mockReset();
});

afterEach(() => cleanup());

describe("SystemMonitorWidget", () => {
  it("renders the collapsed pill with a green overall dot when everything is green", async () => {
    _allGreen();
    render(<SystemMonitorWidget />);
    const widget = await screen.findByTestId("system-monitor-widget");
    await waitFor(() =>
      expect(widget.getAttribute("data-overall-level")).toBe("ok"),
    );
    expect(screen.getByText("Systeemmonitor")).toBeInTheDocument();
    expect(screen.getByTestId("system-monitor-dot-row")).toBeInTheDocument();
  });

  it("expands to show per-check detail when clicked", async () => {
    _allGreen();
    render(<SystemMonitorWidget />);
    await screen.findByText("Systeemmonitor");
    await userEvent.click(screen.getByTestId("system-monitor-widget"));
    expect(
      await screen.findByTestId("system-monitor-detail-list"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("system-monitor-check-api")).toBeInTheDocument();
    expect(
      screen.getByTestId("system-monitor-check-storage"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("system-monitor-check-scheduler"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("system-monitor-check-ibkr"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("system-monitor-check-events"),
    ).toBeInTheDocument();
  });

  it("escalates to fail when storage is connected but not writable", async () => {
    _allGreen();
    getStorageStatusOnline.mockReturnValue(
      ok({
        configured: true,
        connected: true,
        safe_to_write: false,
        migration_readiness_status: "migrations_behind",
        writes_status_nl: "Migraties achter.",
      }),
    );
    render(<SystemMonitorWidget />);
    const widget = await screen.findByTestId("system-monitor-widget");
    await waitFor(() =>
      expect(widget.getAttribute("data-overall-level")).toBe("fail"),
    );
  });

  it("escalates to warn when IBKR is not configured", async () => {
    _allGreen();
    getIbkrSyncStatus.mockReturnValue(
      ok({
        configured: false,
        status_nl: "IBKR niet geconfigureerd.",
        help_nl: "IBKR niet geconfigureerd.",
        positions_count: 0,
        cash_available: false,
        open_orders_count: 0,
        executions_count: 0,
      }),
    );
    render(<SystemMonitorWidget />);
    const widget = await screen.findByTestId("system-monitor-widget");
    await waitFor(() =>
      expect(widget.getAttribute("data-overall-level")).toBe("warn"),
    );
  });

  it("escalates to fail when a blocking system event is active", async () => {
    _allGreen();
    getActiveSystemEvents.mockReturnValue(
      ok({
        events: [
          {
            system_event_id: "evt-1",
            blocks_writes: true,
            blocks_suggestions: false,
            blocks_ai_explanation: false,
            title_nl: "Storage writes blocked",
          },
        ],
      }),
    );
    render(<SystemMonitorWidget />);
    const widget = await screen.findByTestId("system-monitor-widget");
    await waitFor(() =>
      expect(widget.getAttribute("data-overall-level")).toBe("fail"),
    );
    await userEvent.click(widget);
    const eventsCheck = await screen.findByTestId(
      "system-monitor-check-events",
    );
    expect(eventsCheck.textContent).toContain("blokkerend");
  });

  it("stays usable when the API itself is unreachable", async () => {
    getApiHealth.mockReturnValue(fail());
    getStorageStatusOnline.mockReturnValue(fail());
    getSchedulerV127Status.mockReturnValue(fail());
    getIbkrSyncStatus.mockReturnValue(fail());
    getActiveSystemEvents.mockReturnValue(fail());
    render(<SystemMonitorWidget />);
    // The widget renders the label even when every check returns
    // null — the operator still sees the corner box and can click it.
    expect(await screen.findByText("Systeemmonitor")).toBeInTheDocument();
  });

  it("is keyboard-accessible: Enter toggles expansion", async () => {
    _allGreen();
    render(<SystemMonitorWidget />);
    const widget = await screen.findByTestId("system-monitor-widget");
    widget.focus();
    await userEvent.keyboard("{Enter}");
    expect(
      await screen.findByTestId("system-monitor-detail-list"),
    ).toBeInTheDocument();
  });
});
