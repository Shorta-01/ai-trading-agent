"use client";

/**
 * Task 135b: /admin/reconciliation page.
 *
 * Four sections in a single Dutch-labelled admin view:
 *   1. Status header — latest run summary + per-pass counts.
 *   2. Wacht op handmatige beoordeling — pending manual_review_queue
 *      rows with a per-row "Bevestig" action that flips the row to
 *      ``acknowledged``.
 *   3. Onbekende IBKR-uitvoeringen — unresolved unmatched executions
 *      (TWS-side fills with no matching draft).
 *   4. Recente reconciliatieruns — last 50 run-audit rows.
 *
 * Read-only except for the acknowledge POST. Doctrine intact:
 * reconciliation is IBKR-read-only; the admin page never writes to
 * IBKR.
 */

import { useQuery } from "@tanstack/react-query";
import { useCallback } from "react";

import {
  apiClient,
  type ManualReviewResponse,
  type ReconciliationRunResponse,
  type ReconciliationStatusResponse,
  type UnmatchedExecutionRow,
} from "@/lib/apiClient";
import { maskAccountId } from "@/lib/maskAccountId";

const MODE_LABELS: Record<string, string> = {
  completed: "Voltooid",
  skipped_locked: "Overgeslagen (vergrendeld)",
  skipped_disconnected: "Overgeslagen (geen verbinding)",
  error: "Fout",
};

const REASON_LABELS: Record<string, string> = {
  timeout_24h_no_data: "24u timeout zonder IBKR-data",
  terminal_state_divergence: "Verschil in eindstatus",
  unmatched_execution_no_draft: "Uitvoering zonder draft",
};


type ReconciliationOverview = {
  status: ReconciliationStatusResponse;
  pendingReview: ManualReviewResponse[] | null;
  unmatched: UnmatchedExecutionRow[] | null;
  runs: ReconciliationRunResponse[] | null;
};

