"use client";

/**
 * Task 133: Action Draft grid (Te keuren tab).
 *
 * Renders the list of action drafts in proposed / edited / user_approved
 * status for the configured account. Per-row actions: Goedkeuren,
 * Bewerken (inline edit), Dismiss, Verwijder. Approval requires the
 * user to type ``JA`` in a confirmation prompt (mode-neutral wording
 * per the Stage 3 lock — no "paper-order" vs "ECHTE order"
 * differentiation).
 *
 * After approval the row gets a green "Goedgekeurd" badge and the
 * locked Dutch info banner *"Goedgekeurd. IBKR-verzending wordt in
 * een toekomstige update toegevoegd."* — Task 134 will wire the real
 * submit; this task ends at user_approved.
 */

import { useState } from "react";

import { apiClient, type ActionDraftResponse } from "@/lib/apiClient";

import { ActionDraftEditForm } from "./ActionDraftEditForm";

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

const STATUS_COLOR: Record<
  ActionDraftResponse["status"],
  { bg: string; fg: string; label_nl: string }
> = {
  // Task 133 user-facing statuses (the only ones this grid renders;
  // the lifecycle statuses live in the Actief bij IBKR + Historiek
  // tabs via IbkrSubmissionGrids, but the record needs all 15 entries
  // to satisfy TypeScript's exhaustive Record check).
  proposed: { bg: "#dbeafe", fg: "#1e40af", label_nl: "Voorgesteld" },
  edited: { bg: "#fef3c7", fg: "#854d0e", label_nl: "Bewerkt" },
  user_approved: { bg: "#dcfce7", fg: "#166534", label_nl: "Goedgekeurd" },
  dismissed: { bg: "#fee2e2", fg: "#7f1d1d", label_nl: "Genegeerd" },
  deleted: { bg: "#e5e7eb", fg: "#374151", label_nl: "Verwijderd" },
  superseded: { bg: "#fde68a", fg: "#92400e", label_nl: "Verouderd" },
  // Task 134 lifecycle statuses — present for the typecheck even
  // though Te keuren never lists drafts in these states.
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

export function ActionDraftGrid({
  drafts,
  onChange,
}: {
  drafts: ActionDraftResponse[];
  onChange: () => void;
}) {
  if (drafts.length === 0) {
    return (
      <div
        data-testid="action-draft-grid-empty"
        style={{
          padding: 24,
          textAlign: "center",
          color: "#6b7280",
          border: "1px dashed #d1d5db",
          borderRadius: 8,
        }}
      >
        Geen actiedrafts om te keuren.
      </div>
    );
  }

  return (
    <div data-testid="action-draft-grid" style={{ display: "grid", gap: 12 }}>
      {drafts.map((draft) => (
        <ActionDraftRow
          key={draft.action_draft_id}
          draft={draft}
          onChange={onChange}
        />
      ))}
    </div>
  );
}

function ActionDraftRow({
  draft,
  onChange,
}: {
  draft: ActionDraftResponse;
  onChange: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const statusStyle = STATUS_COLOR[draft.status];
  const sideStyle = SIDE_COLOR[draft.side];
  const isPending = draft.status === "proposed" || draft.status === "edited";
  const isApproved = draft.status === "user_approved";
  const isSuperseded = draft.superseded_by_decision_package_id !== null;

  async function handleApprove() {
    const expectedToken = "JA";
    const typed = window.prompt(
      `Type JA om order voor ${draft.quantity}× ${draft.symbol} @ €${fmtDecimal(
        draft.limit_price_local,
        4,
      )} LMT (totaal €${fmtDecimal(draft.notional_eur)}) goed te keuren.`,
    );
    if (typed !== expectedToken) {
      setError("Goedkeuring geannuleerd. Type exact JA om door te gaan.");
      return;
    }
    setBusy("approving");
    setError(null);
    const result = await apiClient.approveActionDraft(draft.action_draft_id);
    setBusy(null);
    if (!result.ok) {
      setError(result.message || "Goedkeuren mislukt.");
      return;
    }
    onChange();
  }

  async function handleSubmitToPaper() {
    const expectedToken = "VERZEND";
    const typed = window.prompt(
      `Type VERZEND om de goedgekeurde order voor ${draft.quantity}× ${draft.symbol} @ €${fmtDecimal(
        draft.limit_price_local,
        4,
      )} LMT naar IBKR paper te verzenden.`,
    );
    if (typed !== expectedToken) {
      setError("Verzending geannuleerd. Type exact VERZEND om door te gaan.");
      return;
    }
    setBusy("submitting");
    setError(null);
    const result = await apiClient.submitActionDraftToPaper(
      draft.action_draft_id,
    );
    setBusy(null);
    if (!result.ok) {
      setError(result.message || "Verzending mislukt.");
      return;
    }
    if (result.data.blocking_reason) {
      setError(
        `Verzending geblokkeerd: ${result.data.blocking_reason} — ${
          result.data.help_nl || result.data.status_nl || ""
        }`,
      );
      return;
    }
    onChange();
  }

  async function handleDismiss() {
    const reason = window.prompt(
      "Optionele reden voor dismiss (mag leeg blijven):",
    );
    setBusy("dismissing");
    setError(null);
    const result = await apiClient.dismissActionDraft(
      draft.action_draft_id,
      reason || undefined,
    );
    setBusy(null);
    if (!result.ok) {
      setError(result.message || "Dismiss mislukt.");
      return;
    }
    onChange();
  }

  async function handleDelete() {
    const ok = window.confirm(
      "Weet je zeker dat je deze draft wil verwijderen?",
    );
    if (!ok) return;
    setBusy("deleting");
    setError(null);
    const result = await apiClient.deleteActionDraft(draft.action_draft_id);
    setBusy(null);
    if (!result.ok) {
      setError(result.message || "Verwijderen mislukt.");
      return;
    }
    onChange();
  }

  return (
    <article
      data-testid={`action-draft-row-${draft.action_draft_id}`}
      style={{
        border: "1px solid #d1d5db",
        borderRadius: 8,
        padding: 16,
        background: isApproved ? "#f0fdf4" : "#ffffff",
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
          <span
            data-testid={`action-draft-side-${draft.action_draft_id}`}
            style={{
              background: sideStyle.bg,
              color: sideStyle.fg,
              padding: "2px 10px",
              borderRadius: 4,
              fontSize: 13,
              fontWeight: 700,
            }}
          >
            {draft.side}
          </span>
          <span
            data-testid={`action-draft-status-${draft.action_draft_id}`}
            style={{
              background: statusStyle.bg,
              color: statusStyle.fg,
              padding: "2px 10px",
              borderRadius: 4,
              fontSize: 12,
              fontWeight: 700,
            }}
          >
            {statusStyle.label_nl}
          </span>
          {isSuperseded ? (
            <span
              data-testid={`action-draft-superseded-${draft.action_draft_id}`}
              style={{
                background: "#fde68a",
                color: "#92400e",
                padding: "2px 10px",
                borderRadius: 4,
                fontSize: 12,
                fontWeight: 700,
              }}
              title="Advies gewijzigd — er is een nieuwere Decision Package voor dit asset."
            >
              Advies gewijzigd
            </span>
          ) : null}
          {draft.submission_block_reason !== null ? (
            <span
              data-testid={`action-draft-block-reason-${draft.action_draft_id}`}
              style={{
                background: "#fecaca",
                color: "#7f1d1d",
                padding: "2px 10px",
                borderRadius: 4,
                fontSize: 12,
                fontWeight: 700,
              }}
              title={`Submission geblokkeerd: ${draft.submission_block_reason}`}
            >
              Blokkering: {draft.submission_block_reason}
            </span>
          ) : null}
        </div>
        <div style={{ fontSize: 12, color: "#6b7280" }}>
          {draft.exchange} · {draft.conid}
        </div>
      </header>

      {editing && isPending ? (
        <ActionDraftEditForm
          draft={draft}
          onCancel={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            onChange();
          }}
        />
      ) : (
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
          <dd
            data-testid={`action-draft-quantity-${draft.action_draft_id}`}
            style={{ margin: 0 }}
          >
            {fmtDecimal(draft.quantity, 0)}
          </dd>
          <dt style={{ fontWeight: 600 }}>Limietprijs</dt>
          <dd style={{ margin: 0 }}>
            {fmtDecimal(draft.limit_price_local, 4)} {draft.currency_local}{" "}
            (LMT, {draft.time_in_force})
          </dd>
          <dt style={{ fontWeight: 600 }}>Notional EUR</dt>
          <dd style={{ margin: 0 }}>€{fmtDecimal(draft.notional_eur)}</dd>
          <dt style={{ fontWeight: 600 }}>Gemaakt op</dt>
          <dd style={{ margin: 0, color: "#6b7280" }}>
            {fmtTs(draft.created_at)}
          </dd>
          {draft.user_note ? (
            <>
              <dt style={{ fontWeight: 600 }}>Notitie</dt>
              <dd style={{ margin: 0, color: "#374151" }}>{draft.user_note}</dd>
            </>
          ) : null}
        </dl>
      )}

      {isApproved ? (
        <div
          data-testid={`action-draft-approved-banner-${draft.action_draft_id}`}
          style={{
            marginTop: 16,
            padding: 12,
            background: "#dbeafe",
            color: "#1e40af",
            borderRadius: 6,
            fontSize: 13,
            display: "flex",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <span style={{ flex: 1 }}>
            Goedgekeurd. Klaar om naar IBKR paper te verzenden.
          </span>
          <button
            type="button"
            data-testid={`action-draft-submit-to-paper-${draft.action_draft_id}`}
            onClick={handleSubmitToPaper}
            disabled={busy !== null}
            style={{
              background: busy === "submitting" ? "#9ca3af" : "#1d4ed8",
              color: "#ffffff",
              border: "none",
              borderRadius: 6,
              padding: "6px 14px",
              fontSize: 13,
              fontWeight: 600,
              cursor: busy !== null ? "not-allowed" : "pointer",
            }}
          >
            {busy === "submitting"
              ? "Verzenden…"
              : "Verzend naar IBKR paper"}
          </button>
        </div>
      ) : null}

      {error ? (
        <div
          data-testid={`action-draft-error-${draft.action_draft_id}`}
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

      {isPending && !editing ? (
        <div
          style={{
            marginTop: 12,
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
          }}
        >
          <button
            type="button"
            data-testid={`action-draft-approve-${draft.action_draft_id}`}
            onClick={handleApprove}
            disabled={busy !== null}
            style={{
              padding: "8px 16px",
              background: "#15803d",
              color: "#ffffff",
              border: "none",
              borderRadius: 6,
              cursor: busy ? "wait" : "pointer",
              fontWeight: 600,
            }}
          >
            Goedkeuren
          </button>
          <button
            type="button"
            data-testid={`action-draft-edit-${draft.action_draft_id}`}
            onClick={() => setEditing(true)}
            disabled={busy !== null}
            style={{
              padding: "8px 16px",
              background: "#1d4ed8",
              color: "#ffffff",
              border: "none",
              borderRadius: 6,
              cursor: busy ? "wait" : "pointer",
            }}
          >
            Bewerken
          </button>
          <button
            type="button"
            data-testid={`action-draft-dismiss-${draft.action_draft_id}`}
            onClick={handleDismiss}
            disabled={busy !== null}
            style={{
              padding: "8px 16px",
              background: "#f59e0b",
              color: "#ffffff",
              border: "none",
              borderRadius: 6,
              cursor: busy ? "wait" : "pointer",
            }}
          >
            Dismiss
          </button>
          <button
            type="button"
            data-testid={`action-draft-delete-${draft.action_draft_id}`}
            onClick={handleDelete}
            disabled={busy !== null}
            style={{
              padding: "8px 16px",
              background: "#dc2626",
              color: "#ffffff",
              border: "none",
              borderRadius: 6,
              cursor: busy ? "wait" : "pointer",
            }}
          >
            Verwijder
          </button>
        </div>
      ) : null}
    </article>
  );
}
