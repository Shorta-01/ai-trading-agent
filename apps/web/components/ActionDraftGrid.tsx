"use client";

/**
 * V1.2 §AT — 3-stage action-draft workflow.
 *
 * Restructures the action-draft surface into the doctrine's three
 * stages (CLAUDE.md §8):
 *
 *   1. "Voorstellen vandaag" (proposed / edited) — per voorstel:
 *      Goedkeuren / Aanpassen (aantal + limietprijs) / Afwijzen.
 *   2. "Te verzenden naar IBKR" (user_approved) — nog bewerkbaar;
 *      per regel "Verwijder uit lijst" + één grote knop bovenaan
 *      "Verzend alle X orders naar IBKR paper".
 *   3. Verzonden orders leven in de Actief/Historiek tabs.
 *
 * Approval en verzending gebeuren via knop + bevestigingsmodal
 * (Ja/Nee) — geen JA/VERZEND typen meer. De edit-velden voor aantal
 * + limietprijs zijn beschikbaar in beide stages via de "Aanpassen"
 * knop die de inline ``ActionDraftEditForm`` opent.
 */

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  apiClient,
  type ActionDraftResponse,
  type IbkrAccountModeResponse,
} from "@/lib/apiClient";
import {
  computeEurEquivalent,
  computeFxSensitivity,
  formatEurDetail,
  TARGET_GROSS_PCT,
  TOB_ROUND_TRIP_PCT,
} from "@/lib/eurEquivalent";

import { ActionDraftEditForm } from "./ActionDraftEditForm";
import { ConfirmModal } from "./ConfirmModal";

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
  proposed: { bg: "#dbeafe", fg: "#1e40af", label_nl: "Voorgesteld" },
  edited: { bg: "#fef3c7", fg: "#854d0e", label_nl: "Bewerkt" },
  user_approved: { bg: "#dcfce7", fg: "#166534", label_nl: "Goedgekeurd" },
  dismissed: { bg: "#fee2e2", fg: "#7f1d1d", label_nl: "Genegeerd" },
  deleted: { bg: "#f3f4f6", fg: "#6b7280", label_nl: "Verwijderd" },
  superseded: { bg: "#fde68a", fg: "#92400e", label_nl: "Vervangen" },
  submitted: { bg: "#e0e7ff", fg: "#3730a3", label_nl: "Verzonden" },
  accepted: { bg: "#e0e7ff", fg: "#3730a3", label_nl: "Geaccepteerd" },
  working: { bg: "#e0e7ff", fg: "#3730a3", label_nl: "Actief" },
  partially_filled: { bg: "#e0e7ff", fg: "#3730a3", label_nl: "Deels gevuld" },
  filled: { bg: "#dcfce7", fg: "#166534", label_nl: "Gevuld" },
  cancelled: { bg: "#fee2e2", fg: "#7f1d1d", label_nl: "Geannuleerd" },
  rejected: { bg: "#fee2e2", fg: "#7f1d1d", label_nl: "Afgewezen" },
  pending_cancellation: { bg: "#fef3c7", fg: "#854d0e", label_nl: "Annulering bezig" },
  awaiting_reply_timeout: { bg: "#fee2e2", fg: "#7f1d1d", label_nl: "Timeout" },
};

const SIDE_COLOR: Record<ActionDraftResponse["side"], { bg: string; fg: string }> = {
  BUY: { bg: "#dcfce7", fg: "#166534" },
  SELL: { bg: "#fee2e2", fg: "#7f1d1d" },
};

// ---------------------------------------------------------------------------
// EUR-equivalent transparency (V1.2 §AV / CLAUDE.md §6.1).
// ---------------------------------------------------------------------------

