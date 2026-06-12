"use client";

/**
 * V1.2 §AF — Watchlist snapshot.
 *
 * Compact view of the active watchlist with — for each item — the
 * latest suggestion's action label and confidence, plus the latest
 * forecast direction if available. Link routes to the full
 * volglijst page.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { EmptyState } from "@/components/EmptyState";
import {
  apiClient,
  type AssetForecastResponse,
  type AssetSuggestionResponse,
  listWatchlistItems,
  type WatchlistItemResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function actionTone(action: string | undefined): { bg: string; fg: string } {
  if (!action) return { bg: "#f3f4f6", fg: "#374151" };
  if (action === "Kopen" || action === "Langzaam bijkopen")
    return { bg: "#dcfce7", fg: "#166534" };
  if (action === "Verkopen" || action === "Vermijden")
    return { bg: "#fee2e2", fg: "#991b1b" };
  if (action === "Verminderen") return { bg: "#fed7aa", fg: "#9a3412" };
  if (action === "Bekijken") return { bg: "#dbeafe", fg: "#1e3a8a" };
  if (action === "Houden") return { bg: "#e0e7ff", fg: "#3730a3" };
  return { bg: "#f3f4f6", fg: "#374151" };
}

function Row({
  watchlist,
  forecast,
  suggestion,
}: {
  watchlist: WatchlistItemResponse;
  forecast?: AssetForecastResponse;
  suggestion?: AssetSuggestionResponse;
}) {
  const symbol = watchlist.item.symbol;
  const action = suggestion?.action_label_nl ?? "Nog geen advies";
  const tone = actionTone(suggestion?.action_label_nl);
  return (
    <li
      data-testid={`watchlist-snapshot-row-${symbol}`}
      style={{
        listStyle: "none",
        padding: "6px 8px",
        marginBottom: 4,
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 6,
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}
    >
      <span style={{ fontWeight: 700, fontSize: 13, minWidth: 64 }}>
        {symbol}
      </span>
      <span
        style={{
          background: tone.bg,
          color: tone.fg,
          fontSize: 11,
          fontWeight: 600,
          padding: "2px 8px",
          borderRadius: 8,
        }}
      >
        {action}
      </span>
      <span style={{ fontSize: 11, color: "#6b7280" }}>
        {forecast?.direction_label_nl ?? "Geen voorspelling"}
      </span>
      <span
        style={{
          marginLeft: "auto",
          fontSize: 11,
          color: "#9ca3af",
        }}
      >
        {watchlist.linked_asset?.asset_name ?? watchlist.item.name ?? ""}
      </span>
    </li>
  );
}

export function WatchlistSnapshot() {
  const query = useQuery({
    queryKey: ["watchlist-snapshot"],
    queryFn: async () => {
      const [wlRes, fcRes, sgRes] = await Promise.all([
        listWatchlistItems(),
        apiClient.getLatestForecasts(),
        apiClient.getLatestSuggestions(),
      ]);
      return {
        watchlist: wlRes.ok ? wlRes.data.items : [],
        forecasts: fcRes.ok ? fcRes.data.items : [],
        suggestions: sgRes.ok ? sgRes.data.items : [],
      };
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const items = (query.data?.watchlist ?? []).filter(
    (w) => w.item.status === "active",
  );
  const forecastBySymbol = new Map<string, AssetForecastResponse>();
  for (const f of query.data?.forecasts ?? []) forecastBySymbol.set(f.symbol, f);
  const suggestionBySymbol = new Map<string, AssetSuggestionResponse>();
  for (const s of query.data?.suggestions ?? [])
    suggestionBySymbol.set(s.symbol, s);

  return (
    <section
      data-testid="watchlist-snapshot"
      className="dashboard-panel"
      style={{ marginBottom: 12 }}
    >
      <div className="panel-head">
        <h2 style={{ margin: 0, fontSize: 16 }}>Watchlist</h2>
        <Link
          href="/volglijst"
          style={{ fontSize: 12, color: "#1d4ed8", textDecoration: "none" }}
        >
          Volglijst openen →
        </Link>
      </div>
      {items.length === 0 ? (
        <EmptyState
          title="Watchlist is leeg"
          message="Voeg eerst items toe via Volglijst voordat ze hier verschijnen."
        />
      ) : (
        <ul style={{ margin: 0, padding: 0 }}>
          {items.slice(0, 8).map((w) => (
            <Row
              key={w.item.watchlist_item_id}
              watchlist={w}
              forecast={forecastBySymbol.get(w.item.symbol)}
              suggestion={suggestionBySymbol.get(w.item.symbol)}
            />
          ))}
          {items.length > 8 ? (
            <li style={{ listStyle: "none", fontSize: 11, color: "#6b7280" }}>
              +{items.length - 8} meer…
            </li>
          ) : null}
        </ul>
      )}
    </section>
  );
}
