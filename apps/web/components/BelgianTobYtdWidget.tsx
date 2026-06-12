"use client";

/**
 * V1.2 §AH — Belgian TOB year-to-date widget (realised, met fallback).
 *
 * Eerst probeert het de realised TOB uit ``/tob/year-to-date`` (deze
 * leest ``ibkr_executions`` rechtstreeks en past de locked
 * tariefcatalogus toe). Als die endpoint geen executies vindt, valt
 * de widget terug op het oude indicatieve totaal uit de
 * action-draft schattingen — dan blijft de label "indicatief".
 *
 * Per-valuta totalen worden onverkort getoond — er wordt geen
 * wisselkoers verzonnen om alles in EUR samen te smelten.
 */

import { useQuery } from "@tanstack/react-query";

import {
  apiClient,
  type AssetActionDraftResponse,
  type LatestActionDraftsResponse,
  type TobYearToDateResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function parseDecimal(value: string | null): number | null {
  if (value === null || value === undefined) return null;
  const cleaned = value.replace(",", ".").trim();
  const num = Number.parseFloat(cleaned);
  return Number.isFinite(num) ? num : null;
}

function isThisYear(iso: string, year: number): boolean {
  if (!iso) return false;
  return iso.startsWith(String(year));
}

function summariseDrafts(items: AssetActionDraftResponse[], year: number): {
  totalEur: number;
  bookedCount: number;
  byClass: Record<string, number>;
} {
  let totalEur = 0;
  let bookedCount = 0;
  const byClass: Record<string, number> = {};
  for (const draft of items) {
    if (draft.status !== "approved" && draft.status !== "submitted") continue;
    if (!isThisYear(draft.updated_at, year)) continue;
    const tob = parseDecimal(draft.estimated_belgian_tob);
    if (tob === null) continue;
    totalEur += tob;
    bookedCount += 1;
    const cls = draft.belgian_tob_security_class ?? "onbekend";
    byClass[cls] = (byClass[cls] ?? 0) + tob;
  }
  return { totalEur, bookedCount, byClass };
}

export function BelgianTobYtdWidget() {
  const realisedQuery = useQuery({
    queryKey: ["belgian-tob-ytd-realised"],
    queryFn: async (): Promise<TobYearToDateResponse | null> => {
      const r = await apiClient.getTobYearToDate();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const draftsQuery = useQuery({
    queryKey: ["belgian-tob-ytd-drafts"],
    queryFn: async (): Promise<LatestActionDraftsResponse | null> => {
      const r = await apiClient.getLatestActionDrafts();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });

  const realised = realisedQuery.data ?? null;
  const usingRealised =
    realised !== null && realised.executions_count > 0;
  const year = realised?.year ?? new Date().getUTCFullYear();
  const drafts = draftsQuery.data?.items ?? [];
  const draftSummary = summariseDrafts(drafts, year);

  const modeLabel = usingRealised ? "realised" : "indicatief";
  const subtitle = usingRealised
    ? `${realised!.executions_count} geboekte fills in ${year}`
    : `${draftSummary.bookedCount} action drafts in ${year}`;

  return (
    <section
      data-testid="belgian-tob-ytd-widget"
      data-mode={modeLabel}
      className="dashboard-panel"
      style={{ marginBottom: 12 }}
    >
      <div className="panel-head">
        <h2 style={{ margin: 0, fontSize: 16 }}>
          Belgische TOB {year} ({modeLabel})
        </h2>
        <span style={{ fontSize: 11, color: "#6b7280" }}>{subtitle}</span>
      </div>
      <p
        className="top-sub"
        style={{ marginBottom: 8, color: "#6b7280", fontSize: 12 }}
      >
        {usingRealised
          ? "Realised TOB uit ibkr_executions; tariefcatalogus toegepast per fill. Per fill-valuta gerapporteerd — geen verzonnen wisselkoers."
          : "Indicatief totaal op basis van estimated_belgian_tob van action drafts met status approved/submitted in deze kalenderjaar. Schakelt automatisch naar realised zodra er fills geregistreerd zijn."}
      </p>
      {usingRealised ? (
        <RealisedView data={realised!} />
      ) : (
        <IndicativeView summary={draftSummary} />
      )}
    </section>
  );
}

function RealisedView({ data }: { data: TobYearToDateResponse }) {
  const entries = Object.entries(data.by_currency);
  if (entries.length === 0) {
    return (
      <p style={{ marginTop: 8, color: "#6b7280", fontSize: 12 }}>
        Nog geen geboekte TOB dit jaar.
      </p>
    );
  }
  return (
    <>
      <div
        data-testid="belgian-tob-ytd-total"
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
          fontSize: 20,
          fontWeight: 700,
          color: "#111827",
        }}
      >
        {entries.map(([ccy, amount]) => (
          <span key={ccy} data-testid={`belgian-tob-ytd-currency-${ccy}`}>
            {ccy} {amount}
          </span>
        ))}
      </div>
      <div
        style={{
          display: "flex",
          gap: 8,
          flexWrap: "wrap",
          marginTop: 8,
        }}
      >
        {Object.entries(data.by_security_class).flatMap(([cls, ccyMap]) =>
          Object.entries(ccyMap).map(([ccy, amount]) => (
            <span
              key={`${cls}-${ccy}`}
              data-testid={`belgian-tob-ytd-class-${cls}-${ccy}`}
              style={{
                background: "#f3f4f6",
                color: "#374151",
                padding: "3px 10px",
                borderRadius: 10,
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              {cls} ({ccy}): {amount}
            </span>
          )),
        )}
      </div>
      <p
        style={{
          marginTop: 8,
          color: "#6b7280",
          fontSize: 11,
          fontStyle: "italic",
        }}
      >
        {data.note_nl}
      </p>
    </>
  );
}

function IndicativeView({
  summary,
}: {
  summary: { totalEur: number; bookedCount: number; byClass: Record<string, number> };
}) {
  return (
    <>
      <div
        data-testid="belgian-tob-ytd-total"
        style={{ fontSize: 22, fontWeight: 700, color: "#111827" }}
      >
        EUR {summary.totalEur.toFixed(2)}
      </div>
      {Object.keys(summary.byClass).length > 0 ? (
        <div
          style={{
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            marginTop: 8,
          }}
        >
          {Object.entries(summary.byClass)
            .sort(([, a], [, b]) => b - a)
            .map(([cls, sum]) => (
              <span
                key={cls}
                data-testid={`belgian-tob-ytd-class-${cls}`}
                style={{
                  background: "#f3f4f6",
                  color: "#374151",
                  padding: "3px 10px",
                  borderRadius: 10,
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                {cls}: EUR {sum.toFixed(2)}
              </span>
            ))}
        </div>
      ) : (
        <p style={{ marginTop: 8, color: "#6b7280", fontSize: 12 }}>
          Nog geen geboekte TOB dit jaar.
        </p>
      )}
    </>
  );
}
