"use client";

/**
 * Task 133: inline edit form for an Action Draft.
 *
 * Pure presentational + a single PATCH on save. The grid passes the
 * current draft + ``onSaved`` / ``onCancel`` callbacks; the form
 * holds local state for quantity / limit price / note and submits on
 * Save. Validation: quantity > 0, limit price > 0 — matches the
 * API's 422 conditions so users see the error before the request.
 */

import { useState } from "react";

import { apiClient, type ActionDraftResponse } from "@/lib/apiClient";

export function ActionDraftEditForm({
  draft,
  onCancel,
  onSaved,
}: {
  draft: ActionDraftResponse;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const [quantity, setQuantity] = useState(draft.quantity);
  const [limitPrice, setLimitPrice] = useState(draft.limit_price_local);
  const [userNote, setUserNote] = useState(draft.user_note ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function validate(): string | null {
    const qty = Number(quantity);
    const price = Number(limitPrice);
    if (Number.isNaN(qty) || qty <= 0) {
      return "Aantal moet groter dan 0 zijn.";
    }
    if (Number.isNaN(price) || price <= 0) {
      return "Limietprijs moet groter dan 0 zijn.";
    }
    return null;
  }

  async function handleSave() {
    const msg = validate();
    if (msg !== null) {
      setError(msg);
      return;
    }
    setBusy(true);
    setError(null);
    const payload: { [key: string]: string } = {};
    if (quantity !== draft.quantity) payload.quantity = quantity;
    if (limitPrice !== draft.limit_price_local) {
      payload.limit_price_local = limitPrice;
    }
    if (userNote !== (draft.user_note ?? "")) {
      payload.user_note = userNote;
    }
    if (Object.keys(payload).length === 0) {
      onCancel();
      setBusy(false);
      return;
    }
    const result = await apiClient.patchActionDraft(
      draft.action_draft_id,
      payload,
    );
    setBusy(false);
    if (!result.ok) {
      setError(result.message || "Bewerken mislukt.");
      return;
    }
    onSaved();
  }

  return (
    <form
      data-testid={`action-draft-edit-form-${draft.action_draft_id}`}
      onSubmit={(event) => {
        event.preventDefault();
        void handleSave();
      }}
      style={{
        display: "grid",
        gap: 12,
        background: "#f9fafb",
        padding: 12,
        borderRadius: 6,
      }}
    >
      <label style={{ display: "grid", gap: 4 }}>
        <span style={{ fontWeight: 600, fontSize: 13 }}>Aantal</span>
        <input
          data-testid={`action-draft-edit-quantity-${draft.action_draft_id}`}
          type="number"
          step="1"
          min="1"
          value={quantity}
          onChange={(event) => setQuantity(event.target.value)}
          required
        />
      </label>
      <label style={{ display: "grid", gap: 4 }}>
        <span style={{ fontWeight: 600, fontSize: 13 }}>
          Limietprijs ({draft.currency_local})
        </span>
        <input
          data-testid={`action-draft-edit-limit-${draft.action_draft_id}`}
          type="number"
          step="0.0001"
          min="0.0001"
          value={limitPrice}
          onChange={(event) => setLimitPrice(event.target.value)}
          required
        />
      </label>
      <label style={{ display: "grid", gap: 4 }}>
        <span style={{ fontWeight: 600, fontSize: 13 }}>Notitie</span>
        <textarea
          data-testid={`action-draft-edit-note-${draft.action_draft_id}`}
          value={userNote}
          onChange={(event) => setUserNote(event.target.value)}
          rows={2}
        />
      </label>
      {error ? (
        <div
          data-testid={`action-draft-edit-error-${draft.action_draft_id}`}
          style={{
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
      <div style={{ display: "flex", gap: 8 }}>
        <button
          type="submit"
          data-testid={`action-draft-edit-save-${draft.action_draft_id}`}
          disabled={busy}
          style={{
            padding: "8px 16px",
            background: "#1d4ed8",
            color: "#ffffff",
            border: "none",
            borderRadius: 6,
            cursor: busy ? "wait" : "pointer",
            fontWeight: 600,
          }}
        >
          Opslaan
        </button>
        <button
          type="button"
          data-testid={`action-draft-edit-cancel-${draft.action_draft_id}`}
          onClick={onCancel}
          disabled={busy}
          style={{
            padding: "8px 16px",
            background: "#e5e7eb",
            color: "#111827",
            border: "none",
            borderRadius: 6,
            cursor: busy ? "wait" : "pointer",
          }}
        >
          Annuleren
        </button>
      </div>
    </form>
  );
}
