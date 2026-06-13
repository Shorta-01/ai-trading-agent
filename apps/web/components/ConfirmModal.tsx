"use client";

/**
 * V1.2 §AT — Reusable confirmation modal.
 *
 * Vervangt de oude `window.prompt("Type JA")` / `window.prompt(
 * "Type VERZEND")` typing-flows door een knop-gedreven modal met
 * Ja/Nee knoppen (CLAUDE.md §8). De operator hoeft niets meer te
 * typen — twee bewuste klikken (open + bevestig) volstaan als
 * mens-in-de-lus check.
 *
 * Het is een gecontroleerde component: de parent houdt `open`-state
 * bij en rendert de modal alleen wanneer nodig. `onConfirm` wordt
 * aangeroepen bij Ja, `onCancel` bij Nee of klik buiten de modal.
 */

import type { ReactNode } from "react";

export function ConfirmModal({
  open,
  title,
  body,
  confirmLabel = "Ja, bevestig",
  cancelLabel = "Nee, annuleer",
  confirmTone = "primary",
  busy = false,
  onConfirm,
  onCancel,
  testId = "confirm-modal",
}: {
  open: boolean;
  title: string;
  body: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmTone?: "primary" | "danger";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  testId?: string;
}) {
  if (!open) return null;

  const confirmBg =
    confirmTone === "danger" ? "#dc2626" : "#15803d";

  return (
    <div
      data-testid={`${testId}-overlay`}
      onClick={busy ? undefined : onCancel}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15, 23, 42, 0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 16,
      }}
    >
      <div
        data-testid={testId}
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#ffffff",
          borderRadius: 10,
          padding: 24,
          maxWidth: 480,
          width: "100%",
          boxShadow: "0 20px 60px rgba(0,0,0,0.25)",
        }}
      >
        <h3 style={{ margin: "0 0 12px", fontSize: 18, fontWeight: 700 }}>
          {title}
        </h3>
        <div style={{ fontSize: 14, color: "#374151", marginBottom: 20 }}>
          {body}
        </div>
        <div
          style={{
            display: "flex",
            gap: 10,
            justifyContent: "flex-end",
            flexWrap: "wrap",
          }}
        >
          <button
            type="button"
            data-testid={`${testId}-cancel`}
            onClick={onCancel}
            disabled={busy}
            style={{
              padding: "8px 16px",
              background: "#e5e7eb",
              color: "#374151",
              border: "none",
              borderRadius: 6,
              fontWeight: 600,
              cursor: busy ? "not-allowed" : "pointer",
            }}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            data-testid={`${testId}-confirm`}
            onClick={onConfirm}
            disabled={busy}
            style={{
              padding: "8px 16px",
              background: busy ? "#9ca3af" : confirmBg,
              color: "#ffffff",
              border: "none",
              borderRadius: 6,
              fontWeight: 600,
              cursor: busy ? "not-allowed" : "pointer",
            }}
          >
            {busy ? "Bezig…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
