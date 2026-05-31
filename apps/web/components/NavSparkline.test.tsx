import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NavHistoryResponse } from "@/lib/apiClient";

const getNavHistory = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getNavHistory: (...a: unknown[]) => getNavHistory(...a),
  },
}));

import { NavSparkline } from "./NavSparkline";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function ok(data: NavHistoryResponse) {
  return Promise.resolve({ ok: true as const, data });
}

function fail() {
  return Promise.resolve({ ok: false as const, reason: "not_reachable" });
}

function _payload(
  values: number[],
  overrides: Partial<NavHistoryResponse> = {},
): NavHistoryResponse {
  return {
    status: values.length ? "ok" : "no_points",
    status_nl: "x",
    help_nl: "x",
    ibkr_account_id: "DU1",
    base_currency: "EUR",
    days_requested: 30,
    points: values.map((v, i) => ({
      recorded_at_utc: `2026-06-${String(i + 1).padStart(2, "0")}T00:00:00+00:00`,
      nav_value: String(v),
    })),
    ...overrides,
  };
}

beforeEach(() => getNavHistory.mockReset());
afterEach(() => cleanup());

describe("NavSparkline", () => {
  it("renders the empty-state message when fewer than 2 points are returned", async () => {
    getNavHistory.mockReturnValue(ok(_payload([100000])));
    render(<NavSparkline />);
    expect(
      await screen.findByTestId("nav-sparkline-empty"),
    ).toBeInTheDocument();
  });

  it("renders the SVG sparkline and a green +change for an upward trend", async () => {
    getNavHistory.mockReturnValue(
      ok(_payload([100000, 100500, 101200, 102000])),
    );
    render(<NavSparkline />);
    expect(
      await screen.findByTestId("nav-sparkline-svg"),
    ).toBeInTheDocument();
    const widget = screen.getByTestId("nav-sparkline");
    await waitFor(() =>
      expect(widget.getAttribute("data-trend")).toBe("up"),
    );
    const change = screen.getByTestId("nav-sparkline-change");
    expect(change.textContent).toMatch(/\+2000\.00 EUR/);
    expect(change.textContent).toContain("+2.00%");
  });

  it("renders red -change for a downward trend", async () => {
    getNavHistory.mockReturnValue(
      ok(_payload([100000, 99500, 98800, 97500])),
    );
    render(<NavSparkline />);
    const widget = await screen.findByTestId("nav-sparkline");
    await waitFor(() =>
      expect(widget.getAttribute("data-trend")).toBe("down"),
    );
    const change = screen.getByTestId("nav-sparkline-change");
    expect(change.textContent).toContain("-2500.00 EUR");
    expect(change.textContent).toContain("-2.50%");
  });

  it("renders the error line when the API is unreachable", async () => {
    getNavHistory.mockReturnValue(fail());
    render(<NavSparkline />);
    expect(
      await screen.findByTestId("nav-sparkline-error"),
    ).toBeInTheDocument();
  });

  it("renders the title with the requested day count", async () => {
    getNavHistory.mockReturnValue(ok(_payload([100, 101], { days_requested: 14 })));
    render(<NavSparkline days={14} />);
    expect(await screen.findByText("NAV trend (14 d)")).toBeInTheDocument();
  });
});
