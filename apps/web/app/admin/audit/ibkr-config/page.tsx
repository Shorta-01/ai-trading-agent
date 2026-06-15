/**
 * V1.2 §BZ vervolg — /admin/audit/ibkr-config compliance audit-trail.
 *
 * Consumeert ``GET /admin/audit/ibkr-config`` (toegevoegd in #675).
 * Toont chronologisch (newest-first) elke SystemEvent rondom IBKR
 * mode-switches, mismatches en account-id wijzigingen — inclusief
 * RESOLVED en ARCHIVED rijen die de operator + accountant nodig
 * hebben als "goed huisvader" bewijs (§12).
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient, type SystemEventSummary } from "@/lib/apiClient";

function StatusBadge({ status }: { status: string }) {
  const colour =
    status === "open"
      ? "#b45309"
      : status === "resolved"
        ? "#15803d"
        : "#6b7280";
  return (
    <span
      data-testid={`audit-event-status-${status}`}
      style={{
        background: colour,
        color: "white",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
      }}
    >
      {status}
    </span>
  );
}

function SeverityChip({ severity }: { severity: string }) {
  const colour =
    severity === "error"
      ? "#b91c1c"
      : severity === "warning"
        ? "#d97706"
        : "#0369a1";
  return (
    <span
      style={{
        background: colour,
        color: "white",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
      }}
    >
      {severity}
    </span>
  );
}

function formatLocalDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("nl-BE", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Brussels",
  });
}

export default function IbkrConfigAuditPage() {
  const query = useQuery({
    queryKey: ["admin-ibkr-config-audit"],
    queryFn: async () => {
      const res = await apiClient.getIbkrConfigAudit();
      return res.ok ? res.data : null;
    },
  });
  const data = query.data;

  return (
    <main
      data-testid="admin-ibkr-config-audit-page"
      style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}
    >
      <h1 style={{ marginBottom: 4 }}>IBKR-config audit-trail</h1>
      <p style={{ marginTop: 0, color: "#6b7280", fontSize: 14 }}>
        Chronologisch overzicht van mode-switches, mismatches en
        account-id wijzigingen. Bewijs voor het &ldquo;goed
        huisvader&rdquo; §12 belastingrapport.
      </p>

      {query.isLoading ? (
        <p data-testid="admin-ibkr-config-audit-loading">Laden…</p>
      ) : null}

      {!query.isLoading && data === null ? (
        <p data-testid="admin-ibkr-config-audit-error">
          Audit-trail kon niet worden geladen. Controleer of de API
          draait en opslag is geconfigureerd.
        </p>
      ) : null}

      {data ? (
        <>
          <p
            data-testid="admin-ibkr-config-audit-count"
            style={{ fontSize: 13, color: "#374151" }}
          >
            {data.active_count} events gevonden — {data.message_nl}
          </p>

          {data.events.length === 0 ? (
            <p
              data-testid="admin-ibkr-config-audit-empty"
              style={{
                marginTop: 16,
                color: "#6b7280",
                fontStyle: "italic",
              }}
            >
              Geen events in het audit-trail. Dit betekent dat er
              sinds deployment geen mode-switches, mismatches of
              account-id wijzigingen zijn geweest.
            </p>
          ) : (
            <table
              data-testid="admin-ibkr-config-audit-table"
              style={{
                width: "100%",
                borderCollapse: "collapse",
                marginTop: 16,
                fontSize: 13,
              }}
            >
              <thead>
                <tr style={{ background: "#f3f4f6", textAlign: "left" }}>
                  <th style={{ padding: "8px 10px" }}>Tijd (Europe/Brussels)</th>
                  <th style={{ padding: "8px 10px" }}>Status</th>
                  <th style={{ padding: "8px 10px" }}>Severity</th>
                  <th style={{ padding: "8px 10px" }}>Event-code</th>
                  <th style={{ padding: "8px 10px" }}>Source</th>
                  <th style={{ padding: "8px 10px" }}>Bericht</th>
                </tr>
              </thead>
              <tbody>
                {data.events.map((event: SystemEventSummary) => (
                  <tr
                    key={event.system_event_id}
                    data-testid={`audit-event-row-${event.system_event_id}`}
                    style={{ borderBottom: "1px solid #e5e7eb" }}
                  >
                    <td style={{ padding: "8px 10px", whiteSpace: "nowrap" }}>
                      {formatLocalDate(event.created_at)}
                    </td>
                    <td style={{ padding: "8px 10px" }}>
                      <StatusBadge status={event.status} />
                    </td>
                    <td style={{ padding: "8px 10px" }}>
                      <SeverityChip severity={event.severity} />
                    </td>
                    <td
                      style={{
                        padding: "8px 10px",
                        fontFamily: "monospace",
                        fontSize: 12,
                      }}
                    >
                      {event.event_code}
                    </td>
                    <td style={{ padding: "8px 10px", fontSize: 12 }}>
                      {event.source_service}:{event.source_component}
                    </td>
                    <td style={{ padding: "8px 10px" }}>
                      <strong style={{ display: "block" }}>
                        {event.title_nl}
                      </strong>
                      <span style={{ color: "#4b5563" }}>{event.message_nl}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      ) : null}
    </main>
  );
}
