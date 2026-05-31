"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiClient, type NavHistoryPoint } from "@/lib/apiClient";

/**
 * Compact 30-day NAV trend line for the dashboard.
 *
 * Renders a self-contained inline SVG polyline — no chart library —
 * to keep the dependency surface small. Reads the new
 * ``GET /portfolio/nav/history`` endpoint and renders 30 days by
 * default; click-through navigation is intentionally absent so the
 * sparkline reads as a glance, not an interactive chart.
 *
 * The component never falls back to a fake line: when fewer than 2
 * NAV points exist the sparkline shows a Dutch empty-state explanation
 * instead of inventing an interpolation.
 */

const POLL_INTERVAL_MS = 5 * 60_000;
const DEFAULT_DAYS = 30;

// SVG viewBox dimensions. The component is responsive — the parent
// caller controls the rendered size via CSS width/height.
const VBW = 240;
const VBH = 64;
const PAD_X = 4;
const PAD_Y = 6;

type SparkPoint = { x: number; y: number };

function _toFloats(points: NavHistoryPoint[]): number[] {
  return points
    .map((p) => Number.parseFloat(p.nav_value))
    .filter((v) => Number.isFinite(v));
}

function _projectPoints(values: number[]): SparkPoint[] {
  if (values.length < 2) return [];
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const span = maxV - minV || 1; // avoid div-by-zero on a flat line
  const xStep = (VBW - 2 * PAD_X) / (values.length - 1);
  return values.map((v, i) => ({
    x: PAD_X + i * xStep,
    // SVG y grows downward; invert so high values render at the top.
    y: VBH - PAD_Y - ((v - minV) / span) * (VBH - 2 * PAD_Y),
  }));
}

function _formatChange(values: number[], currency: string | null): string {
  if (values.length < 2) return "—";
  const first = values[0];
  const last = values[values.length - 1];
  const diff = last - first;
  const pct = first === 0 ? 0 : (diff / first) * 100;
  const sign = diff >= 0 ? "+" : "";
  const cur = currency ?? "";
  return `${sign}${diff.toFixed(2)} ${cur} (${sign}${pct.toFixed(2)}%)`;
}

export function NavSparkline({
  days = DEFAULT_DAYS,
}: {
  days?: number;
}) {
  const query = useQuery({
    queryKey: ["nav-sparkline", days],
    queryFn: async () => {
      const r = await apiClient.getNavHistory(days);
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const values = useMemo(
    () => _toFloats(query.data?.points ?? []),
    [query.data?.points],
  );
  const sparkPoints = useMemo(() => _projectPoints(values), [values]);
  const trendUp =
    values.length >= 2 && values[values.length - 1] >= values[0];
  const lineColour = trendUp ? "#16a34a" : "#dc2626";
  const changeText = _formatChange(values, query.data?.base_currency ?? null);

  return (
    <section
      data-testid="nav-sparkline"
      data-trend={trendUp ? "up" : "down"}
      aria-label="Portfolio NAV trend"
      style={{
        background: "white",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: "12px 16px",
        boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
        fontSize: 13,
        fontFamily:
          "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          marginBottom: 8,
          gap: 8,
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: 14,
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span aria-hidden>📈</span>
          <span>NAV trend ({days} d)</span>
        </h3>
        <span
          data-testid="nav-sparkline-change"
          style={{ color: lineColour, fontWeight: 500 }}
        >
          {changeText}
        </span>
      </header>

      {query.isLoading && (
        <p data-testid="nav-sparkline-loading" style={{ color: "#6b7280" }}>
          NAV-historiek laden…
        </p>
      )}

      {!query.isLoading && query.data === null && (
        <p
          data-testid="nav-sparkline-error"
          style={{ color: "#b91c1c", margin: 0 }}
        >
          NAV-historiek niet bereikbaar.
        </p>
      )}

      {!query.isLoading &&
        query.data !== null &&
        sparkPoints.length < 2 && (
          <p
            data-testid="nav-sparkline-empty"
            style={{ color: "#6b7280", margin: 0 }}
          >
            Onvoldoende NAV-punten in de gekozen periode (
            {values.length} gevonden, minimum 2 nodig).
          </p>
        )}

      {sparkPoints.length >= 2 && (
        <svg
          data-testid="nav-sparkline-svg"
          viewBox={`0 0 ${VBW} ${VBH}`}
          preserveAspectRatio="none"
          style={{
            width: "100%",
            height: 60,
            display: "block",
          }}
          aria-hidden
        >
          <polyline
            fill="none"
            stroke={lineColour}
            strokeWidth={1.5}
            points={sparkPoints
              .map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`)
              .join(" ")}
          />
          {/* Endpoint dot so the operator can spot the latest value. */}
          <circle
            cx={sparkPoints[sparkPoints.length - 1].x}
            cy={sparkPoints[sparkPoints.length - 1].y}
            r={2}
            fill={lineColour}
          />
        </svg>
      )}
    </section>
  );
}
