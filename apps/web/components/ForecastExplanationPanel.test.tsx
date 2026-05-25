import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

import type { ForecastLatestResponse } from "@/lib/apiClient";

const getForecastLatest = vi.fn();
const getLatestDecisionPackage = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getForecastLatest: (...args: unknown[]) => getForecastLatest(...args),
    getLatestDecisionPackage: (...args: unknown[]) =>
      getLatestDecisionPackage(...args),
  },
}));

import { ForecastExplanationPanel } from "./ForecastExplanationPanel";

const HAPPY: ForecastLatestResponse = {
  conid: "ASML.AS",
  generated_at: "2026-05-25T07:00:00+00:00",
  forecast_valid_until: "2026-06-22T07:00:00+00:00",
  horizon_trading_days: 20,
  method: "historical_bootstrap_v1",
  current_price_local: "640.000000",
  currency_local: "EUR",
  p10_log_return: "-0.05",
  p50_log_return: "0.02",
  p90_log_return: "0.08",
  p10_price_local: "608.769",
  p50_price_local: "652.929",
  p90_price_local: "693.282",
  p10_price_eur: "608.769",
  p50_price_eur: "652.929",
  p90_price_eur: "693.282",
  prob_positive: "0.62",
  prob_loss_gt_5pct: "0.12",
  expected_volatility_annualized: "0.25",
  confidence_level: "Hoog",
  label: "Bekijken",
  block_reason: null,
  per_asset_coverage: {
    forecasts_evaluated: 0,
    hit_rate_within_band: null,
    sufficient_history: false,
  },
  safe_for_action_drafts: false,
  safe_for_orders: false,
};

beforeEach(() => {
  getForecastLatest.mockReset();
  getLatestDecisionPackage.mockReset();
  // Default: no Decision Package — keeps existing tests unaffected.
  getLatestDecisionPackage.mockResolvedValue({
    ok: false as const,
    reason: "not_reachable",
  });
});

afterEach(() => {
  cleanup();
});

