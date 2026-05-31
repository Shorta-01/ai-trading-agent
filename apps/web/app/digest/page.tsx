/**
 * Einde-dag digest — the operator's "what happened today" page.
 *
 * Reads the latest ``DailyDigestRecord`` from ``GET /digests/today``
 * and renders four cards (NAV, posities, suggesties, action drafts)
 * plus the operator-facing alert list at the top so anything urgent
 * is the first thing seen.
 *
 * Updated on every ``market_close`` fire of a followed market —
 * usually 17:45 CET for EU operators, 22:15 CET for US operators.
 */

"use client";

import Link from "next/link";

import { useQuery } from "@tanstack/react-query";

import { apiClient, type DigestAlert } from "@/lib/apiClient";

const DIGEST_QUERY_KEY = ["digest", "today"] as const;

const QUERY_OPTIONS = {
  staleTime: 5 * 60_000, // 5 min — digest only changes after a market_close fire
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
} as const;

const SECTION_STYLE: React.CSSProperties = {
  border: "1px solid #e5e7eb",
  borderRadius: 8,
  padding: 16,
  marginTop: 16,
  background: "#ffffff",
};

const CARD_GRID_STYLE: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
  gap: 12,
  marginTop: 16,
};

function formatNumber(value: unknown, fractionDigits = 2): string {
  if (value == null) return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return num.toLocaleString("nl-BE", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

function deltaColor(value: unknown): string {
  if (value == null) return "#374151";
  const num = Number(value);
  if (!Number.isFinite(num)) return "#374151";
  if (num > 0) return "#15803d";
  if (num < 0) return "#b91c1c";
  return "#374151";
}

function deltaArrow(value: unknown): string {
  if (value == null) return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  if (num > 0) return "▲";
  if (num < 0) return "▼";
  return "·";
}

function severityPalette(severity: string): {
  background: string;
  border: string;
  text: string;
} {
  switch (severity.toLowerCase()) {
    case "belangrijk":
      return { background: "#fee2e2", border: "#fca5a5", text: "#991b1b" };
    case "waarschuwing":
      return { background: "#fef3c7", border: "#fcd34d", text: "#92400e" };
    default:
      return { background: "#e0f2fe", border: "#7dd3fc", text: "#075985" };
  }
}

function AlertCallout({ alert }: { alert: DigestAlert }) {
  const palette = severityPalette(alert.severity_nl);
  return (
    <div
      data-testid={`digest-alert-${alert.kind}`}
      style={{
        background: palette.background,
        border: `1px solid ${palette.border}`,
        borderRadius: 6,
        padding: 12,
        marginTop: 8,
      }}
    >
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: palette.text,
          letterSpacing: 0.4,
          textTransform: "uppercase",
        }}
      >
        {alert.severity_nl}
      </div>
      <div style={{ fontWeight: 600, color: palette.text, marginTop: 2 }}>
        {alert.title_nl}
      </div>
      <div style={{ fontSize: 13, color: "#374151", marginTop: 4 }}>
        {alert.body_nl}
      </div>
    </div>
  );
}

function NavCard({ nav }: { nav: Record<string, unknown> }) {
  const totalNav = nav.total_nav as string | undefined;
  const deltaAbs = nav.delta_abs as string | undefined;
  const deltaPct = nav.delta_pct as string | undefined;
  const currency = (nav.currency as string | undefined) ?? "EUR";
  return (
    <div
      data-testid="digest-card-nav"
      style={{ ...SECTION_STYLE, marginTop: 0 }}
    >
      <div style={{ fontSize: 12, color: "#6b7280", fontWeight: 600 }}>
        PORTFOLIO NAV
      </div>
      <div style={{ marginTop: 6, fontSize: 22, fontWeight: 600 }}>
        {totalNav ? `${formatNumber(totalNav)} ${currency}` : "—"}
      </div>
      <div
        style={{
          marginTop: 4,
          fontSize: 14,
          color: deltaColor(deltaPct),
          fontWeight: 600,
        }}
      >
        {deltaArrow(deltaPct)} {deltaAbs ?? "—"} {currency} (
        {deltaPct != null ? `${deltaPct}%` : "—"})
      </div>
    </div>
  );
}

