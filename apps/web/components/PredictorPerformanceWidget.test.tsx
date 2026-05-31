import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
} from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { PredictorPerformanceResponse } from "@/lib/apiClient";

const getPredictorPerformance = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getPredictorPerformance: (...a: unknown[]) =>
      getPredictorPerformance(...a),
  },
}));

import { PredictorPerformanceWidget } from "./PredictorPerformanceWidget";

function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function ok(data: PredictorPerformanceResponse) {
  return Promise.resolve({ ok: true as const, data });
}

function fail() {
  return Promise.resolve({ ok: false as const, reason: "not_reachable" });
}

beforeEach(() => getPredictorPerformance.mockReset());
afterEach(() => cleanup());

describe("PredictorPerformanceWidget", () => {
  it("renders the table with one row per predictor + the best chip", async () => {
    getPredictorPerformance.mockReturnValue(
      ok({
        status: "ok",
        status_nl: "x",
        help_nl: "x",
        lookback_days: 30,
        total_contributions_considered: 3,
        best_model_code: "GBM",
        safe_for_orders: false,
        safe_for_action_drafts: false,
        predictors: [
          {
            model_code: "GBM",
            model_version: "v1",
            sample_count: 2,
            realised_sample_count: 2,
            mean_brier_score: "0.2100",
            mean_return_spread_pct: "0.9000",
            mean_realised_return_pct: "2.7500",
          },
          {
            model_code: "Momentum",
            model_version: "v1",
            sample_count: 1,
            realised_sample_count: 1,
            mean_brier_score: "0.3000",
            mean_return_spread_pct: "0.5000",
            mean_realised_return_pct: "1.0000",
          },
        ],
      }),
    );
    render(<PredictorPerformanceWidget />);
    expect(
      await screen.findByTestId("predictor-performance-table"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("predictor-performance-row-GBM"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("predictor-performance-row-Momentum"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("predictor-performance-best").textContent).toBe(
      "Best: GBM",
    );
  });

  it("renders the empty-state when no predictors are returned", async () => {
    getPredictorPerformance.mockReturnValue(
      ok({
        status: "no_data",
        status_nl: "x",
        help_nl: "x",
        lookback_days: 30,
        total_contributions_considered: 0,
        best_model_code: null,
        safe_for_orders: false,
        safe_for_action_drafts: false,
        predictors: [],
      }),
    );
    render(<PredictorPerformanceWidget />);
    expect(
      await screen.findByTestId("predictor-performance-empty"),
    ).toBeInTheDocument();
  });

  it("renders an em-dash for predictors without a Brier score yet", async () => {
    getPredictorPerformance.mockReturnValue(
      ok({
        status: "ok",
        status_nl: "x",
        help_nl: "x",
        lookback_days: 30,
        total_contributions_considered: 1,
        best_model_code: "NewPredictor",
        safe_for_orders: false,
        safe_for_action_drafts: false,
        predictors: [
          {
            model_code: "NewPredictor",
            model_version: "v1",
            sample_count: 1,
            realised_sample_count: 0,
            mean_brier_score: null,
            mean_return_spread_pct: null,
            mean_realised_return_pct: null,
          },
        ],
      }),
    );
    render(<PredictorPerformanceWidget />);
    const row = await screen.findByTestId(
      "predictor-performance-row-NewPredictor",
    );
    expect(row.textContent).toContain("—");
  });

  it("renders the error line when the API is unreachable", async () => {
    getPredictorPerformance.mockReturnValue(fail());
    render(<PredictorPerformanceWidget />);
    expect(
      await screen.findByTestId("predictor-performance-error"),
    ).toBeInTheDocument();
  });
});
