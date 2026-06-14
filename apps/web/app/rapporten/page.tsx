"use client";

/**
 * V1.2 §AX / CLAUDE.md §13 — /rapporten maandelijks overzicht.
 *
 * Live pagina met jaar- en maand-selector. Toont per maand:
 *
 *  - Executive summary: netto winst, baseline-vergelijking, hit-rate
 *  - Open posities-count
 *  - Action-draft activiteit (proposed / approved / submitted)
 *  - Orchestrator verdict-uitsplitsing
 *  - Income breakdown + cumulatief jaartotaal
 *  - Software-prestatie (hit-rate, gemiddelde hold, confidence-bins)
 *  - Audit-tabel per gesloten trade
 *
 * Auto-PDF archief volgt in een opvolg-PR (geen PDF-library in V1).
 */

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  apiClient,
  type MonthlyReportRealisedTrade,
  type MonthlyReportResponse,
} from "@/lib/apiClient";
import { ArchivePanel } from "@/components/ArchivePanel";

const NOW = new Date();
const CURRENT_YEAR = NOW.getUTCFullYear();
const CURRENT_MONTH = NOW.getUTCMonth() + 1;
const YEAR_OPTIONS = Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - i);
const MONTH_LABELS_NL = [
  "Januari", "Februari", "Maart", "April", "Mei", "Juni",
  "Juli", "Augustus", "September", "Oktober", "November", "December",
];

function fmtMoney(value: string): string {
  const num = Number(value);
  if (Number.isNaN(num)) return value;
  return num.toLocaleString("nl-BE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function MoneyByCurrency({
  amounts,
  testId,
}: {
  amounts: Record<string, string>;
  testId?: string;
}) {
  const entries = Object.entries(amounts);
  if (entries.length === 0) return <span data-testid={testId}>—</span>;
  return (
    <span data-testid={testId}>
      {entries
        .map(([ccy, amount]) => `${fmtMoney(amount)} ${ccy}`)
        .join(" · ")}
    </span>
  );
}

function TradeRow({ trade }: { trade: MonthlyReportRealisedTrade }) {
  return (
    <tr
      data-testid={`rapport-trade-row-${trade.symbol}-${trade.sell_date}`}
    >
      <td>{trade.symbol}</td>
      <td>{trade.currency_local}</td>
      <td style={{ textAlign: "right" }}>{trade.quantity}</td>
      <td>{trade.buy_date}</td>
      <td>{trade.sell_date}</td>
      <td style={{ textAlign: "right" }}>{fmtMoney(trade.gross_local)}</td>
      <td
        style={{
          textAlign: "right",
          fontWeight: 700,
          color: Number(trade.net_local) >= 0 ? "#166534" : "#7f1d1d",
        }}
      >
        {fmtMoney(trade.net_local)}
      </td>
      <td style={{ textAlign: "right" }}>{trade.hold_days}</td>
      <td style={{ textAlign: "right" }}>
        {fmtMoney(trade.net_pct_on_cost)} %
      </td>
    </tr>
  );
}

