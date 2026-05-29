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

import type {
  ManualReviewResponse,
  ReconciliationStatusResponse,
  UnmatchedExecutionRow,
} from "@/lib/apiClient";

const getReconciliationStatus = vi.fn();
const getReconciliationManualReview = vi.fn();
const getReconciliationUnmatchedExecutions = vi.fn();
const getReconciliationRuns = vi.fn();
const acknowledgeManualReview = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getReconciliationStatus: (...a: unknown[]) => getReconciliationStatus(...a),
    getReconciliationManualReview: (...a: unknown[]) =>
      getReconciliationManualReview(...a),
    getReconciliationUnmatchedExecutions: (...a: unknown[]) =>
      getReconciliationUnmatchedExecutions(...a),
    getReconciliationRuns: (...a: unknown[]) => getReconciliationRuns(...a),
    acknowledgeManualReview: (...a: unknown[]) => acknowledgeManualReview(...a),
  },
}));

import Page from "./page";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const STATUS = {
  ibkr_account_id: "DU1234567",
  latest_run: {
    id: 1,
    reconciliation_run_id: "run-1",
    started_at: "2026-05-27T11:50:00+00:00",
    mode_detected: "completed",
    pass_a_orphaned_count: 1,
    pass_b_stale_count: 0,
    pass_c_timeout_count: 2,
    divergences_found: 3,
  },
  drafts_healed_last_24h: 1,
  pending_manual_review_count: 1,
  unresolved_unmatched_count: 0,
} as unknown as ReconciliationStatusResponse;

const REVIEW_ROW = {
  id: 5,
  action_draft_id: "draft-9",
  reason: "timeout_24h_no_data",
  flagged_at: "2026-05-27T11:00:00+00:00",
  details_dutch: "Wacht op IBKR-data.",
} as unknown as ManualReviewResponse;

const UNMATCHED: UnmatchedExecutionRow[] = [];

function ok<T>(data: T) {
  return Promise.resolve({ ok: true as const, data });
}
function fail() {
  return Promise.resolve({ ok: false as const, reason: "not_reachable" });
}

function mockAllOk() {
  getReconciliationStatus.mockReturnValue(ok(STATUS));
  getReconciliationManualReview.mockReturnValue(ok({ rows: [REVIEW_ROW] }));
  getReconciliationUnmatchedExecutions.mockReturnValue(ok({ rows: UNMATCHED }));
  getReconciliationRuns.mockReturnValue(ok({ runs: [] }));
}

beforeEach(() => {
  getReconciliationStatus.mockReset();
  getReconciliationManualReview.mockReset();
  getReconciliationUnmatchedExecutions.mockReset();
  getReconciliationRuns.mockReset();
  acknowledgeManualReview.mockReset();
});
afterEach(() => cleanup());

describe("Reconciliation admin page", () => {
  it("renders the status summary once loaded", async () => {
    mockAllOk();
    render(<Page />);
    expect(
      await screen.findByTestId("reconciliation-status-card"),
    ).toBeInTheDocument();
    expect(screen.getByText("Account: DU1234567")).toBeInTheDocument();
    expect(screen.getByText("Voltooid")).toBeInTheDocument();
  });

  it("shows the error state when status is unavailable", async () => {
    getReconciliationStatus.mockReturnValue(fail());
    getReconciliationManualReview.mockReturnValue(ok({ rows: [] }));
    getReconciliationUnmatchedExecutions.mockReturnValue(ok({ rows: [] }));
    getReconciliationRuns.mockReturnValue(ok({ runs: [] }));
    render(<Page />);
    expect(
      await screen.findByTestId("reconciliation-page-error"),
    ).toBeInTheDocument();
  });

  it("acknowledges a manual-review row and reloads", async () => {
    mockAllOk();
    acknowledgeManualReview.mockReturnValue(ok({ ok: true }));
    const promptSpy = vi
      .spyOn(window, "prompt")
      .mockReturnValue("looks good");
    render(<Page />);
    await screen.findByTestId("reconciliation-status-card");
    await userEvent.click(
      screen.getByTestId("reconciliation-acknowledge-5"),
    );
    await waitFor(() =>
      expect(acknowledgeManualReview).toHaveBeenCalledWith(5, "looks good"),
    );
    expect(getReconciliationStatus).toHaveBeenCalledTimes(2); // initial + reload
    promptSpy.mockRestore();
  });
});
