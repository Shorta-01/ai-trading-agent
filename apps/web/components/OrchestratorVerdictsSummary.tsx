"use client";

/**
 * V1.2 §AE — Doctrine output summary widget for the dashboard.
 *
 * Compact card showing the profit-harvest orchestrator's latest
 * batch: how many candidates passed each gate, how many got the
 * `suggest` verdict, how many were skipped where.
 *
 * Polls ``/orchestrator-verdicts/today`` every 60s. Clicking the
 * card routes to the full ``/orchestrator-verdicts`` page.
 *
 * Empty state: "Nog geen verdicts vandaag — wacht op de morning
 * chain." Informational only; `safe_for_*` stays False.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import {
  apiClient,
  type OrchestratorVerdictsSummaryResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

const DECISION_LABEL_NL: Record<string, string> = {
  suggest: "Voorgesteld",
  skip_macro_regime: "Marktklimaat",
  skip_risk_universe: "Risico-filter",
  skip_earnings_window: "Earnings-venster",
  skip_confidence_gate: "Vertrouwen te laag",
  skip_below_conviction_floor: "Overtuiging te laag",
  skip_sector_concentration: "Sector-cap",
  skip_pair_build: "Order-pair faal",
};

const DECISION_COLOR: Record<string, { bg: string; fg: string }> = {
  suggest: { bg: "#dcfce7", fg: "#166534" },
  skip_macro_regime: { bg: "#fee2e2", fg: "#991b1b" },
  skip_risk_universe: { bg: "#fed7aa", fg: "#9a3412" },
  skip_earnings_window: { bg: "#fef3c7", fg: "#854d0e" },
  skip_confidence_gate: { bg: "#dbeafe", fg: "#1e3a8a" },
  skip_below_conviction_floor: { bg: "#e0e7ff", fg: "#3730a3" },
  skip_sector_concentration: { bg: "#fce7f3", fg: "#9d174d" },
  skip_pair_build: { bg: "#e5e7eb", fg: "#374151" },
};

export function OrchestratorVerdictsSummary() {
  const query = useQuery({
    queryKey: ["orchestrator-verdicts-summary"],
    queryFn: async (): Promise<OrchestratorVerdictsSummaryResponse | null> => {
      const result = await apiClient.getOrchestratorVerdictsSummary();
      return result.ok ? result.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const data = query.data ?? null;

  if (data === null) {
    return null;
  }

  const isEmpty = data.total === 0;

  return (
    <Link
      href="/orchestrator-verdicts"
      data-testid="orchestrator-verdicts-summary-widget"
      style={{
        display: "block",
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 16,
        marginBottom: 12,
        textDecoration: "none",
        color: "inherit",
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
        Doctrine output vandaag
      </h3>
      {isEmpty ? (
        <p
          data-testid="orchestrator-verdicts-empty"
          style={{ margin: 0, color: "#6b7280", fontSize: 13 }}
        >
          Nog geen verdicts vandaag — wacht op de morning chain.
        </p>
      ) : (
        <>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
              marginBottom: 8,
            }}
          >
            {Object.entries(data.by_decision)
              .sort(([, a], [, b]) => b - a)
              .map(([decision, count]) => {
                const label = DECISION_LABEL_NL[decision] ?? decision;
                const colors = DECISION_COLOR[decision] ?? {
                  bg: "#f3f4f6",
                  fg: "#374151",
                };
                return (
                  <span
                    key={decision}
                    data-testid={`orchestrator-verdicts-chip-${decision}`}
                    style={{
                      background: colors.bg,
                      color: colors.fg,
                      padding: "4px 10px",
                      borderRadius: 12,
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    {label}: {count}
                  </span>
                );
              })}
          </div>
          <p style={{ margin: 0, color: "#6b7280", fontSize: 12 }}>
            Totaal {data.total} kandidaten — klik voor details.
          </p>
        </>
      )}
    </Link>
  );
}
