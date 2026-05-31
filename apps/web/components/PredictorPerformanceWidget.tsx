"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/apiClient";

/**
 * Predictor performance leaderboard for the dashboard.
 *
 * Renders the rolling per-predictor Brier-score table from the
 * Prediction Diary feedback loop. The first row is the operator's
 * "best model this month" — useful as a sanity check that the
 * auto-weighted ensemble strategy (Slice 26) is picking the right
 * predictors.
 *
 * Pure read; no actions, no advice. The numbers are aggregates over
 * the past N days (default 30) and only count diary entries that
 * already have a realised outcome.
 */

const POLL_INTERVAL_MS = 10 * 60_000;
const DEFAULT_LOOKBACK = 30;

function _brierColour(brier: number): string {
  // Lower Brier = better. Map 0–1 → green at 0.2 → amber at 0.3 → red at 0.4.
  if (brier <= 0.2) return "#16a34a";
  if (brier <= 0.3) return "#f59e0b";
  return "#dc2626";
}

export function PredictorPerformanceWidget({
  lookbackDays = DEFAULT_LOOKBACK,
}: {
  lookbackDays?: number;
}) {
  const query = useQuery({
    queryKey: ["predictor-performance", lookbackDays],
    queryFn: async () => {
      const r = await apiClient.getPredictorPerformance(lookbackDays);
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  return (
    <section
      data-testid="predictor-performance-widget"
      aria-label="Predictor performance leaderboard"
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
        <h3 style={{ margin: 0, fontSize: 14 }}>
          <span aria-hidden style={{ marginRight: 6 }}>🏆</span>
          <span>Predictor performance ({lookbackDays} d)</span>
        </h3>
        {query.data?.best_model_code && (
          <span
            data-testid="predictor-performance-best"
            style={{ color: "#16a34a", fontWeight: 600 }}
          >
            Best: {query.data.best_model_code}
          </span>
        )}
      </header>

      {query.isLoading && (
        <p
          data-testid="predictor-performance-loading"
          style={{ color: "#6b7280" }}
        >
          Predictor-historiek laden…
        </p>
      )}

      {!query.isLoading && query.data === null && (
        <p
          data-testid="predictor-performance-error"
          style={{ color: "#b91c1c", margin: 0 }}
        >
          Predictor-historiek niet bereikbaar.
        </p>
      )}

      {!query.isLoading &&
        query.data &&
        query.data.predictors.length === 0 && (
          <p
            data-testid="predictor-performance-empty"
            style={{ color: "#6b7280", margin: 0 }}
          >
            Nog geen predictor-contributies. De Prediction Diary heeft de
            uitkomsten van vorige forecasts nog niet gerealiseerd.
          </p>
        )}

      {query.data && query.data.predictors.length > 0 && (
        <table
          data-testid="predictor-performance-table"
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 12,
          }}
        >
          <thead>
            <tr style={{ color: "#6b7280", textAlign: "left" }}>
              <th style={{ padding: "4px 6px" }}>Model</th>
              <th style={{ padding: "4px 6px", textAlign: "right" }}>
                n
              </th>
              <th style={{ padding: "4px 6px", textAlign: "right" }}>
                Brier
              </th>
              <th style={{ padding: "4px 6px", textAlign: "right" }}>
                Real. return %
              </th>
            </tr>
          </thead>
          <tbody>
            {query.data.predictors.map((p) => {
              const brier = p.mean_brier_score
                ? Number.parseFloat(p.mean_brier_score)
                : null;
              return (
                <tr
                  key={`${p.model_code}-${p.model_version}`}
                  data-testid={`predictor-performance-row-${p.model_code}`}
                  style={{ borderTop: "1px solid #f3f4f6" }}
                >
                  <td style={{ padding: "4px 6px", fontWeight: 500 }}>
                    {p.model_code}
                    <span
                      style={{
                        color: "#9ca3af",
                        fontWeight: 400,
                        marginLeft: 4,
                      }}
                    >
                      {p.model_version}
                    </span>
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      textAlign: "right",
                      color: "#6b7280",
                    }}
                  >
                    {p.realised_sample_count}/{p.sample_count}
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      textAlign: "right",
                      color:
                        brier !== null
                          ? _brierColour(brier)
                          : "#9ca3af",
                      fontWeight: 500,
                    }}
                  >
                    {p.mean_brier_score ?? "—"}
                  </td>
                  <td
                    style={{
                      padding: "4px 6px",
                      textAlign: "right",
                      color: "#374151",
                    }}
                  >
                    {p.mean_realised_return_pct ?? "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}
