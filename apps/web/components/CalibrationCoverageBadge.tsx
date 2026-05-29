"use client";

/**
 * Task 130: Dashboard calibration badge.
 *
 * Reads the rolling 90-day calibration coverage from
 * ``/calibration/coverage`` and renders one of three locked states:
 *
 * * ``healthy``  (green)  — hit-rate ≥ 0.60 within p10..p90 band
 * * ``warning``  (amber)  — hit-rate between 0.40 and 0.60, OR <10 evaluated
 * * ``insufficient`` (grey) — diary empty (0 evaluated)
 *
 * The badge is informational only: it does not gate any draft or
 * order action. ``safe_for_*`` stays False everywhere.
 */

import { useQuery } from "@tanstack/react-query";

import {
  apiClient,
  CalibrationCoverageResponse,
} from "@/lib/apiClient";

const HEALTHY_HIT_RATE_FLOOR = 0.6;
const WARNING_HIT_RATE_FLOOR = 0.4;
const MIN_SAMPLE_SIZE = 10;
const POLL_INTERVAL_MS = 60_000;

type Visual = {
  readonly background: string;
  readonly color: string;
  readonly border: string;
  readonly label: string;
};

const VISUALS: Record<"healthy" | "warning" | "insufficient", Visual> = {
  healthy: {
    background: "#dcfce7",
    color: "#166534",
    border: "#bbf7d0",
    label: "Kalibratie: goed",
  },
  warning: {
    background: "#fef3c7",
    color: "#92400e",
    border: "#fde68a",
    label: "Kalibratie: matig",
  },
  insufficient: {
    background: "#f3f4f6",
    color: "#374151",
    border: "#d1d5db",
    label: "Kalibratie: te weinig data",
  },
};


function classify(data: CalibrationCoverageResponse): keyof typeof VISUALS {
  if (
    data.forecasts_evaluated === 0 ||
    data.hit_rate_within_band === null
  ) {
    return "insufficient";
  }
  const rate = Number(data.hit_rate_within_band);
  if (Number.isNaN(rate)) {
    return "insufficient";
  }
  if (data.forecasts_evaluated < MIN_SAMPLE_SIZE) {
    return "warning";
  }
  if (rate >= HEALTHY_HIT_RATE_FLOOR) {
    return "healthy";
  }
  if (rate >= WARNING_HIT_RATE_FLOOR) {
    return "warning";
  }
  return "warning";
}


export function CalibrationCoverageBadge() {
  const query = useQuery({
    queryKey: ["calibration-coverage", 90],
    queryFn: async (): Promise<CalibrationCoverageResponse | null> => {
      const result = await apiClient.getCalibrationCoverage(90);
      return result.ok ? result.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const data = query.data ?? null;

  if (data === null) {
    return null;
  }

  const state = classify(data);
  const visuals = VISUALS[state];
  const helpText =
    data.hit_rate_within_band === null
      ? `Geen voorspellingen geëvalueerd in laatste ${data.window_days} dagen.`
      : `${data.forecasts_evaluated} voorspellingen geëvalueerd in laatste ${data.window_days} dagen; ${(Number(data.hit_rate_within_band) * 100).toFixed(0)}% binnen p10–p90 band.`;

  return (
    <span
      data-testid="calibration-coverage-badge"
      data-state={state}
      role="status"
      aria-label={`${visuals.label}. ${helpText}`}
      title={helpText}
      style={{
        background: visuals.background,
        color: visuals.color,
        border: `1px solid ${visuals.border}`,
        padding: "4px 10px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        display: "inline-block",
      }}
    >
      {visuals.label}
    </span>
  );
}
