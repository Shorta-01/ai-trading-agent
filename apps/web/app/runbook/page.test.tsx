import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";

import type {
  RunbookItemResponse,
  RunbookResponse,
} from "@/lib/apiClient";

const getRunbook = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getRunbook: (...a: unknown[]) => getRunbook(...a),
  },
}));

import RunbookPage from "./page";

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

function makeItem(
  overrides: Partial<RunbookItemResponse> = {},
): RunbookItemResponse {
  return {
    code: "ibkr_account_mode",
    group: "doctrine_locks",
    label_nl: "IBKR account-mode",
    status: "info",
    value_nl: "Paper-account: DU1234567",
    what_it_means_nl: "CLAUDE.md §15 — account-id prefix bepaalt mode.",
    ...overrides,
  };
}

function makeRunbook(overrides: Partial<RunbookResponse> = {}): RunbookResponse {
  return {
    title_nl: "Go-live runbook",
    help_nl: "Operator checklist.",
    ready_for_paper_go_live: true,
    summary_nl: "Alle items in orde.",
    items: [makeItem()],
    ...overrides,
  };
}

beforeEach(() => {
  getRunbook.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("RunbookPage", () => {
  it("toont loading initieel", () => {
    getRunbook.mockImplementation(() => new Promise<never>(() => {}));
    render(<RunbookPage />);
    expect(screen.getByTestId("runbook-loading")).toBeTruthy();
  });

  it("toont error wanneer fetch faalt", async () => {
    getRunbook.mockResolvedValue({ ok: false, reason: "not_reachable" });
    render(<RunbookPage />);
    await waitFor(() => {
      expect(screen.getByTestId("runbook-error")).toBeTruthy();
    });
  });

  it("toont 'Klaar voor paper-go-live' badge wanneer ready=true", async () => {
    getRunbook.mockResolvedValue({
      ok: true,
      data: makeRunbook({ ready_for_paper_go_live: true }),
    });
    render(<RunbookPage />);
    await waitFor(() => {
      expect(screen.getByTestId("runbook-summary-badge").textContent).toMatch(
        /klaar/i,
      );
    });
    expect(
      screen.getByTestId("runbook-summary").getAttribute("data-ready"),
    ).toBe("true");
  });

  it("toont 'Nog niet klaar' wanneer ready=false", async () => {
    getRunbook.mockResolvedValue({
      ok: true,
      data: makeRunbook({
        ready_for_paper_go_live: false,
        summary_nl: "Paper-only modus is blocking.",
      }),
    });
    render(<RunbookPage />);
    await waitFor(() => {
      expect(screen.getByTestId("runbook-summary-badge").textContent).toMatch(
        /nog niet/i,
      );
    });
    expect(screen.getByTestId("runbook-summary-text").textContent).toMatch(
      /blocking/i,
    );
  });

  it("groepeert items per group", async () => {
    getRunbook.mockResolvedValue({
      ok: true,
      data: makeRunbook({
        items: [
          makeItem({ code: "ibkr_account_mode", group: "doctrine_locks" }),
          makeItem({
            code: "storage_writable",
            group: "provider_config",
            label_nl: "Opslag schrijfbaar",
            status: "ok",
          }),
          makeItem({
            code: "earnings_calendar_sync_enabled",
            group: "doctrine_features",
            label_nl: "Earnings",
            status: "warning",
          }),
        ],
      }),
    });
    render(<RunbookPage />);
    await waitFor(() => {
      expect(screen.getByTestId("runbook-group-doctrine_locks")).toBeTruthy();
    });
    expect(screen.getByTestId("runbook-group-provider_config")).toBeTruthy();
    expect(screen.getByTestId("runbook-group-doctrine_features")).toBeTruthy();
  });

  it("rendert status-badges met de juiste tekst", async () => {
    getRunbook.mockResolvedValue({
      ok: true,
      data: makeRunbook({
        items: [
          makeItem({ code: "x1", status: "ok" }),
          makeItem({ code: "x2", status: "blocking", group: "doctrine_locks" }),
          makeItem({ code: "x3", status: "warning", group: "provider_config" }),
          makeItem({ code: "x4", status: "info", group: "provider_config" }),
        ],
      }),
    });
    render(<RunbookPage />);
    await waitFor(() => {
      expect(screen.getByTestId("runbook-item-status-x1").textContent).toBe(
        "OK",
      );
    });
    expect(screen.getByTestId("runbook-item-status-x2").textContent).toBe(
      "BLOCKING",
    );
    expect(screen.getByTestId("runbook-item-status-x3").textContent).toBe(
      "WARNING",
    );
    expect(screen.getByTestId("runbook-item-status-x4").textContent).toBe(
      "INFO",
    );
  });
});
