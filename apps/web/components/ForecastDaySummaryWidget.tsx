"use client";

/**
 * Task 131: Dashboard day-summary widget.
 *
 * Compact card showing label counts for today's forecasts. Polls
 * ``/forecast/day-summary`` every 60s. Clicking a label routes to
 * ``/volglijst?filter=<label>`` so the user can drill into the rows
 * carrying that label.
 *
 * Empty state: "Geen voorspellingen vandaag — wacht op volgende
 * morgenrun om 07:00."
 *
 * Informational only — gates no action, ``safe_for_*`` stays False.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  apiClient,
  type ForecastDaySummaryResponse,
  type ForecastLabel,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

const LABEL_ORDER: ForecastLabel[] = [
  "Kopen",
  "Bekijken",
  "Houden",
  "Verminderen",
  "Verkopen",
  "Geblokkeerd",
];

const LABEL_COLORS: Record<ForecastLabel, { bg: string; fg: string }> = {
  Kopen: { bg: "#dcfce7", fg: "#166534" },
  Verminderen: { bg: "#fed7aa", fg: "#9a3412" },
  Verkopen: { bg: "#fecaca", fg: "#7f1d1d" },
  Houden: { bg: "#dbeafe", fg: "#1e3a8a" },
  Bekijken: { bg: "#fef3c7", fg: "#854d0e" },
  Geblokkeerd: { bg: "#e5e7eb", fg: "#374151" },
};


export function ForecastDaySummaryWidget() {
  const [data, setData] = useState<ForecastDaySummaryResponse | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const result = await apiClient.getForecastDaySummary();
      if (cancelled) return;
      if (result.ok) {
        setData(result.data);
        setUnavailable(false);
      } else {
        setUnavailable(true);
      }
    }

    void load();
    const handle = window.setInterval(() => {
      void load();
    }, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  if (unavailable) {
    return null;
  }
  if (data === null) {
    return null;
  }

  const isEmpty = data.total_forecasts === 0;

  return (
    <div
      data-testid="forecast-day-summary-widget"
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 16,
        marginBottom: 12,
      }}
    >
      <h3
        style={{
          margin: "0 0 8px",
          fontSize: 14,
          fontWeight: 700,
          color: "#1f2937",
        }}
      >
        Vandaag&apos;s voorspellingen
      </h3>

      {isEmpty ? (
        <p
          data-testid="forecast-day-summary-empty"
          style={{ margin: 0, fontSize: 13, color: "#6b7280" }}
        >
          Geen voorspellingen vandaag — wacht op volgende morgenrun om 07:00.
        </p>
      ) : (
        <>
          <p
            data-testid="forecast-day-summary-total"
            style={{ margin: "0 0 8px", fontSize: 13, color: "#374151" }}
          >
            {data.total_forecasts} voorspellingen, {data.total_blocked} geblokkeerd.
          </p>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {LABEL_ORDER.map((label) => {
              const count = data.label_counts[label] ?? 0;
              if (count === 0) return null;
              const colors = LABEL_COLORS[label];
              return (
                <Link
                  key={label}
                  href={`/volglijst?filter=${encodeURIComponent(label)}`}
                  data-testid={`forecast-day-summary-pill-${label}`}
                  style={{
                    background: colors.bg,
                    color: colors.fg,
                    padding: "4px 10px",
                    borderRadius: 999,
                    fontSize: 12,
                    fontWeight: 600,
                    textDecoration: "none",
                  }}
                >
                  {count} {label}
                </Link>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
