import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ErrorLogResponse } from "@/lib/apiClient";

const getErrors = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getErrors: (...args: unknown[]) => getErrors(...args),
  },
}));

import { ErrorLogBadge } from "./ErrorLogBadge";

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function ok(data: ErrorLogResponse) {
  return Promise.resolve({ ok: true as const, data });
}

beforeEach(() => {
  getErrors.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("ErrorLogBadge", () => {
  it("shows a red badge with the open count when there are errors", async () => {
    getErrors.mockReturnValue(ok({ open_count: 3, errors: [] }));
    renderWithClient(<ErrorLogBadge />);
    const badge = await screen.findByTestId("error-log-badge");
    await waitFor(() => expect(badge.dataset.state).toBe("errors"));
    expect(screen.getByTestId("error-log-count")).toHaveTextContent("3");
    expect(badge).toHaveAttribute("href", "/errors");
  });

  it("shows a clear (grey) badge with zero when there are no errors", async () => {
    getErrors.mockReturnValue(ok({ open_count: 0, errors: [] }));
    renderWithClient(<ErrorLogBadge />);
    const badge = await screen.findByTestId("error-log-badge");
    await waitFor(() => expect(badge.dataset.state).toBe("clear"));
    expect(screen.getByTestId("error-log-count")).toHaveTextContent("0");
  });

  it("treats an unreachable API as zero (clear) rather than crashing", async () => {
    getErrors.mockReturnValue(
      Promise.resolve({ ok: false as const, status: 0, message: "x" }),
    );
    renderWithClient(<ErrorLogBadge />);
    const badge = await screen.findByTestId("error-log-badge");
    await waitFor(() => expect(badge.dataset.state).toBe("clear"));
  });
});
