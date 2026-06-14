"use client";

/**
 * V1.2 §BO / CLAUDE.md §8 — Workflow stage summary widgets.
 *
 * GAPS.md P1-1: doctrine §8 vraagt drie stage-blokken op het
 * dashboard. Stage 1 ("Voorstellen vandaag") wordt al door
 * TodayActionsPanel afgedekt; PendingApprovalsPanel mixt Stage 1+2.
 * Deze module voegt twee compact-summary widgets toe:
 *
 *  - Stage2ReadyToSendWidget — count van ``user_approved`` drafts
 *    + link naar /ibkr-acties (Te verzenden naar IBKR tab)
 *  - Stage3SubmittedWidget — count van submitted/working/filled
 *    + per-status breakdown + link naar /ibkr-acties (Historiek tab)
 *
 * Beide pollen elke 60s. Read-only — geen mutations. Operator klikt
 * door naar /ibkr-acties voor edit/bulk-submit/historiek details.
 *
 * CLAUDE.md §2 borging: deze widgets tonen alleen tellers; geen
 * "Verzend alle" knop op het dashboard zelf (die hoort op
 * /ibkr-acties achter een modal confirm).
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo } from "react";

import {
  apiClient,
  type AssetActionDraftResponse,
  type LatestActionDraftsResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

const STAGE_2_STATUSES = ["user_approved", "approved"];
const STAGE_3_STATUSES = [
  "submitted",
  "submitting",
  "working",
  "accepted",
  "partially_filled",
  "filled",
];

function statusLabel(status: string): string {
  if (status === "user_approved" || status === "approved")
    return "Goedgekeurd";
  if (status === "submitting") return "Verzenden…";
  if (status === "submitted") return "Verzonden";
  if (status === "accepted") return "Geaccepteerd";
  if (status === "working") return "Werkend";
  if (status === "partially_filled") return "Deels gevuld";
  if (status === "filled") return "Gevuld";
  return status;
}

function useDrafts() {
  return useQuery({
    queryKey: ["dashboard-action-drafts"],
    queryFn: async (): Promise<LatestActionDraftsResponse | null> => {
      const result = await apiClient.getLatestActionDrafts();
      return result.ok ? result.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
}

function countByStatus(
  drafts: AssetActionDraftResponse[],
  statuses: string[],
): Record<string, number> {
  const out: Record<string, number> = {};
  for (const status of statuses) out[status] = 0;
  for (const d of drafts) {
    if (statuses.includes(d.status)) {
      out[d.status] = (out[d.status] || 0) + 1;
    }
  }
  return out;
}

function CardShell({
  testId,
  title,
  helpNl,
  link,
  children,
}: {
  testId: string;
  title: string;
  helpNl: string;
  link: { href: string; label: string };
  children: React.ReactNode;
}) {
  return (
    <section
      data-testid={testId}
      style={{
        background: "#ffffff",
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: 14, color: "#1f2937" }}>{title}</h2>
          <p
            style={{
              margin: "2px 0 0 0",
              fontSize: 11,
              color: "#6b7280",
            }}
          >
            {helpNl}
          </p>
        </div>
        <Link
          data-testid={`${testId}-link`}
          href={link.href}
          style={{
            fontSize: 12,
            color: "#3b82f6",
            textDecoration: "none",
          }}
        >
          {link.label} →
        </Link>
      </header>
      {children}
    </section>
  );
}

export function Stage2ReadyToSendWidget() {
  const query = useDrafts();
  const items = query.data?.items;
  const counts = useMemo(
    () => countByStatus(items ?? [], STAGE_2_STATUSES),
    [items],
  );
  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  return (
    <CardShell
      testId="stage-2-ready-to-send"
      title="Te verzenden naar IBKR"
      helpNl="Goedgekeurde voorstellen wachten op je bulk-submit klik."
      link={{ href: "/ibkr-acties", label: "Bekijk lijst" }}
    >
      {query.isLoading && (
        <p
          data-testid="stage-2-ready-to-send-loading"
          style={{ margin: 0, fontSize: 12, color: "#6b7280" }}
        >
          Laden…
        </p>
      )}
      {!query.isLoading && query.data === null && (
        <p
          data-testid="stage-2-ready-to-send-error"
          style={{ margin: 0, fontSize: 12, color: "#dc2626" }}
        >
          Kon action-drafts niet ophalen.
        </p>
      )}
      {query.data !== null && query.data !== undefined && total === 0 && (
        <p
          data-testid="stage-2-ready-to-send-empty"
          style={{ margin: 0, fontSize: 12, color: "#6b7280" }}
        >
          Geen voorstellen in afwachting van verzending.
        </p>
      )}
      {total > 0 && (
        <div
          data-testid="stage-2-ready-to-send-total"
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: 8,
          }}
        >
          <strong style={{ fontSize: 28, color: "#16a34a" }}>{total}</strong>
          <span style={{ fontSize: 13, color: "#374151" }}>
            voorstel{total === 1 ? "" : "len"} klaar voor IBKR paper
          </span>
        </div>
      )}
    </CardShell>
  );
}

export function Stage3SubmittedWidget() {
  const query = useDrafts();
  const items = query.data?.items;
  const counts = useMemo(
    () => countByStatus(items ?? [], STAGE_3_STATUSES),
    [items],
  );
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const breakdown = useMemo(
    () =>
      Object.entries(counts)
        .filter(([, n]) => n > 0)
        .map(([status, n]) => ({
          status,
          label: statusLabel(status),
          count: n,
        })),
    [counts],
  );

  return (
    <CardShell
      testId="stage-3-submitted"
      title="Verzonden naar IBKR"
      helpNl="Live status van IBKR-orders; read-only."
      link={{ href: "/ibkr-acties", label: "Bekijk historiek" }}
    >
      {query.isLoading && (
        <p
          data-testid="stage-3-submitted-loading"
          style={{ margin: 0, fontSize: 12, color: "#6b7280" }}
        >
          Laden…
        </p>
      )}
      {!query.isLoading && query.data === null && (
        <p
          data-testid="stage-3-submitted-error"
          style={{ margin: 0, fontSize: 12, color: "#dc2626" }}
        >
          Kon IBKR-status niet ophalen.
        </p>
      )}
      {query.data !== null && query.data !== undefined && total === 0 && (
        <p
          data-testid="stage-3-submitted-empty"
          style={{ margin: 0, fontSize: 12, color: "#6b7280" }}
        >
          Nog geen orders verzonden vandaag.
        </p>
      )}
      {total > 0 && (
        <>
          <div
            data-testid="stage-3-submitted-total"
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 8,
            }}
          >
            <strong style={{ fontSize: 28, color: "#3b82f6" }}>{total}</strong>
            <span style={{ fontSize: 13, color: "#374151" }}>
              order{total === 1 ? "" : "s"} bij IBKR paper
            </span>
          </div>
          <ul
            data-testid="stage-3-submitted-breakdown"
            style={{
              listStyle: "none",
              padding: 0,
              margin: 0,
              display: "flex",
              gap: 6,
              flexWrap: "wrap",
            }}
          >
            {breakdown.map((b) => (
              <li
                key={b.status}
                data-testid={`stage-3-status-${b.status}`}
                style={{
                  padding: "2px 8px",
                  background: "#f3f4f6",
                  color: "#374151",
                  borderRadius: 12,
                  fontSize: 11,
                }}
              >
                {b.label}: <strong>{b.count}</strong>
              </li>
            ))}
          </ul>
        </>
      )}
    </CardShell>
  );
}
