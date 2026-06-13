"use client";

/**
 * V1.2 §AV / CLAUDE.md §7.3 — Sector-verdeling widget.
 *
 * Toont de huidige portefeuille-spreiding per sector als horizontale
 * staaf met percentage en aantal posities. Geen pie chart om de
 * dependency-set licht te houden; de stapelbalkjes laten net zo
 * helder zien dat tech 60% van de portefeuille is.
 *
 * CLAUDE.md §7.3: de doctrine heeft de harde sector-cap weggehaald —
 * de operator beslist of een tech-zware suggestie nog past. Deze
 * widget geeft daar de feitelijke context bij.
 */

import { useQuery } from "@tanstack/react-query";

import { EmptyState } from "@/components/EmptyState";
import {
  apiClient,
  type SectorRow,
  type SectorSpreadResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

const SECTOR_COLORS: string[] = [
  "#0ea5e9",
  "#a855f7",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#6366f1",
  "#14b8a6",
  "#ec4899",
  "#84cc16",
  "#f97316",
];

function sectorColor(index: number): string {
  return SECTOR_COLORS[index % SECTOR_COLORS.length];
}

function formatPct(value: number): string {
  return `${value.toFixed(1).replace(".", ",")} %`;
}

function SectorBar({
  row,
  color,
}: {
  row: SectorRow;
  color: string;
}) {
  return (
    <div
      data-testid={`sector-bar-${row.sector.toLowerCase()}`}
      style={{ marginBottom: 8 }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 13,
          color: "#374151",
          marginBottom: 4,
        }}
      >
        <span>
          <strong>{row.sector}</strong>
          {" · "}
          <span style={{ color: "#6b7280" }}>
            {row.position_count} positie{row.position_count === 1 ? "" : "s"}
          </span>
        </span>
        <span
          data-testid={`sector-bar-${row.sector.toLowerCase()}-pct`}
          style={{ fontWeight: 600 }}
        >
          {formatPct(row.weight_pct)}
        </span>
      </div>
      <div
        style={{
          position: "relative",
          background: "#f3f4f6",
          borderRadius: 4,
          height: 8,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            width: `${Math.min(100, row.weight_pct)}%`,
            background: color,
            transition: "width 200ms",
          }}
        />
      </div>
    </div>
  );
}

export function SectorSpreadWidget() {
  const query = useQuery({
    queryKey: ["sector-spread"],
    queryFn: async (): Promise<SectorSpreadResponse | null> => {
      const result = await apiClient.getSectorSpread();
      return result.ok ? result.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const data = query.data ?? null;
  const items = data?.items ?? [];

  return (
    <section
      data-testid="sector-spread-widget"
      className="dashboard-panel"
    >
      <div className="panel-head">
        <h2>Sector-verdeling</h2>
        <span
          style={{
            fontSize: 11,
            color: "#6b7280",
            background: "#f3f4f6",
            padding: "2px 8px",
            borderRadius: 10,
          }}
        >
          {data?.total_positions ?? 0} posities
        </span>
      </div>
      <p className="top-sub">
        Je huidige spreiding per sector. CLAUDE.md §7.3 maakt sector-
        concentratie informatief in plaats van een harde limiet — als
        je bewust geconcentreerd wilt zitten in tech, blokkeert de
        software dat niet, maar je ziet hier direct waar je staat.
      </p>
      {items.length === 0 ? (
        <EmptyState
          title="Nog geen posities"
          message="Synchroniseer IBKR-snapshots; daarna verschijnt hier de live spreiding."
        />
      ) : (
        <div data-testid="sector-spread-list">
          {items.map((row, idx) => (
            <SectorBar
              key={row.sector}
              row={row}
              color={sectorColor(idx)}
            />
          ))}
          {data?.has_unclassified ? (
            <p
              data-testid="sector-spread-unclassified-note"
              style={{
                margin: "6px 0 0",
                fontSize: 11,
                color: "#6b7280",
                fontStyle: "italic",
              }}
            >
              &ldquo;Onbekend&rdquo; zijn posities zonder gekoppelde
              fundamentals-snapshot — vaak nieuwe symbolen of
              niet-US/EU instrumenten.
            </p>
          ) : null}
        </div>
      )}
    </section>
  );
}
