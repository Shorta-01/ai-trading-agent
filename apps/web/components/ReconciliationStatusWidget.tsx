"use client";

/**
 * Task 135b: Dashboard reconciliation status widget.
 *
 * Compact card showing the current reconciler state. Polls
 * ``/reconciliation/status`` every 60s. Surfaces the latest run mode,
 * the per-pass divergence counts in the last 24h, and the count of
 * pending manual-review queue items + unresolved unmatched
 * executions.
 *
 * Clicking the card routes to ``/admin/reconciliation`` for full
 * triage. Informational only — gates no action; ``safe_for_*`` stays
 * False.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import {
  apiClient,
  type ReconciliationStatusResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

const MODE_LABELS: Record<string, string> = {
  completed: "Voltooid",
  skipped_locked: "Overgeslagen (vergrendeld)",
  skipped_disconnected: "Overgeslagen (geen verbinding)",
  error: "Fout",
};

const MODE_COLORS: Record<string, { bg: string; fg: string }> = {
  completed: { bg: "#dcfce7", fg: "#166534" },
  skipped_locked: { bg: "#e5e7eb", fg: "#374151" },
  skipped_disconnected: { bg: "#fef3c7", fg: "#854d0e" },
  error: { bg: "#fecaca", fg: "#7f1d1d" },
};


export function ReconciliationStatusWidget() {
  const query = useQuery({
    queryKey: ["reconciliation-status"],
    queryFn: async (): Promise<ReconciliationStatusResponse | null> => {
      const result = await apiClient.getReconciliationStatus();
      return result.ok ? result.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const data = query.data ?? null;

  if (data === null) {
    return null;
  }

  const latestMode = data.latest_run?.mode_detected;
  const modeColors =
    latestMode !== undefined && MODE_COLORS[latestMode] !== undefined
      ? MODE_COLORS[latestMode]
      : { bg: "#e5e7eb", fg: "#374151" };
  const modeLabel =
    latestMode !== undefined && MODE_LABELS[latestMode] !== undefined
      ? MODE_LABELS[latestMode]
      : "Onbekend";

  return (
    <Link
      href="/admin/reconciliation"
      data-testid="reconciliation-status-widget"
      style={{
        display: "block",
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 16,
        marginBottom: 12,
        textDecoration: "none",
        color: "inherit",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: 14,
            fontWeight: 700,
            color: "#1f2937",
          }}
        >
          IBKR-reconciliatie
        </h3>
        {data.latest_run === null ? (
          <span
            data-testid="reconciliation-no-runs"
            style={{ fontSize: 12, color: "#6b7280" }}
          >
            Nog geen runs
          </span>
        ) : (
          <span
            data-testid="reconciliation-mode-badge"
            style={{
              background: modeColors.bg,
              color: modeColors.fg,
              padding: "2px 8px",
              borderRadius: 999,
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            {modeLabel}
          </span>
        )}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 8,
          fontSize: 12,
        }}
      >
        <Metric
          label="Hersteld (24u)"
          value={data.drafts_healed_last_24h}
          testId="reconciliation-healed-24h"
        />
        <Metric
          label="Wacht op review"
          value={data.pending_manual_review_count}
          testId="reconciliation-pending-review"
          warn={data.pending_manual_review_count > 0}
        />
        <Metric
          label="Onbekende fills"
          value={data.unresolved_unmatched_count}
          testId="reconciliation-unmatched"
          warn={data.unresolved_unmatched_count > 0}
        />
      </div>
    </Link>
  );
}


function Metric({
  label,
  value,
  testId,
  warn = false,
}: {
  label: string;
  value: number;
  testId: string;
  warn?: boolean;
}) {
  return (
    <div>
      <div
        data-testid={`${testId}-value`}
        style={{
          fontSize: 18,
          fontWeight: 700,
          color: warn && value > 0 ? "#b45309" : "#1f2937",
        }}
      >
        {value}
      </div>
      <div style={{ color: "#6b7280" }}>{label}</div>
    </div>
  );
}
