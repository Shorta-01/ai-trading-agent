"use client";

/**
 * V1.2 §AW / CLAUDE.md §12 — Belastingjaaroverzicht.
 *
 * Volledig overzicht voor de accountant: gerealiseerde
 * kapitaalwinsten met FIFO-matching, Belgische TOB op beide kanten,
 * jaartotalen, maandgrafiek, "goed huisvader"-bewijs en een CSV-
 * export. Per kalenderjaar selecteerbaar.
 *
 * Bedragen blijven in lokale munt totdat het systeem historische
 * FX-koersen bijhoudt — een ``notes_nl`` regel maakt dit expliciet
 * voor de accountant.
 */

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { DividendenManager } from "@/components/DividendenManager";
import {
  apiClient,
  type TaxRealisedTrade,
  type TaxYearReportResponse,
} from "@/lib/apiClient";

const CURRENT_YEAR = new Date().getUTCFullYear();
const YEAR_OPTIONS = Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - i);

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
}: {
  amounts: Record<string, string>;
}) {
  const entries = Object.entries(amounts);
  if (entries.length === 0) return <span>—</span>;
  return (
    <span>
      {entries
        .map(([ccy, amount]) => `${fmtMoney(amount)} ${ccy}`)
        .join(" · ")}
    </span>
  );
}

