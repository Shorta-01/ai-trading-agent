"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/apiClient";

/**
 * Today's action counter — anchor for the operator's workload.
 *
 * Renders three numbers at the top of the dashboard, in operator-
 * priority order:
 *
 *   * **Suggesties vandaag** — total + "X nieuw / Y gewijzigd" subline
 *     (read from ``/suggestions/grid``).
 *   * **Te keuren** — drafts in proposed / edited / user_approved
 *     status, i.e. the operator's TODO inbox
 *     (read from ``/action-draft/te-keuren``).
 *
 * Each card click-throughs to the relevant page. The widget never
 * blocks the dashboard: API failure renders a single Dutch "geen
 * data" line per card.
 */

const POLL_INTERVAL_MS = 60_000;

type CountTone = "neutral" | "attention" | "ok" | "loading";

function cardStyle(tone: CountTone): React.CSSProperties {
  const border =
    tone === "attention"
      ? "#f59e0b"
      : tone === "ok"
        ? "#16a34a"
        : "#e5e7eb";
  return {
    display: "flex",
    flexDirection: "column",
    gap: 4,
    padding: "10px 16px",
    borderRadius: 8,
    border: `1px solid ${border}`,
    background: "white",
    minWidth: 160,
    boxShadow: "0 1px 2px rgba(0, 0, 0, 0.04)",
    color: "inherit",
    textDecoration: "none",
    fontFamily:
      "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
  };
}

function bigNumber(value: number | string | null): React.ReactNode {
  return (
    <span style={{ fontSize: 24, fontWeight: 600, color: "#111827" }}>
      {value ?? "—"}
    </span>
  );
}

function smallLabel(text: string): React.ReactNode {
  return (
    <span style={{ fontSize: 12, color: "#6b7280" }}>{text}</span>
  );
}

export function TodaysActionsCounter() {
  const gridQuery = useQuery({
    queryKey: ["todays-actions", "suggestions-grid"],
    queryFn: async () => {
      const r = await apiClient.getSuggestionsGrid();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const draftsQuery = useQuery({
    queryKey: ["todays-actions", "drafts-te-keuren"],
    queryFn: async () => {
      const r = await apiClient.getActionDraftsTeKeuren();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const suggestionsTotal = gridQuery.data?.total_item_count ?? null;
  const suggestionsNew = gridQuery.data?.new_count ?? 0;
  const suggestionsChanged = gridQuery.data?.changed_count ?? 0;
  const draftsCount = draftsQuery.data?.drafts?.length ?? null;

  const suggestionsTone: CountTone = gridQuery.isLoading
    ? "loading"
    : suggestionsTotal && suggestionsTotal > 0
      ? "attention"
      : "neutral";
  const draftsTone: CountTone = draftsQuery.isLoading
    ? "loading"
    : draftsCount && draftsCount > 0
      ? "attention"
      : "ok";

  return (
    <section
      data-testid="todays-actions-counter"
      aria-label="Wat moet ik vandaag bekijken?"
      style={{
        display: "flex",
        gap: 12,
        flexWrap: "wrap",
        marginBottom: "0.75rem",
      }}
    >
      <Link
        href="/suggesties"
        data-testid="todays-actions-suggestions-card"
        data-tone={suggestionsTone}
        style={cardStyle(suggestionsTone)}
      >
        {smallLabel("Suggesties vandaag")}
        {bigNumber(suggestionsTotal)}
        <span style={{ fontSize: 11, color: "#6b7280" }}>
          {suggestionsNew} nieuw · {suggestionsChanged} gewijzigd
        </span>
      </Link>

      <Link
        href="/ibkr-acties"
        data-testid="todays-actions-drafts-card"
        data-tone={draftsTone}
        style={cardStyle(draftsTone)}
      >
        {smallLabel("Te keuren drafts")}
        {bigNumber(draftsCount)}
        <span style={{ fontSize: 11, color: "#6b7280" }}>
          {draftsCount && draftsCount > 0
            ? "Wachten op jouw beslissing."
            : "Geen actie nodig."}
        </span>
      </Link>
    </section>
  );
}