describe("ForecastExplanationPanel", () => {
  it("renders nothing when not open", () => {
    const { container } = render(
      <ForecastExplanationPanel conid="ASML.AS" open={false} onClose={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
    expect(getForecastLatest).not.toHaveBeenCalled();
  });

  it("renders nine locked Dutch fields on happy path", async () => {
    getForecastLatest.mockResolvedValue({ ok: true as const, data: HAPPY });
    render(
      <ForecastExplanationPanel conid="ASML.AS" open={true} onClose={() => {}} />,
    );

    await waitFor(() => {
      expect(getForecastLatest).toHaveBeenCalledWith("ASML.AS");
    });

    expect(await screen.findByTestId("forecast-field-direction")).toHaveTextContent(
      "Bekijken",
    );
    expect(screen.getByTestId("forecast-field-prob-positive")).toHaveTextContent(
      "62.0%",
    );
    expect(screen.getByTestId("forecast-field-prob-loss")).toHaveTextContent(
      "12.0%",
    );
    expect(screen.getByTestId("forecast-field-band")).toHaveTextContent(
      "608.769 – 693.282 EUR",
    );
    expect(screen.getByTestId("forecast-field-volatility")).toHaveTextContent(
      "25.0% per jaar",
    );
    expect(screen.getByTestId("forecast-field-confidence")).toHaveTextContent(
      "Hoog",
    );
    expect(screen.getByTestId("forecast-field-rationale")).toHaveTextContent(
      "20 handelsdagen",
    );
    expect(screen.getByTestId("forecast-field-method")).toHaveTextContent(
      "Historische bootstrap, 252 dagen, blok-resampling",
    );
    expect(screen.getByTestId("forecast-field-valid-until")).toHaveTextContent(
      "2026-06-22",
    );
  });

  it("shows block_reason next to label when forecast is blocked", async () => {
    getForecastLatest.mockResolvedValue({
      ok: true as const,
      data: {
        ...HAPPY,
        label: "Geblokkeerd",
        block_reason: "insufficient_history",
      },
    });
    render(
      <ForecastExplanationPanel conid="ASML.AS" open={true} onClose={() => {}} />,
    );
    const direction = await screen.findByTestId("forecast-field-direction");
    expect(direction).toHaveTextContent("Geblokkeerd");
    expect(direction).toHaveTextContent("insufficient_history");
  });

  it("renders dual local + EUR band when currency is not EUR", async () => {
    getForecastLatest.mockResolvedValue({
      ok: true as const,
      data: {
        ...HAPPY,
        currency_local: "USD",
        p10_price_eur: "553.98",
        p90_price_eur: "630.89",
      },
    });
    render(
      <ForecastExplanationPanel conid="NVDA" open={true} onClose={() => {}} />,
    );
    const band = await screen.findByTestId("forecast-field-band");
    expect(band).toHaveTextContent("USD");
    expect(band).toHaveTextContent("EUR");
    expect(band).toHaveTextContent("553.98");
  });

  it("shows error message on fetch failure", async () => {
    getForecastLatest.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    render(
      <ForecastExplanationPanel conid="ASML.AS" open={true} onClose={() => {}} />,
    );
    expect(
      await screen.findByTestId("forecast-explanation-error"),
    ).toBeInTheDocument();
  });

  it("shows fallback when per_asset_coverage has insufficient history", async () => {
    getForecastLatest.mockResolvedValue({ ok: true as const, data: HAPPY });
    render(
      <ForecastExplanationPanel conid="ASML.AS" open={true} onClose={() => {}} />,
    );
    const coverage = await screen.findByTestId("forecast-field-per-asset-coverage");
    expect(coverage).toHaveTextContent("Onvoldoende historiek voor kalibratie.");
  });

  it("shows hit-rate when per_asset_coverage has sufficient history", async () => {
    getForecastLatest.mockResolvedValue({
      ok: true as const,
      data: {
        ...HAPPY,
        per_asset_coverage: {
          forecasts_evaluated: 12,
          hit_rate_within_band: "0.75",
          sufficient_history: true,
        },
      },
    });
    render(
      <ForecastExplanationPanel conid="ASML.AS" open={true} onClose={() => {}} />,
    );
    const coverage = await screen.findByTestId("forecast-field-per-asset-coverage");
    expect(coverage).toHaveTextContent("75% binnen p10–p90 band");
    expect(coverage).toHaveTextContent("12 evaluaties");
  });

  it("calls onClose when close button clicked", async () => {
    getForecastLatest.mockResolvedValue({ ok: true as const, data: HAPPY });
    const onClose = vi.fn();
    render(
      <ForecastExplanationPanel conid="ASML.AS" open={true} onClose={onClose} />,
    );
    await screen.findByTestId("forecast-field-direction");
    fireEvent.click(screen.getByTestId("forecast-explanation-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows 'Bekijk Decision Package' button linking to the detail page", async () => {
    getForecastLatest.mockResolvedValue({ ok: true as const, data: HAPPY });
    getLatestDecisionPackage.mockResolvedValue({
      ok: true as const,
      data: { decision_package_id: "dp-xyz-123" },
    });
    render(
      <ForecastExplanationPanel conid="ASML.AS" open={true} onClose={() => {}} />,
    );
    const button = await screen.findByTestId(
      "forecast-bekijk-decision-package",
    );
    expect(button.getAttribute("href")).toBe(
      "/decision-package/dp-xyz-123",
    );
  });

  it("hides 'Bekijk Decision Package' when no package exists", async () => {
    getForecastLatest.mockResolvedValue({ ok: true as const, data: HAPPY });
    getLatestDecisionPackage.mockResolvedValue({
      ok: false as const,
      reason: "not_reachable",
    });
    render(
      <ForecastExplanationPanel conid="ASML.AS" open={true} onClose={() => {}} />,
    );
    await screen.findByTestId("forecast-field-direction");
    expect(
      screen.queryByTestId("forecast-bekijk-decision-package"),
    ).toBeNull();
  });
});
