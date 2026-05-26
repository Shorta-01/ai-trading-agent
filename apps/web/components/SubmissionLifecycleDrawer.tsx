"use client";

/**
 * Task 134c: Submission lifecycle drawer.
 *
 * Opens when the user clicks an in-flight or historiek row in the
 * IBKR Acties page. Fetches the full
 * ``GET /ibkr-submission/lifecycle/{action_draft_id}`` log and
 * renders every callback event in chronological order with the
 * locked Dutch labels.
 *
 * Read-only — the user can't mutate the lifecycle from this view.
 * Closing the drawer is the only action.
 */

import { useEffect, useState } from "react";

import {
  apiClient,
  type IbkrSubmissionLifecycleEvent,
} from "@/lib/apiClient";

const EVENT_LABEL_NL: Record<
  IbkrSubmissionLifecycleEvent["event_type"],
  string
> = {
  status_change: "Statuswijziging",
  fill: "Uitvoering",
  commission_report: "Commissie",
  cancellation_request: "Annulering door gebruiker",
};

const STATUS_LABEL_NL: Record<string, string> = {
  submitted: "Verstuurd",
  accepted: "Geaccepteerd",
  working: "Actief bij IBKR",
  partially_filled: "Gedeeltelijk uitgevoerd",
  filled: "Uitgevoerd",
  cancelled: "Geannuleerd",
  rejected: "Geweigerd",
  pending_cancellation: "Annulering aangevraagd",
  awaiting_reply_timeout: "Wacht op IBKR-bevestiging",
};

function fmtTs(value: string): string {
  return value.slice(0, 19).replace("T", " ");
}

function fmtStatus(status: string | null): string {
  if (status === null) return "—";
  return STATUS_LABEL_NL[status] ?? status;
}

function fmtDecimal(value: string | null, decimals = 2): string {
  if (value === null) return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return value;
  return num.toLocaleString("nl-BE", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function SubmissionLifecycleDrawer({
  actionDraftId,
  open,
  onClose,
}: {
  actionDraftId: string | null;
  open: boolean;
  onClose: () => void;
}) {
  const [events, setEvents] = useState<
    IbkrSubmissionLifecycleEvent[] | null
  >(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || actionDraftId === null) {
      setEvents(null);
      setError(null);
      return;
    }
    let cancelled = false;
    async function load() {
      setError(null);
      setEvents(null);
      const result = await apiClient.getIbkrSubmissionLifecycle(
        actionDraftId as string,
      );
      if (cancelled) return;
      if (!result.ok) {
        setError(
          "Lifecycle kon niet worden geladen. Controleer of de API draait.",
        );
        setEvents([]);
        return;
      }
      setEvents(result.data.events);
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [open, actionDraftId]);

  if (!open || actionDraftId === null) return null;

  return (
    <div
      data-testid="submission-lifecycle-drawer"
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        bottom: 0,
        width: "min(540px, 100%)",
        background: "#ffffff",
        borderLeft: "2px solid #d1d5db",
        boxShadow: "-8px 0 24px rgba(0,0,0,0.08)",
        padding: 24,
        overflowY: "auto",
        zIndex: 50,
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h2 style={{ margin: 0, fontSize: 18 }}>Lifecycle</h2>
        <button
          type="button"
          data-testid="submission-lifecycle-close"
          onClick={onClose}
          style={{
            padding: "6px 14px",
            background: "#e5e7eb",
            color: "#111827",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
          }}
        >
          Sluiten
        </button>
      </header>
      <p style={{ color: "#6b7280", fontSize: 12, marginBottom: 16 }}>
        Draft: <code>{actionDraftId}</code>
      </p>

      {error ? (
        <div
          style={{
            color: "#7f1d1d",
            background: "#fee2e2",
            padding: 12,
            borderRadius: 6,
            marginBottom: 12,
          }}
        >
          {error}
        </div>
      ) : null}

      {events === null ? (
        <p>Bezig met laden…</p>
      ) : events.length === 0 ? (
        <p data-testid="submission-lifecycle-empty">
          Nog geen lifecycle-events voor deze draft.
        </p>
      ) : (
        <ol
          data-testid="submission-lifecycle-events"
          style={{
            margin: 0,
            padding: 0,
            listStyle: "none",
            display: "grid",
            gap: 12,
          }}
        >
          {events.map((event) => (
            <li
              key={event.id ?? `${event.event_at}-${event.event_type}`}
              data-testid={`submission-lifecycle-event-${event.id ?? "x"}`}
              style={{
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                padding: 12,
                background: "#f9fafb",
              }}
            >
              <header
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  fontSize: 13,
                  marginBottom: 6,
                }}
              >
                <strong>{EVENT_LABEL_NL[event.event_type]}</strong>
                <span style={{ color: "#6b7280" }}>
                  {fmtTs(event.event_at)}
                </span>
              </header>
              <dl
                style={{
                  display: "grid",
                  gridTemplateColumns: "max-content 1fr",
                  gap: "2px 12px",
                  margin: 0,
                  fontSize: 13,
                }}
              >
                {event.event_type === "status_change" ? (
                  <>
                    <dt style={{ fontWeight: 600 }}>Van</dt>
                    <dd style={{ margin: 0 }}>
                      {fmtStatus(event.from_status)}
                    </dd>
                    <dt style={{ fontWeight: 600 }}>Naar</dt>
                    <dd style={{ margin: 0 }}>
                      {fmtStatus(event.to_status)}
                    </dd>
                    {event.ibkr_raw_status !== null ? (
                      <>
                        <dt style={{ fontWeight: 600 }}>IBKR-status</dt>
                        <dd
                          style={{ margin: 0, fontFamily: "monospace" }}
                        >
                          {event.ibkr_raw_status}
                        </dd>
                      </>
                    ) : null}
                  </>
                ) : null}
                {event.event_type === "fill" ? (
                  <>
                    <dt style={{ fontWeight: 600 }}>Hoeveelheid</dt>
                    <dd style={{ margin: 0 }}>
                      {fmtDecimal(event.fill_quantity, 0)}
                    </dd>
                    <dt style={{ fontWeight: 600 }}>Prijs</dt>
                    <dd style={{ margin: 0 }}>
                      {fmtDecimal(event.fill_price_local, 4)}
                    </dd>
                    <dt style={{ fontWeight: 600 }}>Nieuwe status</dt>
                    <dd style={{ margin: 0 }}>
                      {fmtStatus(event.to_status)}
                    </dd>
                  </>
                ) : null}
                {event.event_type === "commission_report" ? (
                  <>
                    <dt style={{ fontWeight: 600 }}>Commissie</dt>
                    <dd style={{ margin: 0 }}>
                      {fmtDecimal(event.commission, 2)}{" "}
                      {event.commission_currency ?? ""}
                    </dd>
                  </>
                ) : null}
                {event.event_type === "cancellation_request" ? (
                  <>
                    <dt style={{ fontWeight: 600 }}>Van</dt>
                    <dd style={{ margin: 0 }}>
                      {fmtStatus(event.from_status)}
                    </dd>
                    <dt style={{ fontWeight: 600 }}>Naar</dt>
                    <dd style={{ margin: 0 }}>
                      {fmtStatus(event.to_status)}
                    </dd>
                  </>
                ) : null}
              </dl>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
