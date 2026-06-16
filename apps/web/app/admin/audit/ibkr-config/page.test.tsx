import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getIbkrConfigAudit: vi.fn(),
  },
}));

import { apiClient } from "@/lib/apiClient";
import Page from "./page";

const getIbkrConfigAudit = apiClient.getIbkrConfigAudit as ReturnType<typeof vi.fn>;

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function ok<T>(data: T) {
  return { ok: true as const, data };
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("IBKR-config audit-trail page", () => {
  it("renders a row per event with status, severity and message", async () => {
    getIbkrConfigAudit.mockReturnValue(
      ok({
        available: true,
        storage_configured: true,
        events_loaded: true,
        active_count: 2,
        status_nl: "Beschikbaar",
        message_nl: "2 events",
        events: [
          {
            system_event_id: "evt-1",
            severity: "warning",
            category: "ibkr_config_mismatch",
            source_service: "api",
            source_component: "ibkr_sync",
            event_code: "account_id_mismatch",
            title_nl: "Mismatch",
            message_nl: "DU1234567 vs U7654321",
            help_nl: "",
            created_at: "2026-06-15T08:00:00+00:00",
            blocks_suggestions: false,
            blocks_writes: false,
            blocks_ai_explanation: false,
            status: "resolved",
          },
          {
            system_event_id: "evt-2",
            severity: "info",
            category: "ibkr_config_change",
            source_service: "api",
            source_component: "runtime_config_routes",
            event_code: "ibkr_account_id_changed",
            title_nl: "Account-id gewijzigd",
            message_nl: "DU1111111 -> DU2222222",
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
    render(<Page />);
    await screen.findByTestId("admin-ibkr-config-audit-table");
    expect(screen.getByTestId("audit-event-row-evt-1")).toBeInTheDocument();
    expect(screen.getByTestId("audit-event-row-evt-2")).toBeInTheDocument();
    expect(screen.getByText("DU1234567 vs U7654321")).toBeInTheDocument();
    expect(
      screen.getByText(/DU1111111 -> DU2222222/),
    ).toBeInTheDocument();
    expect(screen.getByTestId("admin-ibkr-config-audit-count")).toHaveTextContent(
      "2 events gevonden",
    );
  });

  it("renders empty-state message when no events exist", async () => {
    getIbkrConfigAudit.mockReturnValue(
      ok({
        available: true,
        storage_configured: true,
        events_loaded: true,
        active_count: 0,
        status_nl: "Beschikbaar",
        message_nl: "0 events",
        events: [],
      }),
    );
    render(<Page />);
    expect(
      await screen.findByTestId("admin-ibkr-config-audit-empty"),
    ).toBeInTheDocument();
  });

  it("renders error fallback when fetch fails", async () => {
    getIbkrConfigAudit.mockResolvedValue({ ok: false, reason: "boom" });
    render(<Page />);
    expect(
      await screen.findByTestId("admin-ibkr-config-audit-error"),
    ).toBeInTheDocument();
  });

  it("filters by event_code via the dropdown", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    getIbkrConfigAudit.mockReturnValue(
      ok({
        available: true,
        storage_configured: true,
        events_loaded: true,
        active_count: 2,
        status_nl: "Beschikbaar",
        message_nl: "2 events",
        events: [
          {
            system_event_id: "evt-mismatch",
            severity: "warning",
            category: "ibkr_config_mismatch",
            source_service: "api",
            source_component: "ibkr_sync",
            event_code: "account_id_mismatch",
            title_nl: "Mismatch",
            message_nl: "msg-1",
            help_nl: "",
            created_at: "2026-03-12T10:00:00+00:00",
            blocks_suggestions: false,
            blocks_writes: false,
            blocks_ai_explanation: false,
            status: "resolved",
          },
          {
            system_event_id: "evt-changed",
            severity: "info",
            category: "ibkr_config_change",
            source_service: "api",
            source_component: "runtime_config_routes",
            event_code: "ibkr_account_id_changed",
            title_nl: "Wijziging",
            message_nl: "msg-2",
            help_nl: "",
            created_at: "2026-05-01T09:00:00+00:00",
            blocks_suggestions: false,
            blocks_writes: false,
            blocks_ai_explanation: false,
            status: "open",
          },
        ],
      }),
    );
    render(<Page />);
    await screen.findByTestId("admin-ibkr-config-audit-table");

    // Beide rijen zichtbaar zonder filter.
    expect(
      screen.getByTestId("audit-event-row-evt-mismatch"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("audit-event-row-evt-changed"),
    ).toBeInTheDocument();

    // Filter op event_code = account_id_mismatch.
    await userEvent.selectOptions(
      screen.getByTestId("admin-ibkr-config-audit-filter-event-code"),
      "account_id_mismatch",
    );
    expect(
      screen.getByTestId("audit-event-row-evt-mismatch"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("audit-event-row-evt-changed"),
    ).toBeNull();
    // Filter-count strookje rapporteert het verschil.
    expect(
      screen.getByTestId("admin-ibkr-config-audit-filter-count").textContent,
    ).toContain("1 na filter");
  });

  it("filters by status and resets via the Reset button", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    getIbkrConfigAudit.mockReturnValue(
      ok({
        available: true,
        storage_configured: true,
        events_loaded: true,
        active_count: 2,
        status_nl: "Beschikbaar",
        message_nl: "2 events",
        events: [
          {
            system_event_id: "evt-1",
            severity: "warning",
            category: "ibkr_config_mismatch",
            source_service: "api",
            source_component: "ibkr_sync",
            event_code: "account_id_mismatch",
            title_nl: "M",
            message_nl: "1",
            help_nl: "",
            created_at: "2026-03-12T10:00:00+00:00",
            blocks_suggestions: false,
            blocks_writes: false,
            blocks_ai_explanation: false,
            status: "open",
          },
          {
            system_event_id: "evt-2",
            severity: "info",
            category: "ibkr_config_change",
            source_service: "api",
            source_component: "runtime_config_routes",
            event_code: "ibkr_account_id_changed",
            title_nl: "C",
            message_nl: "2",
            help_nl: "",
            created_at: "2026-05-01T09:00:00+00:00",
            blocks_suggestions: false,
            blocks_writes: false,
            blocks_ai_explanation: false,
            status: "resolved",
          },
        ],
      }),
    );
    render(<Page />);
    await screen.findByTestId("admin-ibkr-config-audit-table");
    await userEvent.selectOptions(
      screen.getByTestId("admin-ibkr-config-audit-filter-status"),
      "open",
    );
    expect(screen.getByTestId("audit-event-row-evt-1")).toBeInTheDocument();
    expect(screen.queryByTestId("audit-event-row-evt-2")).toBeNull();

    // Reset button verschijnt en herstelt.
    await userEvent.click(
      screen.getByTestId("admin-ibkr-config-audit-filter-reset"),
    );
    expect(screen.getByTestId("audit-event-row-evt-1")).toBeInTheDocument();
    expect(screen.getByTestId("audit-event-row-evt-2")).toBeInTheDocument();
  });

  it("renders the no-match message when filters exclude every row", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    getIbkrConfigAudit.mockReturnValue(
      ok({
        available: true,
        storage_configured: true,
        events_loaded: true,
        active_count: 1,
        status_nl: "Beschikbaar",
        message_nl: "1 event",
        events: [
          {
            system_event_id: "evt-1",
            severity: "warning",
            category: "ibkr_config_mismatch",
            source_service: "api",
            source_component: "ibkr_sync",
            event_code: "account_id_mismatch",
            title_nl: "M",
            message_nl: "msg",
            help_nl: "",
            created_at: "2026-03-12T10:00:00+00:00",
            blocks_suggestions: false,
            blocks_writes: false,
            blocks_ai_explanation: false,
            status: "open",
          },
        ],
      }),
    );
    render(<Page />);
    await screen.findByTestId("admin-ibkr-config-audit-table");
    await userEvent.selectOptions(
      screen.getByTestId("admin-ibkr-config-audit-filter-status"),
      "archived",
    );
    expect(
      screen.getByTestId("admin-ibkr-config-audit-filter-empty"),
    ).toBeInTheDocument();
  });

  it("Export CSV button is disabled when no events match the filter", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    getIbkrConfigAudit.mockReturnValue(
      ok({
        available: true,
        storage_configured: true,
        events_loaded: true,
        active_count: 1,
        status_nl: "Beschikbaar",
        message_nl: "1 event",
        events: [
          {
            system_event_id: "evt-1",
            severity: "warning",
            category: "ibkr_config_mismatch",
            source_service: "api",
            source_component: "ibkr_sync",
            event_code: "account_id_mismatch",
            title_nl: "M",
            message_nl: "msg",
            help_nl: "",
            created_at: "2026-03-12T10:00:00+00:00",
            blocks_suggestions: false,
            blocks_writes: false,
            blocks_ai_explanation: false,
            status: "open",
          },
        ],
      }),
    );
    render(<Page />);
    await screen.findByTestId("admin-ibkr-config-audit-table");
    // 1 event match → button enabled met "(1)" label.
    const button = screen.getByTestId(
      "admin-ibkr-config-audit-export-csv",
    );
    expect(button).not.toBeDisabled();
    expect(button.textContent).toContain("(1)");
    // Filter naar 0 events → button disabled met "(0)" label.
    await userEvent.selectOptions(
      screen.getByTestId("admin-ibkr-config-audit-filter-status"),
      "archived",
    );
    expect(button).toBeDisabled();
    expect(button.textContent).toContain("(0)");
  });
});

describe("buildAuditCsv", () => {
  it("builds a CSV with the required headers and one row per event", async () => {
    const { buildAuditCsv } = await import("./csv");
    const csv = buildAuditCsv([
      {
        system_event_id: "evt-1",
        severity: "warning",
        category: "ibkr_config_mismatch",
        source_service: "api",
        source_component: "ibkr_sync",
        event_code: "account_id_mismatch",
        title_nl: "Mismatch",
        message_nl: "DU1234567 vs U7654321",
        help_nl: "",
        created_at: "2026-03-12T10:00:00+00:00",
        blocks_suggestions: false,
        blocks_writes: false,
        blocks_ai_explanation: false,
        status: "resolved",
      },
    ]);
    const lines = csv.split("\n");
    expect(lines[0]).toContain("created_at_utc");
    expect(lines[0]).toContain("event_code");
    expect(lines[0]).toContain("message_nl");
    expect(lines[1]).toContain("account_id_mismatch");
    expect(lines[1]).toContain("warning");
    expect(lines[1]).toContain("resolved");
    expect(lines[1]).toContain("DU1234567 vs U7654321");
  });

  it("CSV-escapes embedded double quotes via the standard \"\"-doubling", async () => {
    const { buildAuditCsv } = await import("./csv");
    const csv = buildAuditCsv([
      {
        system_event_id: "evt-1",
        severity: "info",
        category: "ibkr_config_change",
        source_service: "api",
        source_component: "runtime_config_routes",
        event_code: "ibkr_account_id_changed",
        title_nl: 'titel met "quotes"',
        message_nl: "details",
        help_nl: "",
        created_at: "2026-05-01T09:00:00+00:00",
        blocks_suggestions: false,
        blocks_writes: false,
        blocks_ai_explanation: false,
        status: "open",
      },
    ]);
    // Embedded quotes worden verdubbeld zoals RFC 4180 vereist.
    expect(csv).toContain('titel met ""quotes""');
  });
});
