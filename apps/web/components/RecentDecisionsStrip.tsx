"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/apiClient";
import type { SuggestionsGridResponse } from "@/lib/apiClient";

/**
 * Recent Decision Packages strip — last N suggestions across all
 * held conids, sorted newest first. Reuses the existing
 * ``/suggestions/grid`` payload (no new endpoint) and flattens every
 * section into a chronological glance.
 *
 * The operator can scan the strip and immediately see:
 *   * "3 nieuwe verkoop-suggesties met hoog vertrouwen" — urgent
 *   * "Alleen 'houden' adviezen vandaag" — calm
 *   * "Top driver tonen" via hover (title attribute)
 *
 * Click a chip → /suggesties for full detail.
 */

const MAX_ROWS = 5;
const POLL_INTERVAL_MS = 60_000;

type FlatItem = {
  suggestion_id: string;
  symbol: string;
  action_label_nl: string;
  confidence_label_nl: string;
  diff_status: string;
  top_driver_nl: string | null;
  generated_at: string;
};

function actionToneColour(label: string): string {
  const lower = label.toLowerCase();
  if (lower.includes("koop")) return "#16a34a";
  if (lower.includes("verkoop")) return "#dc2626";
  if (lower.includes("houd")) return "#6b7280";
  return "#374151";
}

function chipBackground(diffStatus: string): string {
  if (diffStatus === "nieuw") return "#fef3c7"; // amber-100
  if (diffStatus === "gewijzigd") return "#dbeafe"; // blue-100
  return "#f3f4f6"; // grey-100
}

function flattenGrid(grid: SuggestionsGridResponse | null): FlatItem[] {
  if (!grid) return [];
  const items: FlatItem[] = [];
  for (const section of grid.sections ?? []) {
    for (const item of section.items ?? []) {
      items.push({
        suggestion_id: item.suggestion_id,
        symbol: item.symbol,
        action_label_nl: item.action_label_nl,
        confidence_label_nl: item.confidence_label_nl,
        diff_status: item.diff_status,
        top_driver_nl: item.top_driver_nl ?? null,
        generated_at: item.generated_at,
      });
    }
  }
  // Newest first so the freshest signal is in front.
  items.sort((a, b) => b.generated_at.localeCompare(a.generated_at));
  return items.slice(0, MAX_ROWS);
}

export function RecentDecisionsStrip() {
  const query = useQuery({
    queryKey: ["recent-decisions"],
    queryFn: async () => {
      const r = await apiClient.getSuggestionsGrid();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const flat = useMemo(() => flattenGrid(query.data ?? null), [query.data]);

  return (
    <section
      data-testid="recent-decisions-strip"
      aria-label="Recente suggesties"
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
      <h3
        style={{
          margin: "0 0 8px 0",
          fontSize: 14,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <span aria-hidden>📋</span>
        <span>Recente suggesties</span>
      </h3>

      {query.isLoading && (
        <p data-testid="recent-decisions-loading" style={{ color: "#6b7280" }}>
          Suggesties laden…
        </p>
      )}

      {!query.isLoading && query.data === null && (
        <p
          data-testid="recent-decisions-error"
          style={{ color: "#b91c1c", margin: 0 }}
        >
          Suggesties niet bereikbaar.
        </p>
      )}

      {!query.isLoading && flat.length === 0 && query.data !== null && (
        <p
          data-testid="recent-decisions-empty"
          style={{ color: "#6b7280", margin: 0 }}
        >
          Geen suggesties vandaag. De volgende ronde komt na de eerstvolgende
          morning chain.
        </p>
      )}

      {flat.length > 0 && (
        <ul
          data-testid="recent-decisions-list"
          style={{
            listStyle: "none",
            padding: 0,
            margin: 0,
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {flat.map((item) => (
            <li
              key={item.suggestion_id}
              data-testid={`recent-decisions-row-${item.suggestion_id}`}
              data-diff-status={item.diff_status}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                paddingBottom: 4,
              }}
            >
              <span
                aria-hidden
                style={{
                  display: "inline-block",
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: actionToneColour(item.action_label_nl),
                  flexShrink: 0,
                }}
              />
              <Link
                href="/suggesties"
                style={{
                  flexGrow: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  color: "inherit",
                  textDecoration: "none",
                  minWidth: 0,
                }}
                title={item.top_driver_nl ?? undefined}
              >
                <span
                  style={{
                    fontWeight: 600,
                    minWidth: 60,
                    color: "#111827",
                  }}
                >
                  {item.symbol}
                </span>
                <span
                  style={{
                    fontWeight: 500,
                    color: actionToneColour(item.action_label_nl),
                  }}
                >
                  {item.action_label_nl}
                </span>
                <span
                  style={{
                    color: "#6b7280",
                    fontSize: 12,
                    whiteSpace: "nowrap",
                  }}
                >
                  ({item.confidence_label_nl})
                </span>
              </Link>
              {item.diff_status !== "ongewijzigd" && (
                <span
                  style={{
                    fontSize: 11,
                    padding: "2px 6px",
                    borderRadius: 4,
                    background: chipBackground(item.diff_status),
                    color: "#1f2937",
                    flexShrink: 0,
                  }}
                >
                  {item.diff_status}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