export default function Page() {
  const query = useQuery({
    queryKey: ["reconciliation-overview"],
    queryFn: async (): Promise<ReconciliationOverview> => {
      const [statusResult, reviewResult, unmatchedResult, runsResult] =
        await Promise.all([
          apiClient.getReconciliationStatus(),
          apiClient.getReconciliationManualReview(),
          apiClient.getReconciliationUnmatchedExecutions(),
          apiClient.getReconciliationRuns(),
        ]);
      // The status read gates the whole page; the others degrade to null.
      if (!statusResult.ok) {
        throw new Error("Reconciliatiestatus is niet beschikbaar.");
      }
      return {
        status: statusResult.data,
        pendingReview: reviewResult.ok ? reviewResult.data.rows : null,
        unmatched: unmatchedResult.ok ? unmatchedResult.data.rows : null,
        runs: runsResult.ok ? runsResult.data.runs : null,
      };
    },
  });

  const status = query.data?.status ?? null;
  const pendingReview = query.data?.pendingReview ?? null;
  const unmatched = query.data?.unmatched ?? null;
  const runs = query.data?.runs ?? null;
  const error = query.isError ? "Reconciliatiestatus is niet beschikbaar." : null;

  const handleAcknowledge = useCallback(
    async (queueId: number) => {
      const note = window.prompt(
        "Optionele notitie bij het bevestigen:",
        "",
      );
      const result = await apiClient.acknowledgeManualReview(
        queueId,
        note ?? undefined,
      );
      if (!result.ok) {
        window.alert("Bevestigen mislukt.");
        return;
      }
      await query.refetch();
    },
    [query],
  );

  if (error !== null) {
    return (
      <main style={{ padding: 24 }}>
        <h1 style={{ marginBottom: 12 }}>IBKR-reconciliatie</h1>
        <p data-testid="reconciliation-page-error" style={{ color: "#b91c1c" }}>
          {error}
        </p>
      </main>
    );
  }

  if (status === null) {
    return (
      <main style={{ padding: 24 }}>
        <h1 style={{ marginBottom: 12 }}>IBKR-reconciliatie</h1>
        <p data-testid="reconciliation-page-loading">Laden…</p>
      </main>
    );
  }

  return (
    <main style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
      <h1 style={{ marginBottom: 4 }}>IBKR-reconciliatie</h1>
      <p style={{ marginTop: 0, color: "#6b7280", fontSize: 14 }}>
        Account: {maskAccountId(status.ibkr_account_id)}
      </p>

      {/* Status summary */}
      <section
        data-testid="reconciliation-status-card"
        style={{
          background: "#f9fafb",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          padding: 16,
          marginBottom: 24,
        }}
      >
        <h2 style={{ marginTop: 0, fontSize: 16 }}>Huidige status</h2>
        {status.latest_run === null ? (
          <p data-testid="reconciliation-status-no-runs">
            Nog geen reconciliatie-runs uitgevoerd.
          </p>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(5, 1fr)",
              gap: 12,
            }}
          >
            <SummaryCell
              label="Laatste run"
              value={
                MODE_LABELS[status.latest_run.mode_detected] ?? "Onbekend"
              }
            />
            <SummaryCell
              label="Pass A (orphaned)"
              value={status.latest_run.pass_a_orphaned_count}
            />
            <SummaryCell
              label="Pass B (stale)"
              value={status.latest_run.pass_b_stale_count}
            />
            <SummaryCell
              label="Pass C (timeout)"
              value={status.latest_run.pass_c_timeout_count}
            />
            <SummaryCell
              label="Hersteld (24u)"
              value={status.drafts_healed_last_24h}
            />
          </div>
        )}
      </section>

      {/* Pending manual review */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16 }}>
          Wacht op handmatige beoordeling ({status.pending_manual_review_count})
        </h2>
        {pendingReview !== null && pendingReview.length === 0 ? (
          <p
            data-testid="reconciliation-no-pending-review"
            style={{ color: "#6b7280" }}
          >
            Geen openstaande rijen.
          </p>
        ) : (
          <table
            data-testid="reconciliation-pending-review-table"
            style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
          >
            <thead>
              <tr style={{ background: "#f3f4f6" }}>
                <th style={{ textAlign: "left", padding: 8 }}>
                  Action Draft
                </th>
                <th style={{ textAlign: "left", padding: 8 }}>Reden</th>
                <th style={{ textAlign: "left", padding: 8 }}>
                  Gemarkeerd
                </th>
                <th style={{ textAlign: "left", padding: 8 }}>Detail</th>
                <th style={{ padding: 8 }}></th>
              </tr>
            </thead>
            <tbody>
              {(pendingReview ?? []).map((row) => (
                <tr key={row.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                  <td style={{ padding: 8, fontFamily: "monospace" }}>
                    {row.action_draft_id}
                  </td>
                  <td style={{ padding: 8 }}>
                    {REASON_LABELS[row.reason] ?? row.reason}
                  </td>
                  <td style={{ padding: 8 }}>
                    {new Date(row.flagged_at).toLocaleString("nl-NL")}
                  </td>
                  <td style={{ padding: 8, color: "#374151" }}>
                    {row.details_dutch}
                  </td>
                  <td style={{ padding: 8 }}>
                    <button
                      data-testid={`reconciliation-acknowledge-${row.id}`}
                      type="button"
                      onClick={() => {
                        if (row.id !== null) {
                          void handleAcknowledge(row.id);
                        }
                      }}
                      style={{
                        background: "#1f2937",
                        color: "#ffffff",
                        border: "none",
                        padding: "4px 10px",
                        borderRadius: 4,
                        fontSize: 12,
                        cursor: "pointer",
                      }}
                    >
                      Bevestig
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Unmatched executions */}
      <section style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16 }}>
          Onbekende IBKR-uitvoeringen ({status.unresolved_unmatched_count})
        </h2>
        {unmatched !== null && unmatched.length === 0 ? (
          <p
            data-testid="reconciliation-no-unmatched"
            style={{ color: "#6b7280" }}
          >
            Geen onbekende uitvoeringen.
          </p>
        ) : (
          <table
            data-testid="reconciliation-unmatched-table"
            style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
          >
            <thead>
              <tr style={{ background: "#f3f4f6" }}>
                <th style={{ textAlign: "left", padding: 8 }}>Exec ID</th>
                <th style={{ textAlign: "left", padding: 8 }}>Perm ID</th>
                <th style={{ textAlign: "left", padding: 8 }}>Conid</th>
                <th style={{ textAlign: "left", padding: 8 }}>Kant</th>
                <th style={{ textAlign: "right", padding: 8 }}>Aantal</th>
                <th style={{ textAlign: "right", padding: 8 }}>Prijs</th>
                <th style={{ textAlign: "left", padding: 8 }}>Tijd</th>
              </tr>
            </thead>
            <tbody>
              {(unmatched ?? []).map((row) => (
                <tr key={row.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                  <td style={{ padding: 8, fontFamily: "monospace" }}>
                    {row.ibkr_exec_id}
                  </td>
                  <td style={{ padding: 8, fontFamily: "monospace" }}>
                    {row.ibkr_perm_id}
                  </td>
                  <td style={{ padding: 8 }}>{row.conid}</td>
                  <td style={{ padding: 8 }}>{row.side}</td>
                  <td style={{ padding: 8, textAlign: "right" }}>
                    {row.fill_quantity}
                  </td>
                  <td style={{ padding: 8, textAlign: "right" }}>
                    {row.fill_price_local}
                  </td>
                  <td style={{ padding: 8 }}>
                    {new Date(row.fill_time).toLocaleString("nl-NL")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Run history */}
      <section>
        <h2 style={{ fontSize: 16 }}>Recente reconciliatieruns</h2>
        {runs !== null && runs.length === 0 ? (
          <p
            data-testid="reconciliation-no-runs"
            style={{ color: "#6b7280" }}
          >
            Nog geen runs uitgevoerd.
          </p>
        ) : (
          <table
            data-testid="reconciliation-runs-table"
            style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
          >
            <thead>
              <tr style={{ background: "#f3f4f6" }}>
                <th style={{ textAlign: "left", padding: 8 }}>Run ID</th>
                <th style={{ textAlign: "left", padding: 8 }}>Gestart</th>
                <th style={{ textAlign: "left", padding: 8 }}>Status</th>
                <th style={{ textAlign: "right", padding: 8 }}>A</th>
                <th style={{ textAlign: "right", padding: 8 }}>B</th>
                <th style={{ textAlign: "right", padding: 8 }}>C</th>
                <th style={{ textAlign: "right", padding: 8 }}>Totaal</th>
              </tr>
            </thead>
            <tbody>
              {(runs ?? []).map((row) => (
                <tr key={row.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                  <td style={{ padding: 8, fontFamily: "monospace", fontSize: 12 }}>
                    {row.reconciliation_run_id}
                  </td>
                  <td style={{ padding: 8 }}>
                    {new Date(row.started_at).toLocaleString("nl-NL")}
                  </td>
                  <td style={{ padding: 8 }}>
                    {MODE_LABELS[row.mode_detected] ?? row.mode_detected}
                  </td>
                  <td style={{ padding: 8, textAlign: "right" }}>
                    {row.pass_a_orphaned_count}
                  </td>
                  <td style={{ padding: 8, textAlign: "right" }}>
                    {row.pass_b_stale_count}
                  </td>
                  <td style={{ padding: 8, textAlign: "right" }}>
                    {row.pass_c_timeout_count}
                  </td>
                  <td style={{ padding: 8, textAlign: "right", fontWeight: 600 }}>
                    {row.divergences_found}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}


function SummaryCell({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div>
      <div style={{ fontSize: 18, fontWeight: 700, color: "#1f2937" }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: "#6b7280" }}>{label}</div>
    </div>
  );
}
