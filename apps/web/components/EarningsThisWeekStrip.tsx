"use client";

/**
 * V1.2 §AI — Earnings deze week strip.
 *
 * Eerst probeert het de echte earnings-feed uit
 * ``/earnings/upcoming`` (leest ``earnings_events`` tabel, gevuld
 * door de EODHD writer leg — §AJ follow-up). Zolang die tabel leeg
 * is valt de strip terug op het bestaande verdict-filter
 * (``decision === "skip_earnings_window"``) zodat de operator nu al
 * iets nuttigs ziet zonder dat de writer-leg er moet zijn.
 *
 * Read-only; klikt door naar de full verdicts-pagina voor details.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import {
  apiClient,
  type EarningsEventRow,
  type EarningsUpcomingResponse,
  type OrchestratorVerdictRow,
  type OrchestratorVerdictsListResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function uniqueVerdictSymbols(
  rows: OrchestratorVerdictRow[],
): OrchestratorVerdictRow[] {
  const seen = new Set<string>();
  const out: OrchestratorVerdictRow[] = [];
  for (const row of rows) {
    if (seen.has(row.symbol)) continue;
    seen.add(row.symbol);
    out.push(row);
  }
  return out;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("nl-BE", {
      day: "2-digit",
      month: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function EarningsThisWeekStrip() {
  const earningsQuery = useQuery({
    queryKey: ["earnings-this-week-strip-feed"],
    queryFn: async (): Promise<EarningsUpcomingResponse | null> => {
      const r = await apiClient.getUpcomingEarnings({ days: 7 });
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const verdictsQuery = useQuery({
    queryKey: ["earnings-this-week-strip-verdicts"],
    queryFn: async (): Promise<OrchestratorVerdictsListResponse | null> => {
      const r = await apiClient.listOrchestratorVerdicts({ limit: 200 });
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const earningsItems = earningsQuery.data?.items ?? [];
  const hasFeed = earningsItems.length > 0;

  const verdictItems = verdictsQuery.data?.items ?? [];
  const fallbackBlocks = uniqueVerdictSymbols(
    verdictItems.filter((row) => row.decision === "skip_earnings_window"),
  );

  if (!hasFeed && fallbackBlocks.length === 0) {
    return null;
  }

  return (
    <section
      data-testid="earnings-this-week-strip"
      data-mode={hasFeed ? "feed" : "fallback"}
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
      <strong style={{ color: "#854d0e" }}>
        {hasFeed ? "Earnings deze week:" : "Earnings binnen blok-venster:"}
      </strong>
      {hasFeed
        ? earningsItems.slice(0, 8).map((row: EarningsEventRow) => (
            <span
              key={row.earnings_event_id}
              data-testid={`earnings-this-week-chip-${row.symbol}`}
              title={`${row.status} • ${row.source} • ${row.event_date}`}
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
              {row.symbol} {formatDate(row.event_date)}
            </span>
          ))
        : fallbackBlocks.slice(0, 8).map((row) => (
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
      {(hasFeed ? earningsItems.length : fallbackBlocks.length) > 8 ? (
        <span style={{ fontSize: 12, color: "#854d0e" }}>
          +{(hasFeed ? earningsItems.length : fallbackBlocks.length) - 8} meer
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
