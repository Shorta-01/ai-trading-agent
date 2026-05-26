"use client";

/**
 * Task 134c: Actief-bij-IBKR + Historiek grids.
 *
 * Per the brainstorm-locked tab structure (Te keuren / Actief bij
 * IBKR / Historiek):
 *
 * * ``ActiefBijIbkrGrid`` shows drafts in any in-flight status with a
 *   Cancel button per row and a clickable area that opens the
 *   ``SubmissionLifecycleDrawer``. Cancel routes through
 *   ``POST /action-draft/{id}/cancel-submitted`` which transitions
 *   the draft to ``pending_cancellation``; the worker handles the
 *   actual ``ib.cancelOrder()`` on its next sweep tick.
 * * ``HistoriekGrid`` is read-only — terminal drafts only, with the
 *   lifecycle drawer accessible from each row.
 */

import { useState } from "react";

import {
  apiClient,
  type ActionDraftResponse,
  type ActionDraftStatus,
} from "@/lib/apiClient";

const STATUS_BADGE: Record<
  ActionDraftStatus,
  { bg: string; fg: string; label_nl: string }
> = {
  proposed: { bg: "#dbeafe", fg: "#1e40af", label_nl: "Voorgesteld" },
  edited: { bg: "#fef3c7", fg: "#854d0e", label_nl: "Bewerkt" },
  user_approved: { bg: "#dcfce7", fg: "#166534", label_nl: "Goedgekeurd" },
  dismissed: { bg: "#fee2e2", fg: "#7f1d1d", label_nl: "Genegeerd" },
  deleted: { bg: "#e5e7eb", fg: "#374151", label_nl: "Verwijderd" },
  superseded: { bg: "#fde68a", fg: "#92400e", label_nl: "Verouderd" },
  submitted: { bg: "#dbeafe", fg: "#1e3a8a", label_nl: "Verstuurd" },
  accepted: { bg: "#bfdbfe", fg: "#1e40af", label_nl: "Geaccepteerd" },
  working: { bg: "#bae6fd", fg: "#075985", label_nl: "Actief" },
  partially_filled: {
    bg: "#fde68a",
    fg: "#92400e",
    label_nl: "Gedeeltelijk uitgevoerd",
  },
  filled: { bg: "#dcfce7", fg: "#166534", label_nl: "Uitgevoerd" },
  cancelled: { bg: "#e5e7eb", fg: "#374151", label_nl: "Geannuleerd" },
  rejected: { bg: "#fecaca", fg: "#7f1d1d", label_nl: "Geweigerd" },
  pending_cancellation: {
    bg: "#fef3c7",
    fg: "#854d0e",
    label_nl: "Annulering aangevraagd",
  },
  awaiting_reply_timeout: {
    bg: "#fde68a",
    fg: "#92400e",
    label_nl: "Wacht op IBKR-bevestiging",
  },
};

const SIDE_COLOR: Record<
  ActionDraftResponse["side"],
  { bg: string; fg: string }
> = {
  BUY: { bg: "#dcfce7", fg: "#166534" },
  SELL: { bg: "#fecaca", fg: "#7f1d1d" },
};

function fmtTs(value: string | null): string {
  if (value === null) return "—";
  return value.slice(0, 19).replace("T", " ");
}