function ConfidenceDistribution({
  data,
}: {
  data: Record<string, number>;
}) {
  const entries = Object.entries(data);
  if (entries.length === 0) {
    return (
      <p
        data-testid="rapport-confidence-empty"
        style={{ fontStyle: "italic", color: "#6b7280", fontSize: 13 }}
      >
        Geen verdicts in deze maand.
      </p>
    );
  }
  // Stable order: highest bucket first.
  const order = [">=90%", "80-90%", "70-80%", "60-70%", "<60%", "onbekend"];
  const sorted = entries.sort(
    (a, b) => order.indexOf(a[0]) - order.indexOf(b[0]),
  );
  return (
    <ul
      data-testid="rapport-confidence-distribution"
      style={{ listStyle: "none", margin: 0, padding: 0 }}
    >
      {sorted.map(([bucket, pct]) => (
        <li
          key={bucket}
          data-testid={`rapport-confidence-bucket-${bucket}`}
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: 12,
            padding: "2px 0",
          }}
        >
          <span>{bucket}</span>
          <span style={{ fontWeight: 600 }}>
            {pct.toFixed(1).replace(".", ",")} %
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function RapportenPage() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const [month, setMonth] = useState(CURRENT_MONTH);
  const query = useQuery({
    queryKey: ["monthly-report", year, month],
    queryFn: async (): Promise<MonthlyReportResponse | null> => {
      const result = await apiClient.getMonthlyReport({ year, month });
      return result.ok ? result.data : null;
    },
  });
  const report = query.data ?? null;

  return (
    <main className="page-wrap">
      <header
        style={{
          display: "flex",
          gap: 12,
          alignItems: "baseline",
          marginBottom: 12,
          flexWrap: "wrap",
        }}
      >
        <h1 style={{ margin: 0 }}>Maandrapport</h1>
        <label
          style={{ fontSize: 13, color: "#374151" }}
          htmlFor="rapport-year-select"
        >
          Jaar:
          <select
            id="rapport-year-select"
            data-testid="rapport-year-select"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            style={{
              marginLeft: 6,
              padding: "4px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 6,
            }}
          >
            {YEAR_OPTIONS.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <label
          style={{ fontSize: 13, color: "#374151" }}
          htmlFor="rapport-month-select"
        >
          Maand:
          <select
            id="rapport-month-select"
            data-testid="rapport-month-select"
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
            style={{
              marginLeft: 6,
              padding: "4px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 6,
            }}
          >
            {MONTH_LABELS_NL.map((label, idx) => (
              <option key={idx + 1} value={idx + 1}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <a
          data-testid="rapport-pdf-download"
          href={apiClient.monthlyReportPdfUrl({ year, month })}
          download
          style={{
            marginLeft: "auto",
            padding: "6px 12px",
            background: "#7c2d12",
            color: "#ffffff",
            borderRadius: 6,
            textDecoration: "none",
            fontWeight: 600,
            fontSize: 13,
          }}
        >
          Download PDF
        </a>
      </header>

      <section
        data-testid="rapport-executive-summary"
        style={{
          background: "#0f172a",
          color: "#ffffff",
          padding: 16,
          borderRadius: 8,
          marginBottom: 16,
        }}
      >
        <p
          data-testid="rapport-executive-headline"
          style={{ margin: 0, fontSize: 18, fontWeight: 700 }}
        >
          {report?.executive_summary.headline_nl ??
            "Maandrapport laden…"}
        </p>
        <div style={{ marginTop: 8, fontSize: 13, opacity: 0.9 }}>
          <strong>Netto van de maand:</strong>{" "}
          <MoneyByCurrency
            testId="rapport-executive-net"
            amounts={
              report?.executive_summary.net_local_by_currency ?? {}
            }
          />
        </div>
        {report?.executive_summary.vs_baseline_eur ? (
          <p
            data-testid="rapport-executive-baseline"
            style={{ margin: "6px 0 0", fontSize: 13, opacity: 0.9 }}
          >
            {report.executive_summary.vs_baseline_eur}
          </p>
        ) : null}
      </section>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <section
          data-testid="rapport-activity"
          style={{
            background: "#ffffff",
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            padding: 12,
          }}
        >
          <h2 style={{ marginTop: 0 }}>Maand-activiteit</h2>
          <dl
            style={{
              display: "grid",
              gridTemplateColumns: "1fr auto",
              gap: "4px 16px",
              margin: 0,
              fontSize: 13,
            }}
          >
            <dt>Open posities (laatste sync)</dt>
            <dd
              data-testid="rapport-open-positions-count"
              style={{ margin: 0, fontWeight: 600 }}
            >
              {report?.open_positions_count ?? 0}
            </dd>
            <dt>Action drafts voorgesteld</dt>
            <dd
              data-testid="rapport-activity-proposed"
              style={{ margin: 0 }}
            >
              {report?.action_draft_activity.proposed ?? 0}
            </dd>
            <dt>Goedgekeurd</dt>
            <dd
              data-testid="rapport-activity-approved"
              style={{ margin: 0 }}
            >
              {report?.action_draft_activity.user_approved ?? 0}
            </dd>
            <dt>Verzonden naar IBKR</dt>
            <dd
              data-testid="rapport-activity-submitted"
              style={{ margin: 0 }}
            >
              {report?.action_draft_activity.submitted ?? 0}
            </dd>
            <dt>Gefilled</dt>
            <dd
              data-testid="rapport-activity-filled"
              style={{ margin: 0 }}
            >
              {report?.action_draft_activity.filled ?? 0}
            </dd>
            <dt>Afgewezen</dt>
            <dd
              data-testid="rapport-activity-dismissed"
              style={{ margin: 0 }}
            >
              {report?.action_draft_activity.dismissed ?? 0}
            </dd>
          </dl>
        </section>

        <section
          data-testid="rapport-income"
          style={{
            background: "#ffffff",
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            padding: 12,
          }}
        >
          <h2 style={{ marginTop: 0 }}>Income</h2>
          <dl
            style={{
              display: "grid",
              gridTemplateColumns: "max-content 1fr",
              gap: "4px 16px",
              margin: 0,
              fontSize: 13,
            }}
          >
            <dt>Bruto capital gains</dt>
            <dd style={{ margin: 0 }}>
              <MoneyByCurrency
                amounts={
                  report?.income.capital_gains_local_by_currency ?? {}
                }
              />
            </dd>
            <dt>TOB</dt>
            <dd style={{ margin: 0, color: "#7f1d1d" }}>
              <MoneyByCurrency
                amounts={report?.income.tob_local_by_currency ?? {}}
              />
            </dd>
            <dt>Netto deze maand</dt>
            <dd
              data-testid="rapport-income-net"
              style={{ margin: 0, fontWeight: 700, color: "#166534" }}
            >
              <MoneyByCurrency
                amounts={report?.income.net_local_by_currency ?? {}}
              />
            </dd>
            <dt>Cumulatief YTD</dt>
            <dd
              data-testid="rapport-income-ytd"
              style={{ margin: 0, fontWeight: 700 }}
            >
              <MoneyByCurrency
                amounts={
                  report?.income.ytd_net_local_by_currency ?? {}
                }
              />
            </dd>
          </dl>
        </section>
      </div>

      <section
        data-testid="rapport-software-performance"
        style={{
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          padding: 12,
          marginBottom: 16,
        }}
      >
        <h2 style={{ marginTop: 0 }}>Software-prestatie</h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 16,
            fontSize: 13,
          }}
        >
          <dl style={{ margin: 0 }}>
            <dt style={{ color: "#6b7280" }}>Hit-rate +4 %</dt>
            <dd
              data-testid="rapport-perf-hit-rate"
              style={{ margin: "2px 0 8px", fontWeight: 700, fontSize: 16 }}
            >
              {(report?.software_performance.hit_rate_pct ?? 0)
                .toFixed(1)
                .replace(".", ",")}{" "}
              %
            </dd>
            <dt style={{ color: "#6b7280" }}>Gem. hold (dagen)</dt>
            <dd style={{ margin: "2px 0 8px", fontWeight: 600 }}>
              {report?.software_performance.average_hold_days ?? 0}
            </dd>
            <dt style={{ color: "#6b7280" }}>Voorstellen → goedgekeurd</dt>
            <dd
              data-testid="rapport-perf-approval-ratio"
              style={{ margin: 0, fontWeight: 600 }}
            >
              {report?.software_performance.proposals_vs_approved[0] ?? 0}
              {" → "}
              {report?.software_performance.proposals_vs_approved[1] ?? 0}
            </dd>
          </dl>
          <div>
            <p
              style={{
                margin: "0 0 4px",
                fontSize: 12,
                color: "#6b7280",
              }}
            >
              Confidence-distributie verdicts
            </p>
            <ConfidenceDistribution
              data={
                report?.software_performance.confidence_distribution_pct ??
                {}
              }
            />
          </div>
        </div>
      </section>

      <section
        data-testid="rapport-verdict-activity"
        style={{
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          padding: 12,
          marginBottom: 16,
        }}
      >
        <h2 style={{ marginTop: 0 }}>Orchestrator output</h2>
        {report && report.verdict_activity.total > 0 ? (
          <ul
            data-testid="rapport-verdict-list"
            style={{ listStyle: "none", margin: 0, padding: 0 }}
          >
            {Object.entries(report.verdict_activity.by_decision).map(
              ([decision, count]) => (
                <li
                  key={decision}
                  data-testid={`rapport-verdict-${decision}`}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 13,
                    padding: "4px 0",
                    borderBottom: "1px solid #f3f4f6",
                  }}
                >
                  <span>{decision}</span>
                  <span style={{ fontWeight: 600 }}>{count}</span>
                </li>
              ),
            )}
          </ul>
        ) : (
          <p
            data-testid="rapport-verdict-empty"
            style={{ fontStyle: "italic", color: "#6b7280", fontSize: 13 }}
          >
            Geen orchestrator-verdicts in deze maand.
          </p>
        )}
      </section>

      <section
        data-testid="rapport-trades-section"
        style={{
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          padding: 12,
          marginBottom: 16,
        }}
      >
        <h2 style={{ marginTop: 0 }}>Audit-trail: gesloten trades</h2>
        {report && report.realised_trades.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table
              data-testid="rapport-trades-table"
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 12,
              }}
            >
              <thead>
                <tr style={{ background: "#f3f4f6", textAlign: "left" }}>
                  <th>Symbool</th>
                  <th>Valuta</th>
                  <th style={{ textAlign: "right" }}>Aantal</th>
                  <th>Aankoop</th>
                  <th>Verkoop</th>
                  <th style={{ textAlign: "right" }}>Bruto</th>
                  <th style={{ textAlign: "right" }}>Netto</th>
                  <th style={{ textAlign: "right" }}>Hold</th>
                  <th style={{ textAlign: "right" }}>%</th>
                </tr>
              </thead>
              <tbody>
                {report.realised_trades.map((trade) => (
                  <TradeRow
                    key={`${trade.symbol}-${trade.sell_date}-${trade.quantity}`}
                    trade={trade}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p
            data-testid="rapport-trades-empty"
            style={{ fontStyle: "italic", color: "#6b7280" }}
          >
            Geen gesloten trades in {MONTH_LABELS_NL[month - 1]} {year}.
          </p>
        )}
      </section>

      {(report?.notes_nl ?? []).length > 0 ? (
        <div
          data-testid="rapport-notes"
          style={{
            background: "#fef3c7",
            border: "1px solid #fde68a",
            borderRadius: 6,
            padding: 10,
            fontSize: 12,
            color: "#92400e",
          }}
        >
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {(report?.notes_nl ?? []).map((note, idx) => (
              <li key={idx}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* V1.2 §CD / GAPS.md P2-11 — Events sectie (CLAUDE.md §13). */}
      {(report?.events ?? []).length > 0 ? (
        <section
          data-testid="rapport-events"
          style={{
            background: "#ffffff",
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            padding: 12,
            margin: "12px 0",
          }}
        >
          <h2 style={{ margin: 0, fontSize: 14, color: "#1f2937" }}>
            Events deze maand
          </h2>
          <p
            style={{
              margin: "2px 0 8px 0",
              fontSize: 11,
              color: "#6b7280",
            }}
          >
            Pauze-momenten, macro alerts, settings wijzigingen en andere
            operationele meldingen (severity ≥ warning).
          </p>
          <ul
            style={{
              listStyle: "none",
              padding: 0,
              margin: 0,
              display: "flex",
              flexDirection: "column",
              gap: 6,
            }}
          >
            {(report?.events ?? []).map((ev, idx) => (
              <li
                key={idx}
                data-testid={`rapport-event-${idx}`}
                data-severity={ev.severity}
                style={{
                  padding: "6px 10px",
                  background:
                    ev.severity === "critical"
                      ? "#fee2e2"
                      : ev.severity === "error"
                        ? "#fee2e2"
                        : "#fef3c7",
                  borderRadius: 4,
                  fontSize: 12,
                  color: "#374151",
                }}
              >
                <strong>{ev.title_nl}</strong>{" "}
                <span style={{ color: "#6b7280", fontSize: 11 }}>
                  ({ev.category} · {ev.severity}) ·{" "}
                  {ev.event_at.replace("T", " ").slice(0, 16)}
                </span>
                <div style={{ marginTop: 2 }}>{ev.message_nl}</div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <ArchivePanel defaultYear={year} defaultMonth={month} />
    </main>
  );
}
