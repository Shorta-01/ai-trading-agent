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
});
