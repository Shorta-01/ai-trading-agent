import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

import type { ReconciliationStatusResponse } from "@/lib/apiClient";

const getReconciliationStatus = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getReconciliationStatus: (...args: unknown[]) =>
      getReconciliationStatus(...args),
  },
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

import { ReconciliationStatusWidget } from "./ReconciliationStatusWidget";

const COMPLETED: ReconciliationStatusResponse = {
  ibkr_account_id: "DU1234567",
  latest_run: {
    id: 1,
    reconciliation_run_id: "run-1",
    started_at: "2026-05-27T11:50:00+00:00",
    completed_at: "2026-05-27T11:50:30+00:00",
    account_id: "DU1234567",
    pass_a_orphaned_count: 1,
    pass_b_stale_count: 0,
    pass_c_timeout_count: 2,
    divergences_found: 3,
    mode_detected: "completed",
    error_details_json: null,
  },
  drafts_healed_last_24h: 1,
  pending_manual_review_count: 2,
  unresolved_unmatched_count: 0,
};

const NO_RUN: ReconciliationStatusResponse = {
  ibkr_account_id: "DU1234567",
  latest_run: null,
  drafts_healed_last_24h: 0,
  pending_manual_review_count: 0,
  unresolved_unmatched_count: 0,
};

beforeEach(() => {
  getReconciliationStatus.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("ReconciliationStatusWidget", () => {
  it("renders the mode badge and per-metric counts on a completed run", async () => {
    getReconciliationStatus.mockResolvedValue({
      ok: true as const,
      data: COMPLETED,
    });
    render(<ReconciliationStatusWidget />);

    const badge = await screen.findByTestId("reconciliation-mode-badge");
    expect(badge).toHaveTextContent("Voltooid");

    expect(screen.getByTestId("reconciliation-healed-24h-value"))
      .toHaveTextContent("1");
    expect(screen.getByTestId("reconciliation-pending-review-value"))
      .toHaveTextContent("2");
    expect(screen.getByTestId("reconciliation-unmatched-value"))
      .toHaveTextContent("0");
  });

  it("renders the no-runs hint when latest_run is null", async () => {
    getReconciliationStatus.mockResolvedValue({
      ok: true as const,
      data: NO_RUN,
    });
    render(<ReconciliationStatusWidget />);

    const hint = await screen.findByTestId("reconciliation-no-runs");
    expect(hint).toHaveTextContent("Nog geen runs");
  });

  it("renders nothing on API failure", async () => {
    getReconciliationStatus.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    const { container } = render(<ReconciliationStatusWidget />);
    await waitFor(() => {
      expect(getReconciliationStatus).toHaveBeenCalledTimes(1);
    });
    expect(
      container.querySelector(
        '[data-testid="reconciliation-status-widget"]',
      ),
    ).toBeNull();
  });

  it("links to /admin/reconciliation", async () => {
    getReconciliationStatus.mockResolvedValue({
      ok: true as const,
      data: COMPLETED,
    });
    render(<ReconciliationStatusWidget />);
    const link = await screen.findByTestId("reconciliation-status-widget");
    expect(link.getAttribute("href")).toBe("/admin/reconciliation");
  });
});
