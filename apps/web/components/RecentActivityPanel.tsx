"use client";

/**
 * V1.2 §AF — Recent activity panel.
 *
 * Last 24h of broker activity: executions/fills sorted newest first.
 * Empty state for a fresh setup. Pure read-only; this panel never
 * promotes anything.
 */

import { useQuery } from "@tanstack/react-query";

import { EmptyState } from "@/components/EmptyState";
import { apiClient, type IbkrExecutionSnapshot } from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;
const WINDOW_HOURS = 24;

function within24h(iso: string): boolean {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return false;
  return Date.now() - t <= WINDOW_HOURS * 3600 * 1000;
}

function Row({ exec }: { exec: IbkrExecutionSnapshot }) {
  const sideTone =
    exec.side.toUpperCase() === "BUY"
      ? { bg: "#dcfce7", fg: "#166534" }
      : { bg: "#fed7aa", fg: "#9a3412" };
  return (
    <li
      data-testid={`recent-activity-row-${exec.execution_id}`}
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
        fontSize: 12,
      }}
    >
      <span style={{ fontWeight: 700, minWidth: 64 }}>{exec.symbol}</span>
      <span
        style={{
          background: sideTone.bg,
          color: sideTone.fg,
          fontSize: 11,
          fontWeight: 600,
          padding: "1px 6px",
          borderRadius: 8,
        }}
      >
        {exec.side}
      </span>
      <span style={{ color: "#374151" }}>
        {exec.quantity} × {exec.price} {exec.currency}
      </span>
      <span style={{ marginLeft: "auto", color: "#9ca3af", fontSize: 11 }}>
        {exec.execution_time}
      </span>
    </li>
  );
}

export function RecentActivityPanel() {
  const query = useQuery({
    queryKey: ["recent-activity-panel"],
    queryFn: async (): Promise<IbkrExecutionSnapshot[]> => {
      const r = await apiClient.getIbkrExecutions();
      return r.ok ? (r.data.items ?? []) : [];
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const items = (query.data ?? [])
    .filter((e) => within24h(e.execution_time))
    .sort((a, b) => b.execution_time.localeCompare(a.execution_time));

  return (
    <section
      data-testid="recent-activity-panel"
      className="dashboard-panel"
      style={{ marginBottom: 12 }}
    >
      <div className="panel-head">
        <h2 style={{ margin: 0, fontSize: 16 }}>Recent gebeurd (24u)</h2>
        <span style={{ fontSize: 11, color: "#6b7280" }}>
          {items.length} fills
        </span>
      </div>
      {items.length === 0 ? (
        <EmptyState
          title="Geen fills in de laatste 24 uur"
          message="Uitvoeringen die door IBKR worden gerapporteerd verschijnen hier."
        />
      ) : (
        <ul style={{ margin: 0, padding: 0 }}>
          {items.slice(0, 8).map((e) => (
            <Row key={e.execution_id} exec={e} />
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
