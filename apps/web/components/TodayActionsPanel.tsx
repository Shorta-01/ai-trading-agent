"use client";

/**
 * V1.2 §AF — "Vandaag te doen" panel.
 *
 * Groups the latest suggestions by Dutch action label so the operator
 * sees in one glance what the doctrine recommends today: Kopen,
 * Verkopen, Houden, Bekijken. Each row shows symbol, confidence, and
 * a short rationale. Read-only: clicking routes to the asset's
 * decision-package detail page.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { EmptyState } from "@/components/EmptyState";
import {
  apiClient,
  type AssetSuggestionResponse,
  type LatestSuggestionsResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

const ACTION_ORDER = ["Kopen", "Verkopen", "Verminderen", "Bekijken", "Houden"];
const ACTION_TONE: Record<string, { bg: string; fg: string }> = {
  Kopen: { bg: "#dcfce7", fg: "#166534" },
  "Langzaam bijkopen": { bg: "#dcfce7", fg: "#166534" },
  Verkopen: { bg: "#fee2e2", fg: "#991b1b" },
  Verminderen: { bg: "#fed7aa", fg: "#9a3412" },
  Vermijden: { bg: "#fee2e2", fg: "#991b1b" },
  Bekijken: { bg: "#dbeafe", fg: "#1e3a8a" },
  Houden: { bg: "#e0e7ff", fg: "#3730a3" },
  Geblokkeerd: { bg: "#fee2e2", fg: "#991b1b" },
};

function bucketColor(action: string): { bg: string; fg: string } {
  return ACTION_TONE[action] ?? { bg: "#f3f4f6", fg: "#374151" };
}

function SuggestionLine({ item }: { item: AssetSuggestionResponse }) {
  return (
    <li
      data-testid={`today-actions-row-${item.symbol}`}
      style={{
        listStyle: "none",
        padding: "6px 8px",
        marginBottom: 4,
        borderRadius: 6,
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}
    >
      <span style={{ fontWeight: 700, fontSize: 13, minWidth: 64 }}>{item.symbol}</span>
      <span
        title={item.confidence_label_nl}
        style={{
          fontSize: 11,
          color: "#6b7280",
          background: "#f3f4f6",
          padding: "1px 6px",
          borderRadius: 8,
        }}
      >
        {item.confidence_label_nl}
      </span>
      <span style={{ fontSize: 12, color: "#374151", flex: 1 }} title={item.rationale_nl}>
        {item.rationale_nl.length > 60
          ? `${item.rationale_nl.slice(0, 60)}…`
          : item.rationale_nl}
      </span>
      <Link
        href={`/decision-package/${encodeURIComponent(item.suggestion_id)}`}
        style={{ fontSize: 11, color: "#1d4ed8", textDecoration: "none" }}
      >
        Detail →
      </Link>
    </li>
  );
}

function Bucket({
  action,
  items,
}: {
  action: string;
  items: AssetSuggestionResponse[];
}) {
  const tone = bucketColor(action);
  return (
    <div
      data-testid={`today-actions-bucket-${action}`}
      style={{
        background: "#f9fafb",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 10,
        minWidth: 0,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 6,
        }}
      >
        <span
          style={{
            background: tone.bg,
            color: tone.fg,
            fontWeight: 700,
            fontSize: 12,
            padding: "2px 10px",
            borderRadius: 10,
          }}
        >
          {action}
        </span>
        <span style={{ fontSize: 12, color: "#6b7280" }}>{items.length}</span>
      </div>
      {items.length === 0 ? (
        <p style={{ margin: 0, fontSize: 12, color: "#9ca3af" }}>—</p>
      ) : (
        <ul style={{ margin: 0, padding: 0 }}>
          {items.slice(0, 6).map((it) => (
            <SuggestionLine key={it.suggestion_id} item={it} />
          ))}
          {items.length > 6 ? (
            <li style={{ listStyle: "none", fontSize: 11, color: "#6b7280" }}>
              +{items.length - 6} meer…
            </li>
          ) : null}
        </ul>
      )}
    </div>
  );
}

export function TodayActionsPanel() {
  const query = useQuery({
    queryKey: ["today-actions-suggestions"],
    queryFn: async (): Promise<LatestSuggestionsResponse | null> => {
      const r = await apiClient.getLatestSuggestions();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const data = query.data ?? null;
  const items = data?.items ?? [];

  const buckets = new Map<string, AssetSuggestionResponse[]>();
  for (const action of ACTION_ORDER) buckets.set(action, []);
  for (const it of items) {
    const action = it.action_label_nl || "Bekijken";
    if (!buckets.has(action)) buckets.set(action, []);
    buckets.get(action)!.push(it);
  }
  const visibleBuckets = Array.from(buckets.entries()).filter(
    ([, arr]) => arr.length > 0,
  );

  return (
    <section
      data-testid="today-actions-panel"
      className="dashboard-panel"
      style={{ marginBottom: 12 }}
    >
      <div className="panel-head">
        <h2 style={{ margin: 0, fontSize: 16 }}>Vandaag te doen</h2>
        <span style={{ fontSize: 11, color: "#6b7280" }}>
          {items.length} suggesties uit de morning chain
        </span>
      </div>
      {items.length === 0 ? (
        <EmptyState
          title="Nog geen suggesties vandaag"
          message="De morning chain heeft nog geen suggesties geschreven. Eerst de 07:00 briefing afwachten."
        />
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${Math.min(visibleBuckets.length, 4)}, minmax(0, 1fr))`,
            gap: 10,
          }}
          data-testid="today-actions-grid"
        >
          {visibleBuckets.map(([action, arr]) => (
            <Bucket key={action} action={action} items={arr} />
          ))}
        </div>
      )}
    </section>
  );
}
