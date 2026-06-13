"use client";

/**
 * V1.2 §AU / CLAUDE.md §5 — Favorieten dashboard-blok.
 *
 * Toont de symbolen die de operator als favoriet heeft gemarkeerd,
 * met de meest recente orchestrator-scoring (confidence + decision +
 * blocking_reason) per symbool. Ook namen die nog niet door de gates
 * komen verschijnen — zo ziet de operator waarom een favoriet (nog)
 * geen voorstel is.
 *
 * Read-only: er staat geen "Goedkeuren"-knop op favorieten. De BUY-
 * voorstellen blijven op de hoofd-flow lopen via Acties → Te keuren.
 */

import { useQuery } from "@tanstack/react-query";

import { EmptyState } from "@/components/EmptyState";
import {
  apiClient,
  type WatchlistFavoriteRow,
  type WatchlistFavoritesResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function formatConfidence(value: number | null): string {
  if (value === null) return "—";
  // Storage writes confidence as 0–1; surface as a percentage with a
  // Dutch decimal comma.
  const pct = value <= 1 ? value * 100 : value;
  return `${pct.toFixed(1).replace(".", ",")} %`;
}

function decisionBadge(decision: string | null): {
  label: string;
  background: string;
  color: string;
} {
  if (decision === null) {
    return {
      label: "Nog geen score",
      background: "#f3f4f6",
      color: "#6b7280",
    };
  }
  if (decision === "suggest") {
    return { label: "Voorstel", background: "#dcfce7", color: "#166534" };
  }
  // All skip_* decisions render with the warning tone — operator can
  // open the row note to see exactly which gate fired.
  return {
    label: "Geblokkeerd door gate",
    background: "#fef3c7",
    color: "#92400e",
  };
}

function FavorietenRow({ row }: { row: WatchlistFavoriteRow }) {
  const badge = decisionBadge(row.latest_decision);
  return (
    <div
      data-testid={`favoriet-row-${row.symbol}`}
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
          alignItems: "baseline",
          gap: 12,
          marginBottom: 6,
        }}
      >
        <span
          data-testid={`favoriet-symbol-${row.symbol}`}
          style={{ fontWeight: 700, fontSize: 14 }}
        >
          {row.symbol}
        </span>
        <span
          data-testid={`favoriet-confidence-${row.symbol}`}
          style={{ fontSize: 12, color: "#374151" }}
        >
          Confidence: {formatConfidence(row.latest_confidence)}
        </span>
        <span
          data-testid={`favoriet-decision-${row.symbol}`}
          style={{
            marginLeft: "auto",
            fontSize: 11,
            background: badge.background,
            color: badge.color,
            padding: "2px 8px",
            borderRadius: 10,
            fontWeight: 600,
          }}
        >
          {badge.label}
        </span>
      </div>
      {row.latest_summary_nl ? (
        <p
          data-testid={`favoriet-summary-${row.symbol}`}
          style={{
            margin: 0,
            fontSize: 12,
            color: "#374151",
          }}
        >
          {row.latest_summary_nl}
        </p>
      ) : null}
      {row.latest_blocking_reason ? (
        <p
          data-testid={`favoriet-blocking-${row.symbol}`}
          style={{
            margin: "4px 0 0",
            fontSize: 11,
            color: "#92400e",
          }}
        >
          Gate-blok: {row.latest_blocking_reason}
        </p>
      ) : null}
      {row.note ? (
        <p
          data-testid={`favoriet-note-${row.symbol}`}
          style={{
            margin: "4px 0 0",
            fontSize: 11,
            color: "#6b7280",
            fontStyle: "italic",
          }}
        >
          Notitie: {row.note}
        </p>
      ) : null}
    </div>
  );
}

export function FavorietenWidget() {
  const query = useQuery({
    queryKey: ["watchlist-favorieten"],
    queryFn: async (): Promise<WatchlistFavoritesResponse | null> => {
      const result = await apiClient.listFavorieten();
      return result.ok ? result.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const data = query.data ?? null;
  const items = data?.items ?? [];

  return (
    <section
      data-testid="favorieten-widget"
      className="dashboard-panel"
    >
      <div className="panel-head">
        <h2>Favorieten</h2>
        <span
          style={{
            fontSize: 11,
            color: "#6b7280",
            background: "#f3f4f6",
            padding: "2px 8px",
            borderRadius: 10,
          }}
        >
          Live confidence
        </span>
      </div>
      <p className="top-sub">
        Symbolen die je extra wilt opvolgen. Ook als ze de gates niet
        passeren, zie je hier de recentste score zodat duidelijk is
        waarom ze (nog) geen voorstel zijn. Beheer de lijst via{" "}
        <strong>Instellingen → Watchlist</strong>.
      </p>
      {items.length === 0 ? (
        <EmptyState
          title="Nog geen favorieten"
          message="Voeg symbolen toe op de instellingenpagina om hier live confidence te zien."
        />
      ) : (
        <div data-testid="favorieten-list">
          {items.map((row) => (
            <FavorietenRow key={row.watchlist_preference_id} row={row} />
          ))}
        </div>
      )}
    </section>
  );
}
