"use client";

/**
 * V1.2 §AG — Belgian TOB year-to-date widget.
 *
 * Indicatief lopend jaartotaal voor de Belgische beurstaks (TOB).
 * Aggregeert ``estimated_belgian_tob`` van action-drafts die dit
 * kalenderjaar zijn ingediend ("approved" of "submitted"). Eind-juiste
 * realised-TOB-berekening vraagt classificatie per security-type op
 * elke fill (stock 0,35 % / bond 0,12 % / ETF 0,12 % – 1,32 %), wat
 * een follow-up backend job is. Tot dan: dit cijfer is bewust
 * gemerkt als "indicatief" zodat het niet als fiscaal bewijs wordt
 * gelezen.
 *
 * Geen AI-getallen: alle TOB-schattingen komen uit de bestaande
 * action-draft pijp (Belgisch tariefcatalogus toegepast in de
 * worker).
 */

import { useQuery } from "@tanstack/react-query";

import {
  apiClient,
  type AssetActionDraftResponse,
  type LatestActionDraftsResponse,
} from "@/lib/apiClient";

const POLL_INTERVAL_MS = 60_000;

function parseTob(value: string | null): number | null {
  if (value === null || value === undefined) return null;
  const cleaned = value.replace(",", ".").trim();
  const num = Number.parseFloat(cleaned);
  return Number.isFinite(num) ? num : null;
}

function isThisYear(iso: string): boolean {
  if (!iso) return false;
  return iso.startsWith(String(new Date().getUTCFullYear()));
}

function summarize(items: AssetActionDraftResponse[]): {
  totalEur: number;
  bookedCount: number;
  byClass: Record<string, number>;
} {
  let totalEur = 0;
  let bookedCount = 0;
  const byClass: Record<string, number> = {};
  for (const draft of items) {
    if (draft.status !== "approved" && draft.status !== "submitted") continue;
    if (!isThisYear(draft.updated_at)) continue;
    const tob = parseTob(draft.estimated_belgian_tob);
    if (tob === null) continue;
    totalEur += tob;
    bookedCount += 1;
    const cls = draft.belgian_tob_security_class ?? "onbekend";
    byClass[cls] = (byClass[cls] ?? 0) + tob;
  }
  return { totalEur, bookedCount, byClass };
}

export function BelgianTobYtdWidget() {
  const query = useQuery({
    queryKey: ["belgian-tob-ytd"],
    queryFn: async (): Promise<LatestActionDraftsResponse | null> => {
      const r = await apiClient.getLatestActionDrafts();
      return r.ok ? r.data : null;
    },
    refetchInterval: POLL_INTERVAL_MS,
  });
  const items = query.data?.items ?? [];
  const { totalEur, bookedCount, byClass } = summarize(items);
  const year = new Date().getUTCFullYear();

  return (
    <section
      data-testid="belgian-tob-ytd-widget"
      className="dashboard-panel"
      style={{ marginBottom: 12 }}
    >
      <div className="panel-head">
        <h2 style={{ margin: 0, fontSize: 16 }}>Belgische TOB {year} (indicatief)</h2>
        <span style={{ fontSize: 11, color: "#6b7280" }}>
          {bookedCount} geboekte action drafts
        </span>
      </div>
      <p
        className="top-sub"
        style={{ marginBottom: 8, color: "#6b7280", fontSize: 12 }}
      >
        Lopend totaal op basis van <code>estimated_belgian_tob</code> per action
        draft; alleen drafts met status &quot;approved&quot; of &quot;submitted&quot;
        in {year} tellen mee. Niet fiscaal bindend.
      </p>
      <div
        data-testid="belgian-tob-ytd-total"
        style={{ fontSize: 22, fontWeight: 700, color: "#111827" }}
      >
        EUR {totalEur.toFixed(2)}
      </div>
      {Object.keys(byClass).length > 0 ? (
        <div
          style={{
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            marginTop: 8,
          }}
        >
          {Object.entries(byClass)
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
    </section>
  );
}