function PositionsCard({
  positions,
}: {
  positions: Record<string, unknown>;
}) {
  const count = (positions.position_count as number | undefined) ?? 0;
  const winners = (positions.top_winners as Array<Record<string, unknown>>) ?? [];
  const losers = (positions.top_losers as Array<Record<string, unknown>>) ?? [];
  return (
    <div
      data-testid="digest-card-positions"
      style={{ ...SECTION_STYLE, marginTop: 0 }}
    >
      <div style={{ fontSize: 12, color: "#6b7280", fontWeight: 600 }}>
        POSITIES — {count} totaal
      </div>
      <div style={{ marginTop: 8 }}>
        <strong style={{ fontSize: 13 }}>Top winners</strong>
        {winners.length === 0 ? (
          <div style={{ fontSize: 13, color: "#6b7280" }}>—</div>
        ) : (
          <ul style={{ margin: "4px 0 0 16px", padding: 0, fontSize: 13 }}>
            {winners.slice(0, 3).map((w) => (
              <li key={String(w.symbol)}>
                {String(w.symbol)} —{" "}
                <span style={{ color: "#15803d", fontWeight: 600 }}>
                  +{String(w.pnl_pct)}%
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div style={{ marginTop: 10 }}>
        <strong style={{ fontSize: 13 }}>Top losers</strong>
        {losers.length === 0 ? (
          <div style={{ fontSize: 13, color: "#6b7280" }}>—</div>
        ) : (
          <ul style={{ margin: "4px 0 0 16px", padding: 0, fontSize: 13 }}>
            {losers.slice(0, 3).map((l) => (
              <li key={String(l.symbol)}>
                {String(l.symbol)} —{" "}
                <span style={{ color: "#b91c1c", fontWeight: 600 }}>
                  {String(l.pnl_pct)}%
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function SuggestionsCard({
  suggestions,
}: {
  suggestions: Record<string, unknown>;
}) {
  const total = (suggestions.total as number | undefined) ?? 0;
  const highConf = (suggestions.high_confidence_count as number | undefined) ?? 0;
  const byLabel =
    (suggestions.by_action_label as Record<string, number>) ?? {};
  const sortedLabels = Object.entries(byLabel).sort((a, b) => b[1] - a[1]);
  return (
    <div
      data-testid="digest-card-suggestions"
      style={{ ...SECTION_STYLE, marginTop: 0 }}
    >
      <div style={{ fontSize: 12, color: "#6b7280", fontWeight: 600 }}>
        SUGGESTIES VANDAAG
      </div>
      <div style={{ marginTop: 6, fontSize: 22, fontWeight: 600 }}>{total}</div>
      <div style={{ fontSize: 13, color: "#374151", marginTop: 2 }}>
        Waarvan{" "}
        <strong style={{ color: "#15803d" }}>{highConf} hoge zekerheid</strong>
      </div>
      {sortedLabels.length > 0 ? (
        <ul style={{ margin: "8px 0 0 16px", padding: 0, fontSize: 13 }}>
          {sortedLabels.map(([label, count]) => (
            <li key={label}>
              {label}: <strong>{count}</strong>
            </li>
          ))}
        </ul>
      ) : null}
      <Link
        href="/suggesties"
        data-testid="digest-card-suggestions-link"
        style={{
          display: "inline-block",
          marginTop: 10,
          fontSize: 12,
          color: "#1f2937",
          textDecoration: "underline",
        }}
      >
        Open de suggesties-grid →
      </Link>
    </div>
  );
}

function ActionDraftsCard({
  drafts,
}: {
  drafts: Record<string, unknown>;
}) {
  const created = (drafts.created_today as number | undefined) ?? 0;
  const approved = (drafts.approved_today as number | undefined) ?? 0;
  const submitted = (drafts.submitted_today as number | undefined) ?? 0;
  const cancelled = (drafts.cancelled_today as number | undefined) ?? 0;
  return (
    <div
      data-testid="digest-card-action-drafts"
      style={{ ...SECTION_STYLE, marginTop: 0 }}
    >
      <div style={{ fontSize: 12, color: "#6b7280", fontWeight: 600 }}>
        ACTION DRAFTS VANDAAG
      </div>
      <ul style={{ margin: "8px 0 0 16px", padding: 0, fontSize: 13 }}>
        <li>
          Aangemaakt: <strong>{created}</strong>
        </li>
        <li>
          Goedgekeurd: <strong>{approved}</strong>
        </li>
        <li>
          Verstuurd: <strong>{submitted}</strong>
        </li>
        <li>
          Geannuleerd: <strong>{cancelled}</strong>
        </li>
      </ul>
    </div>
  );
}

export default function Page() {
  const query = useQuery({
    queryKey: DIGEST_QUERY_KEY,
    queryFn: async () => {
      const result = await apiClient.getDigestToday();
      if (!result.ok) throw new Error("digest-unavailable");
      return result.data;
    },
    ...QUERY_OPTIONS,
  });

  if (query.isPending) {
    return (
      <main className="page-wrap" data-testid="digest-page">
        <h2>Einde-dag digest</h2>
        <p data-testid="digest-loading">Laden...</p>
      </main>
    );
  }

  if (query.isError || !query.data) {
    return (
      <main className="page-wrap" data-testid="digest-page">
        <h2>Einde-dag digest</h2>
        <p data-testid="digest-error" style={{ color: "#b91c1c" }}>
          Digest kon niet worden opgehaald. Controleer de opslag-
          verbinding en probeer opnieuw.
        </p>
      </main>
    );
  }

  const data = query.data;
  const noData = data.generated_at == null;

  return (
    <main className="page-wrap" data-testid="digest-page">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 12,
        }}
      >
        <div>
          <h2 style={{ margin: 0 }}>Einde-dag digest</h2>
          <p
            data-testid="digest-status"
            style={{ marginTop: 4, color: "#374151", fontSize: 13 }}
          >
            {data.status_nl}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void query.refetch()}
          data-testid="digest-refresh"
          style={{
            border: "1px solid #d1d5db",
            background: "#ffffff",
            color: "#374151",
            borderRadius: 4,
            padding: "6px 12px",
            fontSize: 13,
            cursor: "pointer",
          }}
        >
          Vernieuwen
        </button>
      </div>

      <p
        style={{
          marginTop: 8,
          color: "#6b7280",
          fontSize: 13,
          lineHeight: 1.5,
        }}
      >
        {data.help_nl}
      </p>

      {data.generated_at ? (
        <div
          data-testid="digest-meta"
          style={{
            marginTop: 12,
            display: "flex",
            gap: 16,
            fontSize: 13,
            color: "#374151",
            flexWrap: "wrap",
          }}
        >
          <span>
            <strong>Gegenereerd:</strong>{" "}
            {new Date(data.generated_at).toLocaleString("nl-BE")}
          </span>
          <span>
            <strong>Markt:</strong> {data.market_code}
          </span>
          {data.briefing_date ? (
            <span>
              <strong>Datum:</strong> {data.briefing_date}
            </span>
          ) : null}
        </div>
      ) : null}

      {data.alerts.length > 0 ? (
        <section
          style={SECTION_STYLE}
          data-testid="digest-alerts-section"
        >
          <h3 style={{ margin: 0, fontSize: 16 }}>Aandachtspunten</h3>
          {data.alerts.map((alert) => (
            <AlertCallout key={alert.kind} alert={alert} />
          ))}
        </section>
      ) : null}

      {noData ? (
        <section style={SECTION_STYLE} data-testid="digest-empty">
          <p style={{ margin: 0, color: "#374151" }}>
            Geen digest beschikbaar. De eerste digest verschijnt nadat
            een gevolgde markt vandaag sluit (~15 min na slottime).
          </p>
        </section>
      ) : (
        <div style={CARD_GRID_STYLE}>
          <NavCard nav={data.nav_summary} />
          <PositionsCard positions={data.positions_summary} />
          <SuggestionsCard suggestions={data.suggestions_summary} />
          <ActionDraftsCard drafts={data.action_drafts_summary} />
        </div>
      )}
    </main>
  );
}
