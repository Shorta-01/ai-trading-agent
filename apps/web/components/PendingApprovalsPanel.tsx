"use client";

/**
 * V1.2 §AF — "Te keuren bij IBKR" panel.
 *
 * Action drafts waiting for the operator's approval. Each row shows
 * symbol, side, order type, quantity, limit price, dry-run status
 * and a one-click link to the asset's approval screen. Read-only;
 * never promotes to a broker submission.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { EmptyState } from "@/components/EmptyState";
import {
  apiClient,
  type AssetActionDraftResponse,
  type LatestActionDraftsResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function dryRunTone(status: string): { bg: string; fg: string; label: string } {
  if (status === "passed")
    return { bg: "#dcfce7", fg: "#166534", label: "Dry-run geslaagd" };
  if (status === "failed")
    return { bg: "#fee2e2", fg: "#991b1b", label: "Dry-run mislukt" };
  return { bg: "#fef3c7", fg: "#854d0e", label: status };
}

function Row({ draft }: { draft: AssetActionDraftResponse }) {
  const tone = dryRunTone(draft.dry_run_status);
  return (
    <li
      data-testid={`pending-approval-row-${draft.draft_id}`}
      style={{
        listStyle: "none",
        padding: 8,
        marginBottom: 6,
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 6,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontWeight: 700, fontSize: 13 }}>{draft.symbol}</span>
        <span
          style={{
            fontSize: 11,
            background: "#e0e7ff",
            color: "#3730a3",
            padding: "1px 6px",
            borderRadius: 8,
          }}
        >
          {draft.action_side} {draft.order_type}/{draft.tif}
        </span>
        <span style={{ fontSize: 12, color: "#374151" }}>
          {draft.quantity} × {draft.limit_price}
        </span>
        <span
          data-testid={`pending-approval-row-${draft.draft_id}-dryrun`}
          style={{
            marginLeft: "auto",
            background: tone.bg,
            color: tone.fg,
            fontSize: 11,
            fontWeight: 600,
            padding: "2px 8px",
            borderRadius: 8,
          }}
        >
          {tone.label}
        </span>
      </div>
      <div
        style={{
          display: "flex",
          gap: 12,
          fontSize: 11,
          color: "#6b7280",
          marginTop: 4,
        }}
      >
        <span>Waarde: {draft.estimated_order_value ?? "—"}</span>
        <span>TOB: {draft.estimated_belgian_tob ?? "—"}</span>
        <span>
          Cash: {draft.estimated_cash_before ?? "—"} →{" "}
          {draft.estimated_cash_after ?? "—"}
        </span>
        <Link
          href="/ibkr-acties"
          style={{
            marginLeft: "auto",
            color: "#1d4ed8",
            textDecoration: "none",
            fontWeight: 600,
          }}
        >
          Naar keuren →
        </Link>
      </div>
    </li>
  );
}

export function PendingApprovalsPanel() {
  const query = useQuery({
    queryKey: ["pending-approvals-drafts"],
    queryFn: async (): Promise<LatestActionDraftsResponse | null> => {
      const r = await apiClient.getLatestActionDrafts();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const data = query.data ?? null;
  const items = (data?.items ?? []).filter(
    (d) => d.status !== "approved" && d.status !== "submitted",
  );

  return (
    <section
      data-testid="pending-approvals-panel"
      className="dashboard-panel"
      style={{ marginBottom: 12 }}
    >
      <div className="panel-head">
        <h2 style={{ margin: 0, fontSize: 16 }}>Te keuren bij IBKR</h2>
        <Link
          href="/ibkr-acties"
          style={{ fontSize: 12, color: "#1d4ed8", textDecoration: "none" }}
        >
          Alles bekijken →
        </Link>
      </div>
      {items.length === 0 ? (
        <EmptyState
          title="Geen acties te keuren"
          message="Wanneer de morning chain een draft schrijft die geslaagd is voor dry-run, verschijnt die hier."
        />
      ) : (
        <ul
          data-testid="pending-approvals-list"
          style={{ margin: 0, padding: 0 }}
        >
          {items.slice(0, 8).map((d) => (
            <Row key={d.draft_id} draft={d} />
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
