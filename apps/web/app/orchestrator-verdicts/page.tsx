"use client";

/**
 * V1.2 §AE — Orchestrator verdicts page.
 *
 * Full table of the profit-harvest orchestrator's most recent
 * verdicts. Each row shows symbol, decision badge, blocking
 * reason, Dutch summary, timestamp, and (expandable) the full
 * `details_json` blob with per-gate diagnostics.
 *
 * Filters: by decision code via chips. Polls every 60s.
 */

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  apiClient,
  type OrchestratorVerdictRow,
  type OrchestratorVerdictsListResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

const DECISION_LABEL_NL: Record<string, string> = {
  suggest: "Voorgesteld",
  skip_macro_regime: "Marktklimaat",
  skip_risk_universe: "Risico-filter",
  skip_earnings_window: "Earnings-venster",
  skip_confidence_gate: "Vertrouwen",
  skip_below_conviction_floor: "Overtuiging",
  skip_sector_concentration: "Sector-cap",
  skip_pair_build: "Order-pair",
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

function VerdictRow({ row }: { row: OrchestratorVerdictRow }) {
  const [expanded, setExpanded] = useState(false);
  const decisionColors = DECISION_COLOR[row.decision] ?? {
    bg: "#f3f4f6",
    fg: "#374151",
  };
  const decisionLabel = DECISION_LABEL_NL[row.decision] ?? row.decision;
  return (
    <div
      data-testid={`verdict-row-${row.verdict_id}`}
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 12,
        marginBottom: 8,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 6,
        }}
      >
        <span style={{ fontWeight: 700, fontSize: 14 }}>{row.symbol}</span>
        <span
          style={{
            background: decisionColors.bg,
            color: decisionColors.fg,
            padding: "2px 8px",
            borderRadius: 10,
            fontSize: 11,
            fontWeight: 600,
          }}
        >
          {decisionLabel}
        </span>
        {row.blocking_reason && (
          <span style={{ color: "#9ca3af", fontSize: 12 }}>
            ({row.blocking_reason})
          </span>
        )}
        <span
          style={{
            marginLeft: "auto",
            color: "#6b7280",
            fontSize: 11,
          }}
        >
          {new Date(row.generated_at).toLocaleString("nl-BE")}
        </span>
      </div>
      <p style={{ margin: "4px 0", fontSize: 13, color: "#374151" }}>
        {row.summary_nl}
      </p>
      <button
        type="button"
        data-testid={`verdict-row-${row.verdict_id}-toggle`}
        onClick={() => setExpanded((v) => !v)}
        style={{
          background: "transparent",
          border: "none",
          color: "#1d4ed8",
          fontSize: 12,
          cursor: "pointer",
          padding: 0,
        }}
      >
        {expanded ? "Verberg details" : "Toon details"}
      </button>
      {expanded && (
        <pre
          data-testid={`verdict-row-${row.verdict_id}-details`}
          style={{
            marginTop: 8,
            background: "#f9fafb",
            border: "1px solid #e5e7eb",
            borderRadius: 4,
            padding: 8,
            fontSize: 11,
            overflowX: "auto",
            color: "#374151",
          }}
        >
          {JSON.stringify(row.details_json, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default function OrchestratorVerdictsPage() {
  const [filter, setFilter] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["orchestrator-verdicts-list"],
    queryFn: async (): Promise<OrchestratorVerdictsListResponse | null> => {
      const result = await apiClient.listOrchestratorVerdicts({ limit: 200 });
      return result.ok ? result.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const data = query.data;

  const items = data?.items ?? [];
  const filtered = filter ? items.filter((i) => i.decision === filter) : items;
  const decisionsPresent = Array.from(new Set(items.map((i) => i.decision)));

  return (
    <main style={{ padding: 24, maxWidth: 960, margin: "0 auto" }}>
      <h1 style={{ margin: "0 0 4px", fontSize: 22, fontWeight: 700 }}>
        Orchestrator verdicts
      </h1>
      <p
        style={{ margin: "0 0 16px", fontSize: 13, color: "#6b7280" }}
        data-testid="orchestrator-verdicts-help"
      >
        {data?.help_nl ??
          "Verdicts van de profit-harvest orchestrator per kandidaat."}
      </p>
      <div
        style={{
          display: "flex",
          gap: 6,
          flexWrap: "wrap",
          marginBottom: 12,
        }}
        data-testid="orchestrator-verdicts-filter-row"
      >
        <button
          type="button"
          onClick={() => setFilter(null)}
          data-testid="verdict-filter-all"
          style={{
            padding: "4px 10px",
            border: filter === null ? "2px solid #1d4ed8" : "1px solid #d1d5db",
            background: "#ffffff",
            borderRadius: 12,
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          Alle ({items.length})
        </button>
        {decisionsPresent.map((d) => {
          const colors = DECISION_COLOR[d] ?? { bg: "#f3f4f6", fg: "#374151" };
          const count = items.filter((i) => i.decision === d).length;
          return (
            <button
              key={d}
              type="button"
              onClick={() => setFilter(d)}
              data-testid={`verdict-filter-${d}`}
              style={{
                padding: "4px 10px",
                border: filter === d ? "2px solid #1d4ed8" : "1px solid #d1d5db",
                background: colors.bg,
                color: colors.fg,
                borderRadius: 12,
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {DECISION_LABEL_NL[d] ?? d} ({count})
            </button>
          );
        })}
      </div>
      {filtered.length === 0 ? (
        <p
          data-testid="orchestrator-verdicts-empty"
          style={{ color: "#6b7280", fontSize: 13 }}
        >
          {items.length === 0
            ? "Nog geen verdicts geschreven."
            : "Geen verdicts voor dit filter."}
        </p>
      ) : (
        <div>
          {filtered.map((row) => (
            <VerdictRow key={row.verdict_id} row={row} />
          ))}
        </div>
      )}
    </main>
  );
}
