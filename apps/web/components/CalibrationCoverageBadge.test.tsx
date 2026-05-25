import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

import type { CalibrationCoverageResponse } from "@/lib/apiClient";

const getCalibrationCoverage = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getCalibrationCoverage: (...args: unknown[]) =>
      getCalibrationCoverage(...args),
  },
}));

import { CalibrationCoverageBadge } from "./CalibrationCoverageBadge";

const HEALTHY: CalibrationCoverageResponse = {
  window_days: 90,
  forecasts_evaluated: 20,
  hit_rate_within_band: "0.75",
  p10_p90_coverage_percent: "75.0",
  mean_realized_minus_p50: "0.001",
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

const WARNING_SMALL_SAMPLE: CalibrationCoverageResponse = {
  ...HEALTHY,
  forecasts_evaluated: 5,
  hit_rate_within_band: "0.80",
};

const WARNING_LOW_RATE: CalibrationCoverageResponse = {
  ...HEALTHY,
  hit_rate_within_band: "0.45",
  p10_p90_coverage_percent: "45.0",
};

const INSUFFICIENT: CalibrationCoverageResponse = {
  window_days: 90,
  forecasts_evaluated: 0,
  hit_rate_within_band: null,
  p10_p90_coverage_percent: null,
  mean_realized_minus_p50: null,
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

beforeEach(() => {
  getCalibrationCoverage.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("CalibrationCoverageBadge", () => {
  it("renders healthy state when hit-rate >= 0.60 with enough samples", async () => {
    getCalibrationCoverage.mockResolvedValue({
      ok: true as const,
      data: HEALTHY,
    });
    render(<CalibrationCoverageBadge />);
    const badge = await screen.findByTestId("calibration-coverage-badge");
    expect(badge).toHaveAttribute("data-state", "healthy");
    expect(badge).toHaveTextContent("Kalibratie: goed");
  });

  it("renders warning state when sample size is too small", async () => {
    getCalibrationCoverage.mockResolvedValue({
      ok: true as const,
      data: WARNING_SMALL_SAMPLE,
    });
    render(<CalibrationCoverageBadge />);
    const badge = await screen.findByTestId("calibration-coverage-badge");
    expect(badge).toHaveAttribute("data-state", "warning");
    expect(badge).toHaveTextContent("Kalibratie: matig");
  });

  it("renders warning state when hit-rate is mid-band", async () => {
    getCalibrationCoverage.mockResolvedValue({
      ok: true as const,
      data: WARNING_LOW_RATE,
    });
    render(<CalibrationCoverageBadge />);
    const badge = await screen.findByTestId("calibration-coverage-badge");
    expect(badge).toHaveAttribute("data-state", "warning");
  });

  it("renders insufficient state when diary is empty", async () => {
    getCalibrationCoverage.mockResolvedValue({
      ok: true as const,
      data: INSUFFICIENT,
    });
    render(<CalibrationCoverageBadge />);
    const badge = await screen.findByTestId("calibration-coverage-badge");
    expect(badge).toHaveAttribute("data-state", "insufficient");
    expect(badge).toHaveTextContent("te weinig data");
  });

  it("renders nothing on API failure", async () => {
    getCalibrationCoverage.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    const { container } = render(<CalibrationCoverageBadge />);
    await waitFor(() => {
      expect(getCalibrationCoverage).toHaveBeenCalledTimes(1);
    });
    expect(
      container.querySelector('[data-testid="calibration-coverage-badge"]'),
    ).toBeNull();
  });

  it("calls the endpoint with window_days=90", async () => {
    getCalibrationCoverage.mockResolvedValue({
      ok: true as const,
      data: HEALTHY,
    });
    render(<CalibrationCoverageBadge />);
    await waitFor(() => {
      expect(getCalibrationCoverage).toHaveBeenCalledWith(90);
    });
  });
});
