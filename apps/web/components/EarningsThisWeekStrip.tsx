"use client";

/**
 * V1.2 §AG — Earnings deze week strip.
 *
 * Toont symbolen die deze week door de earnings-gate geblokt zijn
 * (orchestrator verdict ``skip_earnings_window``). Dat is doctrine-
 * correct: de gate kent het exacte earnings-window — wij hoeven hier
 * niet ons eigen earnings-kalender te verzinnen. Tot een echte
 * earnings-feed wordt aangesloten in de worker is dit de meest
 * recente bron van waarheid.
 *
 * Read-only; klikt door naar de full verdicts-pagina voor details.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import {
  apiClient,
  type OrchestratorVerdictRow,
  type OrchestratorVerdictsListResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function uniqueSymbols(rows: OrchestratorVerdictRow[]): OrchestratorVerdictRow[] {
  const seen = new Set<string>();
  const out: OrchestratorVerdictRow[] = [];
  for (const row of rows) {
    if (seen.has(row.symbol)) continue;
    seen.add(row.symbol);
    out.push(row);
  }
  return out;
}

export function EarningsThisWeekStrip() {
  const query = useQuery({
    queryKey: ["earnings-this-week-strip"],
    queryFn: async (): Promise<OrchestratorVerdictsListResponse | null> => {
      const r = await apiClient.listOrchestratorVerdicts({ limit: 200 });
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const items = query.data?.items ?? [];
  const earningsBlocks = uniqueSymbols(
    items.filter((row) => row.decision === "skip_earnings_window"),
  );

  if (earningsBlocks.length === 0) return null;

  return (
    <section
      data-testid="earnings-this-week-strip"
      style={{
        background: "#fef3c7",
        border: "1px solid #fcd34d",
        borderRadius: 8,
        padding: "8px 12px",
        marginBottom: 12,
        display: "flex",
        alignItems: "center",
        gap: 10,
        flexWrap: "wrap",
        fontSize: 13,
      }}
    >
      <strong style={{ color: "#854d0e" }}>Earnings binnen blok-venster:</strong>
      {earningsBlocks.slice(0, 8).map((row) => (
        <span
          key={row.verdict_id}
          data-testid={`earnings-this-week-chip-${row.symbol}`}
          title={row.summary_nl}
          style={{
            background: "#ffffff",
            color: "#92400e",
            padding: "2px 8px",
            borderRadius: 8,
            fontSize: 12,
            fontWeight: 600,
            border: "1px solid #fcd34d",
          }}
        >
          {row.symbol}
        </span>
      ))}
      {earningsBlocks.length > 8 ? (
        <span style={{ fontSize: 12, color: "#854d0e" }}>
          +{earningsBlocks.length - 8} meer
        </span>
      ) : null}
      <Link
        href="/orchestrator-verdicts"
        style={{
          marginLeft: "auto",
          color: "#1d4ed8",
          fontSize: 12,
          textDecoration: "none",
          fontWeight: 600,
        }}
      >
        Details →
      </Link>
    </section>
  );
}