function EurEquivalentBlock({ draft }: { draft: ActionDraftResponse }) {
  // The doctrine only sizes BUYs; SELLs already realise the +4% target
  // so the transparency block doesn't add anything there.
  if (draft.side !== "BUY") return null;
  const eq = computeEurEquivalent(draft.notional_eur);
  if (eq.gross_eur <= 0) return null;
  const fxRows = computeFxSensitivity(
    draft.notional_eur,
    draft.fx_rate_at_creation,
    draft.currency_local,
  );
  return (
    <div
      data-testid={`action-draft-eur-equivalent-${draft.action_draft_id}`}
      style={{
        marginTop: 12,
        padding: 10,
        background: "#f0fdf4",
        border: "1px solid #bbf7d0",
        borderRadius: 6,
        fontSize: 12,
      }}
    >
      <div style={{ fontWeight: 600, color: "#166534", marginBottom: 4 }}>
        EUR-equivalent op +{TARGET_GROSS_PCT}% (na TOB {TOB_ROUND_TRIP_PCT}%
        round-trip)
      </div>
      <div
        data-testid={`action-draft-eur-equivalent-net-${draft.action_draft_id}`}
        style={{ color: "#14532d" }}
      >
        Bruto {formatEurDetail(eq.gross_eur)} · TOB
        {" −"}
        {formatEurDetail(eq.tob_eur)} · <strong>Netto {formatEurDetail(eq.net_eur)}</strong>
      </div>
      {fxRows.length > 0 ? (
        <ul
          data-testid={`action-draft-fx-sensitivity-${draft.action_draft_id}`}
          style={{
            margin: "6px 0 0",
            padding: 0,
            listStyle: "none",
            color: "#374151",
          }}
        >
          {fxRows.map((row, idx) => (
            <li
              key={`fx-${idx}`}
              data-testid={`action-draft-fx-row-${draft.action_draft_id}-${idx}`}
              style={{ display: "flex", justifyContent: "space-between" }}
            >
              <span>{row.scenario_nl}</span>
              <span style={{ fontWeight: 600 }}>
                {formatEurDetail(row.net_eur)}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Per-draft row.
// ---------------------------------------------------------------------------

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
  const [approveModal, setApproveModal] = useState(false);
  const [submitModal, setSubmitModal] = useState(false);

  const statusStyle = STATUS_COLOR[draft.status];
  const sideStyle = SIDE_COLOR[draft.side];
  const isPending = draft.status === "proposed" || draft.status === "edited";
  const isApproved = draft.status === "user_approved";
  const isSuperseded = draft.superseded_by_decision_package_id !== null;

  async function confirmApprove() {
    setBusy("approving");
    setError(null);
    const result = await apiClient.approveActionDraft(draft.action_draft_id);
    setBusy(null);
    setApproveModal(false);
    if (!result.ok) {
      setError(result.message || "Goedkeuren mislukt.");
      return;
    }
    onChange();
  }

  async function confirmSubmit() {
    setBusy("submitting");
    setError(null);
    const result = await apiClient.submitActionDraftToPaper(
      draft.action_draft_id,
    );
    setBusy(null);
    setSubmitModal(false);
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
      "Optionele reden voor afwijzen (mag leeg blijven):",
    );
    setBusy("dismissing");
    setError(null);
    const result = await apiClient.dismissActionDraft(
      draft.action_draft_id,
      reason || undefined,
    );
    setBusy(null);
    if (!result.ok) {
      setError(result.message || "Afwijzen mislukt.");
      return;
    }
    onChange();
  }

  async function handleDelete() {
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

      {editing ? (
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

      {editing ? null : <EurEquivalentBlock draft={draft} />}

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

      {/* Stage 1 — Voorstellen: Goedkeuren / Aanpassen / Afwijzen. */}
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
            onClick={() => setApproveModal(true)}
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
            Aanpassen
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
            Afwijzen
          </button>
        </div>
      ) : null}

      {/* Stage 2 — Te verzenden: nog bewerkbaar + verwijder uit lijst. */}
      {isApproved && !editing ? (
        <div
          data-testid={`action-draft-approved-banner-${draft.action_draft_id}`}
          style={{
            marginTop: 12,
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: 13, color: "#166534", flex: 1 }}>
            Goedgekeurd — klaar om te verzenden. Nog bewerkbaar.
          </span>
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
            Aanpassen
          </button>
          <button
            type="button"
            data-testid={`action-draft-submit-to-paper-${draft.action_draft_id}`}
            onClick={() => setSubmitModal(true)}
            disabled={busy !== null}
            style={{
              background: "#1d4ed8",
              color: "#ffffff",
              border: "none",
              borderRadius: 6,
              padding: "8px 16px",
              fontWeight: 600,
              cursor: busy !== null ? "not-allowed" : "pointer",
            }}
          >
            Verzend naar IBKR paper
          </button>
          <button
            type="button"
            data-testid={`action-draft-remove-from-list-${draft.action_draft_id}`}
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
            Verwijder uit lijst
          </button>
        </div>
      ) : null}

      <ConfirmModal
        open={approveModal}
        testId={`action-draft-approve-modal-${draft.action_draft_id}`}
        title="Order goedkeuren?"
        body={
          <>
            Keur je de order voor{" "}
            <strong>
              {fmtDecimal(draft.quantity, 0)}× {draft.symbol}
            </strong>{" "}
            @ €{fmtDecimal(draft.limit_price_local, 4)} LMT (totaal €
            {fmtDecimal(draft.notional_eur)}) goed? De order gaat hierna naar
            je &quot;Te verzenden&quot;-lijst — nog niet naar IBKR.
          </>
        }
        confirmLabel="Ja, goedkeuren"
        busy={busy === "approving"}
        onConfirm={confirmApprove}
        onCancel={() => setApproveModal(false)}
      />

      <ConfirmModal
        open={submitModal}
        testId={`action-draft-submit-modal-${draft.action_draft_id}`}
        title="Verzenden naar IBKR paper?"
        body={
          <>
            Verzend de goedgekeurde order voor{" "}
            <strong>
              {fmtDecimal(draft.quantity, 0)}× {draft.symbol}
            </strong>{" "}
            @ €{fmtDecimal(draft.limit_price_local, 4)} LMT naar IBKR paper?
            Dit plaatst het order bij de broker.
          </>
        }
        confirmLabel="Ja, verzend"
        busy={busy === "submitting"}
        onConfirm={confirmSubmit}
        onCancel={() => setSubmitModal(false)}
      />
    </article>
  );
}

// ---------------------------------------------------------------------------
// Bulk-submit header for the "Te verzenden" stage.
// ---------------------------------------------------------------------------

function BulkSubmitBar({
  approvedDrafts,
  onChange,
}: {
  approvedDrafts: ActionDraftResponse[];
  onChange: () => void;
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);

  // V1.2 §BZ vervolg: detect of de geconfigureerde IBKR-sessie tegen
  // een live-account verbonden is. ``useQuery`` met dezelfde queryKey
  // als ``/portefeuille`` zodat React Query de fetch dedup't.
  const accountModeQuery = useQuery({
    queryKey: ["portefeuille-account-mode"],
    queryFn: async (): Promise<IbkrAccountModeResponse | null> => {
      const res = await apiClient.getIbkrAccountMode();
      return res.ok ? res.data : null;
    },
  });
  const accountMode = accountModeQuery.data ?? null;
  const isLiveAccount = accountMode?.mode === "live";

  const totalEur = approvedDrafts.reduce(
    (sum, d) => sum + Number(d.notional_eur || 0),
    0,
  );

  async function confirmBulkSubmit() {
    setBusy(true);
    setError(null);
    let ok = 0;
    let blocked = 0;
    const failures: string[] = [];
    for (const draft of approvedDrafts) {
      const result = await apiClient.submitActionDraftToPaper(
        draft.action_draft_id,
      );
      if (!result.ok) {
        failures.push(`${draft.symbol}: ${result.message ?? "request_failed"}`);
        continue;
      }
      if (result.data.blocking_reason) {
        blocked += 1;
        failures.push(`${draft.symbol}: ${result.data.blocking_reason}`);
        continue;
      }
      ok += 1;
    }
    setBusy(false);
    setModalOpen(false);
    const pieces = [`${ok} verzonden`];
    if (blocked > 0) pieces.push(`${blocked} geblokkeerd`);
    if (failures.length > 0) {
      setError(`Niet alles gelukt: ${failures.join("; ")}`);
    }
    setSummary(pieces.join(", "));
    onChange();
  }

  if (approvedDrafts.length === 0) return null;

  return (
    <div
      data-testid="action-draft-bulk-submit-bar"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        background: "#ecfdf5",
        border: "1px solid #6ee7b7",
        borderRadius: 8,
        padding: "10px 14px",
        flexWrap: "wrap",
      }}
    >
      <span style={{ fontWeight: 600, color: "#065f46", flex: 1 }}>
        {approvedDrafts.length} order
        {approvedDrafts.length === 1 ? "" : "s"} klaar om te verzenden — totaal €
        {totalEur.toLocaleString("nl-BE", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}
      </span>
      {summary ? (
        <span
          data-testid="action-draft-bulk-submit-summary"
          style={{ fontSize: 13, color: "#065f46" }}
        >
          {summary}
        </span>
      ) : null}
      <button
        type="button"
        data-testid="action-draft-bulk-submit-button"
        onClick={() => setModalOpen(true)}
        disabled={busy}
        data-account-mode={accountMode?.mode ?? "unknown"}
        style={{
          background: busy
            ? "#9ca3af"
            : isLiveAccount
              ? "#b91c1c"
              : "#15803d",
          color: "#ffffff",
          border: "none",
          borderRadius: 6,
          padding: "10px 18px",
          fontWeight: 700,
          fontSize: 14,
          cursor: busy ? "not-allowed" : "pointer",
        }}
      >
        {isLiveAccount
          ? `⚠️ Verzend alle ${approvedDrafts.length} orders naar IBKR LIVE`
          : `Verzend alle ${approvedDrafts.length} orders naar IBKR`}
      </button>
      {error ? (
        <div
          data-testid="action-draft-bulk-submit-error"
          style={{
            width: "100%",
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

      <ConfirmModal
        open={modalOpen}
        testId="action-draft-bulk-submit-modal"
        title={
          isLiveAccount
            ? "⚠️ Alle orders verzenden naar IBKR LIVE — echt geld"
            : "Alle orders verzenden naar IBKR?"
        }
        body={
          <>
            {isLiveAccount ? (
              <div
                data-testid="action-draft-bulk-submit-live-warning"
                role="alert"
                style={{
                  background: "#fef2f2",
                  border: "2px solid #b91c1c",
                  color: "#7f1d1d",
                  padding: "10px 12px",
                  borderRadius: 6,
                  marginBottom: 12,
                  fontSize: 13,
                  lineHeight: 1.4,
                }}
              >
                <strong style={{ display: "block", marginBottom: 4 }}>
                  Je verbindt met een LIVE IBKR-account
                  {accountMode?.actual_account_id_masked
                    ? ` (${accountMode.actual_account_id_masked})`
                    : ""}
                  .
                </strong>
                Deze orders gaan met ECHT geld naar de markt. Controleer
                aantal, limit-prijs en symbool nog éénmaal voor je
                bevestigt — dit is niet ongedaan te maken.
              </div>
            ) : null}
            <p style={{ margin: "0 0 10px" }}>
              Je staat op het punt{" "}
              <strong>{approvedDrafts.length} orders</strong> te verzenden naar
              IBKR{isLiveAccount ? " LIVE" : ""}, totaal{" "}
              <strong>
                €
                {totalEur.toLocaleString("nl-BE", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </strong>
              .
            </p>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
              {approvedDrafts.map((d) => (
                <li key={d.action_draft_id}>
                  {d.side} {fmtDecimal(d.quantity, 0)}× {d.symbol} @ €
                  {fmtDecimal(d.limit_price_local, 4)} (€
                  {fmtDecimal(d.notional_eur)})
                </li>
              ))}
            </ul>
          </>
        }
        confirmLabel={
          isLiveAccount
            ? `Ja, ${approvedDrafts.length} LIVE orders verzenden`
            : `Ja, verzend ${approvedDrafts.length} orders`
        }
        busy={busy}
        onConfirm={confirmBulkSubmit}
        onCancel={() => setModalOpen(false)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Top-level grid: splits into the two operator-facing stages.
// ---------------------------------------------------------------------------

export function ActionDraftGrid({
  drafts,
  onChange,
}: {
  drafts: ActionDraftResponse[];
  onChange: () => void;
}) {
  const proposed = drafts.filter(
    (d) => d.status === "proposed" || d.status === "edited",
  );
  const approved = drafts.filter((d) => d.status === "user_approved");
  const other = drafts.filter(
    (d) =>
      d.status !== "proposed" &&
      d.status !== "edited" &&
      d.status !== "user_approved",
  );

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
    <div data-testid="action-draft-grid" style={{ display: "grid", gap: 20 }}>
      <section data-testid="action-draft-stage-voorstellen">
        <h2 style={{ fontSize: 16, margin: "0 0 10px" }}>
          Voorstellen vandaag ({proposed.length})
        </h2>
        {proposed.length === 0 ? (
          <p style={{ color: "#6b7280", fontSize: 13, margin: 0 }}>
            Geen nieuwe voorstellen.
          </p>
        ) : (
          <div style={{ display: "grid", gap: 12 }}>
            {proposed.map((draft) => (
              <ActionDraftRow
                key={draft.action_draft_id}
                draft={draft}
                onChange={onChange}
              />
            ))}
          </div>
        )}
      </section>

      <section data-testid="action-draft-stage-te-verzenden">
        <h2 style={{ fontSize: 16, margin: "0 0 10px" }}>
          Te verzenden naar IBKR ({approved.length})
        </h2>
        {approved.length === 0 ? (
          <p style={{ color: "#6b7280", fontSize: 13, margin: 0 }}>
            Nog niets goedgekeurd om te verzenden.
          </p>
        ) : (
          <div style={{ display: "grid", gap: 12 }}>
            <BulkSubmitBar approvedDrafts={approved} onChange={onChange} />
            {approved.map((draft) => (
              <ActionDraftRow
                key={draft.action_draft_id}
                draft={draft}
                onChange={onChange}
              />
            ))}
          </div>
        )}
      </section>

      {other.length > 0 ? (
        <section data-testid="action-draft-stage-overig">
          <h2 style={{ fontSize: 16, margin: "0 0 10px" }}>
            Overige ({other.length})
          </h2>
          <div style={{ display: "grid", gap: 12 }}>
            {other.map((draft) => (
              <ActionDraftRow
                key={draft.action_draft_id}
                draft={draft}
                onChange={onChange}
              />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