function TradeRow({ trade }: { trade: TaxRealisedTrade }) {
  return (
    <tr data-testid={`tax-trade-row-${trade.buy_exec_id}-${trade.sell_exec_id}`}>
      <td>{trade.symbol}</td>
      <td>{trade.account_id}</td>
      <td>{trade.currency_local}</td>
      <td style={{ textAlign: "right" }}>{trade.quantity}</td>
      <td>{trade.buy_date}</td>
      <td style={{ textAlign: "right" }}>{fmtMoney(trade.buy_price_local)}</td>
      <td>{trade.sell_date}</td>
      <td style={{ textAlign: "right" }}>{fmtMoney(trade.sell_price_local)}</td>
      <td style={{ textAlign: "right" }}>{fmtMoney(trade.gross_local)}</td>
      <td style={{ textAlign: "right", color: "#7f1d1d" }}>
        −{fmtMoney(trade.tob_buy_local)}
      </td>
      <td style={{ textAlign: "right", color: "#7f1d1d" }}>
        −{fmtMoney(trade.tob_sell_local)}
      </td>
      <td
        data-testid={`tax-trade-row-${trade.buy_exec_id}-${trade.sell_exec_id}-net`}
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

function MonthlyChart({
  monthlyPoints,
}: {
  monthlyPoints: TaxYearReportResponse["monthly_points"];
}) {
  // Pick the single currency with the biggest absolute cumulative
  // movement as the rendered series — multi-currency overlays would
  // need normalisation which V1 explicitly defers.
  const series = useMemo(() => {
    const totals: Record<string, number> = {};
    for (const point of monthlyPoints) {
      for (const [ccy, amount] of Object.entries(
        point.cumulative_net_local_by_currency,
      )) {
        totals[ccy] = Math.max(
          totals[ccy] ?? 0,
          Math.abs(Number(amount) || 0),
        );
      }
    }
    const ccy = Object.entries(totals).sort((a, b) => b[1] - a[1])[0]?.[0];
    if (!ccy) return null;
    const values = monthlyPoints.map(
      (p) => Number(p.cumulative_net_local_by_currency[ccy] ?? "0"),
    );
    return { ccy, values };
  }, [monthlyPoints]);

  if (series === null) {
    return (
      <p
        data-testid="tax-monthly-chart-empty"
        style={{ fontStyle: "italic", color: "#6b7280", fontSize: 13 }}
      >
        Nog geen gerealiseerde resultaten om te plotten.
      </p>
    );
  }
  const max = Math.max(...series.values.map((v) => Math.abs(v)), 1);
  return (
    <div data-testid="tax-monthly-chart" style={{ display: "flex", gap: 4 }}>
      {series.values.map((value, idx) => {
        const height = (Math.abs(value) / max) * 80;
        const color = value >= 0 ? "#16a34a" : "#dc2626";
        return (
          <div
            key={idx}
            data-testid={`tax-monthly-bar-${idx}`}
            title={`${monthlyPoints[idx].month}: ${fmtMoney(String(value))} ${series.ccy}`}
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 4,
            }}
          >
            <div
              style={{
                width: "100%",
                height: 80,
                background: "#f3f4f6",
                borderRadius: 4,
                display: "flex",
                alignItems: "flex-end",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: "100%",
                  height: `${height}%`,
                  background: color,
                  transition: "height 200ms",
                }}
              />
            </div>
            <div style={{ fontSize: 9, color: "#6b7280" }}>
              {monthlyPoints[idx].month.slice(5)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function BelastingPage() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const query = useQuery({
    queryKey: ["tax-year-report", year],
    queryFn: async (): Promise<TaxYearReportResponse | null> => {
      const result = await apiClient.getTaxYearReport({ year });
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
        }}
      >
        <h1 style={{ margin: 0 }}>Belastingoverzicht</h1>
        <label
          style={{ fontSize: 13, color: "#374151" }}
          htmlFor="tax-year-select"
        >
          Jaar:
          <select
            id="tax-year-select"
            data-testid="tax-year-select"
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
        <a
          data-testid="tax-csv-download"
          href={apiClient.taxYearReportCsvUrl({ year })}
          download
          style={{
            marginLeft: "auto",
            padding: "6px 12px",
            background: "#0f172a",
            color: "#ffffff",
            borderRadius: 6,
            textDecoration: "none",
            fontWeight: 600,
            fontSize: 13,
          }}
        >
          Download CSV
        </a>
      </header>

      <p
        style={{
          margin: 0,
          fontSize: 13,
          color: "#374151",
          marginBottom: 12,
        }}
      >
        {report?.help_nl ??
          "Belastingoverzicht laden — gerealiseerde kapitaalwinsten worden FIFO-gematched per (account, symbol)."}
      </p>

      {(report?.notes_nl ?? []).length > 0 ? (
        <div
          data-testid="tax-notes"
          style={{
            background: "#fef3c7",
            border: "1px solid #fde68a",
            borderRadius: 6,
            padding: 10,
            marginBottom: 16,
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

      <section
        data-testid="tax-year-totals"
        style={{
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          padding: 12,
          marginBottom: 16,
        }}
      >
        <h2 style={{ marginTop: 0 }}>Jaartotalen</h2>
        <dl
          style={{
            display: "grid",
            gridTemplateColumns: "max-content 1fr",
            gap: "6px 16px",
            margin: 0,
            fontSize: 13,
          }}
        >
          <dt style={{ fontWeight: 600 }}>Aantal trades</dt>
          <dd
            data-testid="tax-year-totals-trade-count"
            style={{ margin: 0 }}
          >
            {report?.year_totals.trade_count ?? 0}
          </dd>
          <dt style={{ fontWeight: 600 }}>Bruto</dt>
          <dd style={{ margin: 0 }}>
            <MoneyByCurrency
              amounts={report?.year_totals.gross_local_by_currency ?? {}}
            />
          </dd>
          <dt style={{ fontWeight: 600 }}>Totaal TOB</dt>
          <dd
            data-testid="tax-year-totals-tob"
            style={{ margin: 0, color: "#7f1d1d" }}
          >
            <MoneyByCurrency
              amounts={report?.year_totals.tob_local_by_currency ?? {}}
            />
          </dd>
          <dt style={{ fontWeight: 600 }}>Netto</dt>
          <dd
            data-testid="tax-year-totals-net"
            style={{
              margin: 0,
              fontWeight: 700,
              color: "#166534",
            }}
          >
            <MoneyByCurrency
              amounts={report?.year_totals.net_local_by_currency ?? {}}
            />
          </dd>
          <dt style={{ fontWeight: 600 }}>Gem. hold (dagen)</dt>
          <dd style={{ margin: 0 }}>
            {report?.year_totals.average_hold_days ?? 0}
          </dd>
          <dt style={{ fontWeight: 600 }}>Hit-rate +4 %</dt>
          <dd data-testid="tax-year-totals-hit-rate" style={{ margin: 0 }}>
            {report?.year_totals.hit_rate_pct.toFixed(1).replace(".", ",") ??
              "0,0"}{" "}
            %
          </dd>
          {report?.year_totals.net_eur_total ? (
            <>
              <dt
                style={{
                  fontWeight: 600,
                  marginTop: 8,
                  paddingTop: 8,
                  borderTop: "1px solid #e5e7eb",
                }}
              >
                Netto EUR (FX-conversie)
              </dt>
              <dd
                data-testid="tax-year-totals-net-eur"
                style={{
                  margin: 0,
                  fontWeight: 700,
                  color: "#166534",
                  marginTop: 8,
                  paddingTop: 8,
                  borderTop: "1px solid #e5e7eb",
                }}
              >
                {fmtMoney(report.year_totals.net_eur_total)} EUR{" "}
                <span style={{ fontSize: 11, color: "#6b7280" }}>
                  ({report.year_totals.eur_conversion_coverage_pct ?? 0} %
                  conversie-dekking)
                </span>
              </dd>
            </>
          ) : null}
        </dl>
      </section>

      <section
        data-testid="tax-good-householder"
        style={{
          background: "#f0fdf4",
          border: "1px solid #bbf7d0",
          borderRadius: 8,
          padding: 12,
          marginBottom: 16,
        }}
      >
        <h2 style={{ marginTop: 0, color: "#166534" }}>
          &ldquo;Goed huisvader&rdquo;-bewijs
        </h2>
        <p style={{ margin: 0, color: "#14532d" }}>
          {report?.good_householder.summary_nl ?? "Berekening loopt…"}
        </p>
      </section>

      <section
        data-testid="tax-monthly-section"
        style={{
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          padding: 12,
          marginBottom: 16,
        }}
      >
        <h2 style={{ marginTop: 0 }}>Cumulatief per maand</h2>
        <MonthlyChart monthlyPoints={report?.monthly_points ?? []} />
      </section>

      <section
        data-testid="tax-realised-trades-section"
        style={{
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          padding: 12,
          marginBottom: 16,
        }}
      >
        <h2 style={{ marginTop: 0 }}>Gerealiseerde trades</h2>
        {report && report.realised_trades.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table
              data-testid="tax-realised-trades-table"
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 12,
              }}
            >
              <thead>
                <tr style={{ background: "#f3f4f6", textAlign: "left" }}>
                  <th>Symbool</th>
                  <th>Account</th>
                  <th>Valuta</th>
                  <th style={{ textAlign: "right" }}>Aantal</th>
                  <th>Aankoop-datum</th>
                  <th style={{ textAlign: "right" }}>Aankoop-prijs</th>
                  <th>Verkoop-datum</th>
                  <th style={{ textAlign: "right" }}>Verkoop-prijs</th>
                  <th style={{ textAlign: "right" }}>Bruto</th>
                  <th style={{ textAlign: "right" }}>TOB aankoop</th>
                  <th style={{ textAlign: "right" }}>TOB verkoop</th>
                  <th style={{ textAlign: "right" }}>Netto</th>
                  <th style={{ textAlign: "right" }}>Hold</th>
                  <th style={{ textAlign: "right" }}>%</th>
                </tr>
              </thead>
              <tbody>
                {report.realised_trades.map((trade) => (
                  <TradeRow
                    key={`${trade.buy_exec_id}-${trade.sell_exec_id}`}
                    trade={trade}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p
            data-testid="tax-realised-trades-empty"
            style={{ fontStyle: "italic", color: "#6b7280" }}
          >
            Geen gerealiseerde trades in {year}.
          </p>
        )}
      </section>

      <section
        data-testid="tax-dividends-section"
        style={{
          background: "#ffffff",
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          padding: 12,
        }}
      >
        <h2 style={{ marginTop: 0 }}>Ontvangen dividenden</h2>
        <p
          data-testid="tax-dividends-info"
          style={{ fontStyle: "italic", color: "#6b7280", fontSize: 13 }}
        >
          V1 heeft geen broker-dividend-feed; je registreert dividenden
          handmatig hieronder. De bronbelasting wordt automatisch
          ingevuld volgens verdrag-tarieven (US 15 %, NL 15 %, FR 12,8 %,
          BE 0 %). Belgische 30 % roerende voorheffing-regularisatie
          komt op rapportniveau van je accountant.
        </p>
        <div style={{ marginTop: 12 }}>
          <DividendenManager year={year} />
        </div>
      </section>
    </main>
  );
}