function fmtDecimal(value: string, decimals = 2): string {
  const num = Number(value);
  if (Number.isNaN(num)) return value;
  return num.toLocaleString("nl-BE", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function StatusBadge({ status }: { status: ActionDraftStatus }) {
  const style = STATUS_BADGE[status];
  return (
    <span
      data-testid={`ibkr-grid-status-${status}`}
      style={{
        background: style.bg,
        color: style.fg,
        padding: "2px 10px",
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 700,
      }}
    >
      {style.label_nl}
    </span>
  );
}

function SideBadge({ side }: { side: ActionDraftResponse["side"] }) {
  const style = SIDE_COLOR[side];
  return (
    <span
      style={{
        background: style.bg,
        color: style.fg,
        padding: "2px 10px",
        borderRadius: 4,
        fontSize: 13,
        fontWeight: 700,
      }}
    >
      {side}
    </span>
  );
}

// ---------------------------------------------------------------------
// Actief bij IBKR.
// ---------------------------------------------------------------------

export function ActiefBijIbkrGrid({
  drafts,
  onChange,
  onOpenLifecycle,
}: {
  drafts: ActionDraftResponse[];
  onChange: () => void;
  onOpenLifecycle: (actionDraftId: string) => void;
}) {
  if (drafts.length === 0) {
    return (
      <div
        data-testid="ibkr-actief-grid-empty"
        style={{
          padding: 24,
          textAlign: "center",
          color: "#6b7280",
          border: "1px dashed #d1d5db",
          borderRadius: 8,
        }}
      >
        Geen actieve IBKR-orders.
      </div>
    );
  }
  return (
    <div data-testid="ibkr-actief-grid" style={{ display: "grid", gap: 12 }}>
      {drafts.map((draft) => (
        <ActiefBijIbkrRow
          key={draft.action_draft_id}
          draft={draft}
          onChange={onChange}
          onOpenLifecycle={onOpenLifecycle}
        />
      ))}
    </div>
  );
}

function ActiefBijIbkrRow({
  draft,
  onChange,
  onOpenLifecycle,
}: {
  draft: ActionDraftResponse;
  onChange: () => void;
  onOpenLifecycle: (id: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cancellable =
    draft.status === "submitted" ||
    draft.status === "accepted" ||
    draft.status === "working" ||
    draft.status === "partially_filled";

  async function handleCancel() {
    const ok = window.confirm(
      `Order voor ${draft.quantity}× ${draft.symbol} annuleren?`,
    );
    if (!ok) return;
    setBusy(true);
    setError(null);
    const result = await apiClient.cancelSubmittedActionDraft(
      draft.action_draft_id,
    );
    setBusy(false);
    if (!result.ok) {
      setError(result.message || "Annulering mislukt.");
      return;
    }
    onChange();
  }

  return (
    <article
      data-testid={`ibkr-actief-row-${draft.action_draft_id}`}
      style={{
        border: "1px solid #d1d5db",
        borderRadius: 8,
        padding: 16,
        background: "#ffffff",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h3 style={{ margin: 0, fontSize: 18 }}>{draft.symbol}</h3>
          <SideBadge side={draft.side} />
          <StatusBadge status={draft.status} />
        </div>
        <button
          type="button"
          data-testid={`ibkr-actief-lifecycle-${draft.action_draft_id}`}
          onClick={() => onOpenLifecycle(draft.action_draft_id)}
          style={{
            padding: "6px 12px",
            background: "#e5e7eb",
            color: "#111827",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
            fontSize: 12,
          }}
        >
          Lifecycle
        </button>
      </header>
      <dl
        style={{
          display: "grid",
          gridTemplateColumns: "max-content 1fr",
          gap: "4px 16px",
          margin: 0,
          fontSize: 14,
        }}
      >
        <dt style={{ fontWeight: 600 }}>Aantal</dt>
        <dd style={{ margin: 0 }}>{fmtDecimal(draft.quantity, 0)}</dd>
        <dt style={{ fontWeight: 600 }}>Limietprijs</dt>
        <dd style={{ margin: 0 }}>
          {fmtDecimal(draft.limit_price_local, 4)} {draft.currency_local}
        </dd>
        <dt style={{ fontWeight: 600 }}>Notional EUR</dt>
        <dd style={{ margin: 0 }}>€{fmtDecimal(draft.notional_eur)}</dd>
        <dt style={{ fontWeight: 600 }}>Verstuurd op</dt>
        <dd style={{ margin: 0, color: "#6b7280" }}>
          {fmtTs(draft.submission_started_at)}
        </dd>
      </dl>

      {error ? (
        <div
          data-testid={`ibkr-actief-error-${draft.action_draft_id}`}
          style={{
            marginTop: 12,
            color: "#7f1d1d",
            background: "#fee2e2",
            padding: 8,
            borderRadius: 4,
            fontSize: 13,
          }}
        >
          {error}
        </div>
      ) : null}

      {cancellable ? (
        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <button
            type="button"
            data-testid={`ibkr-actief-cancel-${draft.action_draft_id}`}
            onClick={handleCancel}
            disabled={busy}
            style={{
              padding: "8px 16px",
              background: "#dc2626",
              color: "#ffffff",
              border: "none",
              borderRadius: 6,
              cursor: busy ? "wait" : "pointer",
              fontWeight: 600,
            }}
          >
            {busy ? "Bezig…" : "Annuleer"}
          </button>
        </div>
      ) : null}
    </article>
  );
}

// ---------------------------------------------------------------------
// Historiek.
// ---------------------------------------------------------------------

export function HistoriekGrid({
  drafts,
  onOpenLifecycle,
}: {
  drafts: ActionDraftResponse[];
  onOpenLifecycle: (actionDraftId: string) => void;
}) {
  if (drafts.length === 0) {
    return (
      <div
        data-testid="ibkr-historiek-grid-empty"
        style={{
          padding: 24,
          textAlign: "center",
          color: "#6b7280",
          border: "1px dashed #d1d5db",
          borderRadius: 8,
        }}
      >
        Geen afgeronde orders.
      </div>
    );
  }
  return (
    <div data-testid="ibkr-historiek-grid" style={{ display: "grid", gap: 12 }}>
      {drafts.map((draft) => (
        <HistoriekRow
          key={draft.action_draft_id}
          draft={draft}
          onOpenLifecycle={onOpenLifecycle}
        />
      ))}
    </div>
  );
}

function HistoriekRow({
  draft,
  onOpenLifecycle,
}: {
  draft: ActionDraftResponse;
  onOpenLifecycle: (id: string) => void;
}) {
  return (
    <article
      data-testid={`ibkr-historiek-row-${draft.action_draft_id}`}
      style={{
        border: "1px solid #d1d5db",
        borderRadius: 8,
        padding: 16,
        background: "#f9fafb",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h3 style={{ margin: 0, fontSize: 18 }}>{draft.symbol}</h3>
          <SideBadge side={draft.side} />
          <StatusBadge status={draft.status} />
        </div>
        <button
          type="button"
          data-testid={`ibkr-historiek-lifecycle-${draft.action_draft_id}`}
          onClick={() => onOpenLifecycle(draft.action_draft_id)}
          style={{
            padding: "6px 12px",
            background: "#e5e7eb",
            color: "#111827",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
            fontSize: 12,
          }}
        >
          Lifecycle
        </button>
      </header>
      <dl
        style={{
          display: "grid",
          gridTemplateColumns: "max-content 1fr",
          gap: "4px 16px",
          margin: 0,
          fontSize: 14,
        }}
      >
        <dt style={{ fontWeight: 600 }}>Aantal</dt>
        <dd style={{ margin: 0 }}>{fmtDecimal(draft.quantity, 0)}</dd>
        <dt style={{ fontWeight: 600 }}>Limietprijs</dt>
        <dd style={{ margin: 0 }}>
          {fmtDecimal(draft.limit_price_local, 4)} {draft.currency_local}
        </dd>
        <dt style={{ fontWeight: 600 }}>Notional EUR</dt>
        <dd style={{ margin: 0 }}>€{fmtDecimal(draft.notional_eur)}</dd>
        <dt style={{ fontWeight: 600 }}>Afgesloten op</dt>
        <dd style={{ margin: 0, color: "#6b7280" }}>
          {fmtTs(draft.terminal_state_at)}
        </dd>
      </dl>
    </article>
  );
}
