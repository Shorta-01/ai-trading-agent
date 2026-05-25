import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

import type { IbkrConnectionStatusResponse } from "@/lib/apiClient";

const getIbkrConnectionStatus = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getIbkrConnectionStatus: (...args: unknown[]) =>
      getIbkrConnectionStatus(...args),
  },
}));

import { AccountModeBadge } from "./AccountModeBadge";

function ok(data: IbkrConnectionStatusResponse) {
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
  getIbkrConnectionStatus.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
  cleanup();
});

describe("AccountModeBadge", () => {
  it("renders disconnected state when the API is unreachable", async () => {
    getIbkrConnectionStatus.mockReturnValue(notReachable());

    render(<AccountModeBadge />);

    const badge = await screen.findByTestId("account-mode-badge");
    await waitFor(() => {
      expect(badge.dataset.mode).toBe("disconnected");
    });
    expect(badge).toHaveTextContent("Geen IBKR-verbinding");
  });

  it("renders the Paper state with a masked DU account id", async () => {
    getIbkrConnectionStatus.mockReturnValue(
      ok({
        connected: true,
        account_id: "DU•••4567",
        account_mode: "paper",
        verified_at: "2026-05-25T07:00:00+00:00",
        error: null,
        safe_for_action_drafts: false,
        safe_for_orders: false,
      }),
    );

    render(<AccountModeBadge />);

    const badge = await screen.findByTestId("account-mode-badge");
    await waitFor(() => {
      expect(badge.dataset.mode).toBe("paper");
    });
    expect(badge).toHaveTextContent("Paper-rekening: DU•••4567");
  });

  it("renders the Live state with a masked U account id", async () => {
    getIbkrConnectionStatus.mockReturnValue(
      ok({
        connected: true,
        account_id: "U7•••4321",
        account_mode: "live",
        verified_at: "2026-05-25T07:00:00+00:00",
        error: null,
        safe_for_action_drafts: false,
        safe_for_orders: false,
      }),
    );

    render(<AccountModeBadge />);

    const badge = await screen.findByTestId("account-mode-badge");
    await waitFor(() => {
      expect(badge.dataset.mode).toBe("live");
    });
    expect(badge).toHaveTextContent("Echte rekening: U7•••4321");
  });

  it("flashes the first-mount colour for 500ms then settles", async () => {
    getIbkrConnectionStatus.mockReturnValue(
      ok({
        connected: true,
        account_id: "DU•••4567",
        account_mode: "paper",
        verified_at: "2026-05-25T07:00:00+00:00",
        error: null,
        safe_for_action_drafts: false,
        safe_for_orders: false,
      }),
    );

    render(<AccountModeBadge />);
    const badge = await screen.findByTestId("account-mode-badge");

    // Initial mount → flash colour #3b82f6 (full-saturation paper blue).
    const initialBg = badge.style.background;
    expect(initialBg.toLowerCase()).toContain("rgb(59, 130, 246)");

    // Advance past the flash duration → settles to neutral paper.
    await vi.advanceTimersByTimeAsync(600);
    await waitFor(() => {
      expect(badge.style.background.toLowerCase()).toContain(
        "rgb(30, 64, 175)",
      );
    });
  });

  it("polls /ibkr/connection/status on the 30-second interval", async () => {
    getIbkrConnectionStatus.mockReturnValue(notReachable());

    render(<AccountModeBadge />);
    await screen.findByTestId("account-mode-badge");

    // One call on mount.
    expect(getIbkrConnectionStatus).toHaveBeenCalledTimes(1);

    // Each interval tick fires one more call.
    await vi.advanceTimersByTimeAsync(30_000);
    expect(getIbkrConnectionStatus).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(30_000);
    expect(getIbkrConnectionStatus).toHaveBeenCalledTimes(3);
  });
});
