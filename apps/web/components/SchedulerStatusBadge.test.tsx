import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

import type { SchedulerV127StatusResponse } from "@/lib/apiClient";

const getSchedulerV127Status = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getSchedulerV127Status: (...args: unknown[]) =>
      getSchedulerV127Status(...args),
  },
}));

import { SchedulerStatusBadge } from "./SchedulerStatusBadge";

function ok(data: SchedulerV127StatusResponse) {
  return Promise.resolve({ ok: true as const, data });
}

function notReachable() {
  return Promise.resolve({
    ok: false as const,
    reason: "not_reachable" as const,
  });
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  getSchedulerV127Status.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
  cleanup();
});

describe("SchedulerStatusBadge", () => {
  it("renders Uitgeschakeld when the scheduler reports disabled", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({
        enabled: false,
        last_run_at: null,
        last_run_type: null,
        last_mode_detected: null,
        last_outcome: null,
        next_runs: [],
        safe_for_action_drafts: false,
        safe_for_orders: false,
      }),
    );

    render(<SchedulerStatusBadge />);

    const badge = await screen.findByTestId("scheduler-status-badge");
    await waitFor(() => {
      expect(badge.dataset.state).toBe("uitgeschakeld");
    });
    expect(badge).toHaveTextContent("Uitgeschakeld");
  });

  it("renders Actief with the next run time when enabled + healthy", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({
        enabled: true,
        last_run_at: "2026-05-25T07:00:00+00:00",
        last_run_type: "hourly_delta",
        last_mode_detected: "normal",
        last_outcome: "completed",
        next_runs: ["2026-05-25T13:00:00+02:00"],
        safe_for_action_drafts: false,
        safe_for_orders: false,
      }),
    );

    render(<SchedulerStatusBadge />);

    const badge = await screen.findByTestId("scheduler-status-badge");
    await waitFor(() => {
      expect(badge.dataset.state).toBe("actief");
    });
    expect(badge).toHaveTextContent("Actief");
    expect(badge).toHaveTextContent("volgende run");
  });

  it("renders Fout when the last run errored", async () => {
    getSchedulerV127Status.mockReturnValue(
      ok({
        enabled: true,
        last_run_at: "2026-05-25T07:00:00+00:00",
        last_run_type: "hourly_delta",
        last_mode_detected: "disconnected",
        last_outcome: "error",
        next_runs: ["2026-05-25T08:00:00+02:00"],
        safe_for_action_drafts: false,
        safe_for_orders: false,
      }),
    );

    render(<SchedulerStatusBadge />);

    const badge = await screen.findByTestId("scheduler-status-badge");
    await waitFor(() => {
      expect(badge.dataset.state).toBe("fout");
    });
    expect(badge).toHaveTextContent("Fout");
  });

  it("renders Fout when the API itself is unreachable", async () => {
    getSchedulerV127Status.mockReturnValue(notReachable());

    render(<SchedulerStatusBadge />);

    const badge = await screen.findByTestId("scheduler-status-badge");
    await waitFor(() => {
      expect(badge.dataset.state).toBe("fout");
    });
  });

  it("polls /scheduler/v127/status on the 60-second interval", async () => {
    getSchedulerV127Status.mockReturnValue(notReachable());

    render(<SchedulerStatusBadge />);
    await screen.findByTestId("scheduler-status-badge");

    expect(getSchedulerV127Status).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(60_000);
    expect(getSchedulerV127Status).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(60_000);
    expect(getSchedulerV127Status).toHaveBeenCalledTimes(3);
  });
});
