import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ClaudeBudgetStatusResponse } from "@/lib/apiClient";

const getSchedulerV127Status = vi.fn();
const getClaudeBudgetStatus = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getSchedulerV127Status: (...a: unknown[]) =>
      getSchedulerV127Status(...a),
    getClaudeBudgetStatus: (...a: unknown[]) => getClaudeBudgetStatus(...a),
  },
}));

import { TriageStrip } from "./TriageStrip";

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

function _budget(
  overrides: Partial<ClaudeBudgetStatusResponse> = {},
): ClaudeBudgetStatusResponse {
  return {
    status: "ok",
    status_nl: "Budget-status opgehaald",
    help_nl: "x",
    monthly_cap_eur: "50",
    budget_month: "2026-06",
    monthly_total_eur: "12.40",
    remaining_eur: "37.60",
    exceeded: false,
    safe_for_action_drafts: false,
    safe_for_orders: false,
    ...overrides,
  };
}

beforeEach(() => {
  getSchedulerV127Status.mockReset();
  getClaudeBudgetStatus.mockReset();
});

afterEach(() => cleanup());

describe("TriageStrip — MorningChainBanner", () => {
  it("renders an OK level when last_outcome=succeeded", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({
        enabled: true,
        last_outcome: "succeeded",
        last_run_at: "2026-06-03T04:30:00+00:00",
        next_runs: [],
      }),
    );
    getClaudeBudgetStatus.mockReturnValue(ok(_budget()));
    render(<TriageStrip />);
    const banner = await screen.findByTestId("triage-morning-chain-banner");
    await waitFor(() =>
      expect(banner.getAttribute("data-level")).toBe("ok"),
    );
    expect(banner.textContent).toContain("OK");
  });

  it("renders a FAIL level when last_outcome=error", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({ enabled: true, last_outcome: "error", next_runs: [] }),
    );
    getClaudeBudgetStatus.mockReturnValue(ok(_budget()));
    render(<TriageStrip />);
    const banner = await screen.findByTestId("triage-morning-chain-banner");
    await waitFor(() =>
      expect(banner.getAttribute("data-level")).toBe("fail"),
    );
    expect(banner.textContent).toContain("ERROR");
  });

  it("renders a WARN level when scheduler hasn't fired yet", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({ enabled: false, last_outcome: null, next_runs: [] }),
    );
    getClaudeBudgetStatus.mockReturnValue(ok(_budget()));
    render(<TriageStrip />);
    const banner = await screen.findByTestId("triage-morning-chain-banner");
    await waitFor(() =>
      expect(banner.getAttribute("data-level")).toBe("warn"),
    );
  });
});

describe("TriageStrip — NextEventCountdown", () => {
  it("renders the earliest next run as the countdown target", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({
        enabled: true,
        last_outcome: "succeeded",
        next_runs: [
          "2026-06-03T15:30:00+00:00", // later
          "2026-06-03T07:30:00+00:00", // earlier — should win
        ],
      }),
    );
    getClaudeBudgetStatus.mockReturnValue(ok(_budget()));
    render(<TriageStrip />);
    const next = await screen.findByTestId("triage-next-event");
    expect(next.getAttribute("data-next-iso")).toBe(
      "2026-06-03T07:30:00+00:00",
    );
    expect(next.textContent).toContain("Volgende");
  });

  it("renders the empty state when there are no upcoming fires", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({
        enabled: true,
        last_outcome: "succeeded",
        next_runs: [],
      }),
    );
    getClaudeBudgetStatus.mockReturnValue(ok(_budget()));
    render(<TriageStrip />);
    expect(
      await screen.findByTestId("triage-next-event-empty"),
    ).toBeInTheDocument();
  });
});

describe("TriageStrip — ClaudeBudgetPill", () => {
  it("renders OK level under 80% usage", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({ enabled: true, last_outcome: "succeeded", next_runs: [] }),
    );
    getClaudeBudgetStatus.mockReturnValue(
      ok(_budget({ monthly_total_eur: "12.40", monthly_cap_eur: "50" })),
    );
    render(<TriageStrip />);
    const pill = await screen.findByTestId("triage-budget-pill");
    await waitFor(() =>
      expect(pill.getAttribute("data-level")).toBe("ok"),
    );
    expect(pill.textContent).toMatch(/€12\.40.*€50\.00/);
  });

  it("renders WARN level at 80%+ usage", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({ enabled: true, last_outcome: "succeeded", next_runs: [] }),
    );
    getClaudeBudgetStatus.mockReturnValue(
      ok(_budget({ monthly_total_eur: "42", monthly_cap_eur: "50" })),
    );
    render(<TriageStrip />);
    const pill = await screen.findByTestId("triage-budget-pill");
    await waitFor(() =>
      expect(pill.getAttribute("data-level")).toBe("warn"),
    );
  });

  it("renders FAIL level when the cap is exceeded", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({ enabled: true, last_outcome: "succeeded", next_runs: [] }),
    );
    getClaudeBudgetStatus.mockReturnValue(
      ok(
        _budget({
          monthly_total_eur: "55",
          monthly_cap_eur: "50",
          exceeded: true,
        }),
      ),
    );
    render(<TriageStrip />);
    const pill = await screen.findByTestId("triage-budget-pill");
    await waitFor(() =>
      expect(pill.getAttribute("data-level")).toBe("fail"),
    );
  });

  it("renders the unconfigured state when status=not_configured", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({ enabled: true, last_outcome: "succeeded", next_runs: [] }),
    );
    getClaudeBudgetStatus.mockReturnValue(
      ok(
        _budget({
          status: "not_configured",
          monthly_total_eur: null,
          remaining_eur: null,
          budget_month: null,
        }),
      ),
    );
    render(<TriageStrip />);
    expect(
      await screen.findByTestId("triage-budget-unconfigured"),
    ).toBeInTheDocument();
  });

  it("falls back to loading when both queries are still in flight", async () => {
    getSchedulerV127Status.mockImplementation(
      () => new Promise(() => {}),
    );
    getClaudeBudgetStatus.mockImplementation(() => new Promise(() => {}));
    render(<TriageStrip />);
    expect(
      await screen.findByTestId("triage-budget-loading"),
    ).toBeInTheDocument();
  });

  it("stays usable when one API fails", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({ enabled: true, last_outcome: "succeeded", next_runs: [] }),
    );
    getClaudeBudgetStatus.mockReturnValue(fail());
    render(<TriageStrip />);
    // Budget falls into unconfigured/null branch; the rest of the strip
    // still renders.
    expect(
      await screen.findByTestId("triage-morning-chain-banner"),
    ).toBeInTheDocument();
  });
});
