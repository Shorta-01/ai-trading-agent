"use client";

/**
 * Task 126b: real-data Portefeuille panel.
 *
 * Three vertical states:
 *
 * 1. **Disconnected** — full-width Dutch banner; grid hidden.
 * 2. **Connected, empty** — cash card visible, positions table
 *    shows the empty-state Dutch message.
 * 3. **Connected, populated** — cash card + positions grid render
 *    the latest persisted snapshot from
 *    ``/ibkr/sync/positions/latest`` + ``/ibkr/sync/cash/latest``.
 *
 * Decimal precision is preserved end-to-end — every numeric arrives
 * as a string from the API and is rendered verbatim. Empty values
 * surface as "Niet beschikbaar".
 */

import { useQuery } from "@tanstack/react-query";

import {
  apiClient,
  IbkrCashLatestResponse,
  IbkrPositionsLatestResponse,
  MarketDataByAccountResponse,
  MarketDataByAccountRow,
} from "@/lib/apiClient";
import { PriceFreshnessBadge } from "@/components/PriceFreshnessBadge";

const POLL_INTERVAL_MS = 30_000;

const NIET_BESCHIKBAAR = "Niet beschikbaar";

function formatNumber(value: string | null): string {
  if (value === null || value.trim() === "") return NIET_BESCHIKBAAR;
  return value;
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return NIET_BESCHIKBAAR;
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return NIET_BESCHIKBAAR;
    return d.toLocaleString("nl-BE", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return NIET_BESCHIKBAAR;
  }
}

function formatCashLabel(currency: string, raw: string | null): string {
  return raw === null || raw.trim() === ""
    ? NIET_BESCHIKBAAR
    : `${currency} ${raw}`;
}

export function PortefeuilleRealtimeSection() {
  const query = useQuery({
    queryKey: ["portefeuille-realtime"],
    refetchInterval: POLL_INTERVAL_MS,
    queryFn: async () => {
      const [statusResult, positionsResult, cashResult, marketDataResult] =
        await Promise.all([
          apiClient.getIbkrConnectionStatus(),
          apiClient.getIbkrSyncPositionsLatest(),
          apiClient.getIbkrSyncCashLatest(),
          apiClient.getMarketDataByAccount(),
        ]);
      return {
        status: statusResult.ok ? statusResult.data : null,
        positions: positionsResult.ok ? positionsResult.data : null,
        cash: cashResult.ok ? cashResult.data : null,
        marketData: marketDataResult.ok ? marketDataResult.data : null,
        hasStorageError:
          !statusResult.ok || !positionsResult.ok || !cashResult.ok,
      };
    },
  });

  const status = query.data?.status ?? null;
  const positions = query.data?.positions ?? null;
  const cash = query.data?.cash ?? null;
  const marketData = query.data?.marketData ?? null;
  const hasStorageError = query.data?.hasStorageError ?? false;
  const loaded = !query.isPending;

  if (!loaded) {
    return (
      <section
        className="dashboard-panel"
        data-testid="portefeuille-realtime-section"
        data-state="loading"
      >
        <div className="panel-head">
          <h2>IBKR portefeuille</h2>
        </div>
        <div className="panel-body" aria-busy="true">
          <p>Bezig met laden…</p>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            <li
              style={{
                height: 24,
                background: "#e5e7eb",
                margin: "0.5rem 0",
                borderRadius: 4,
              }}
            />
            <li
              style={{
                height: 24,
                background: "#e5e7eb",
                margin: "0.5rem 0",
                borderRadius: 4,
              }}
            />
            <li
              style={{
                height: 24,
                background: "#e5e7eb",
                margin: "0.5rem 0",
                borderRadius: 4,
              }}
            />
          </ul>
        </div>
      </section>
    );
  }

  const isConnected = status?.connected === true;

  if (!isConnected) {
    return (
      <section
        className="dashboard-panel"
        data-testid="portefeuille-realtime-section"
        data-state="disconnected"
      >
        <div
          role="alert"
          style={{
            background: "#fef3c7",
            color: "#92400e",
            padding: "1rem 1.25rem",
            borderRadius: 6,
            border: "1px solid #fbbf24",
          }}
        >
          <strong>IBKR-verbinding ontbreekt.</strong>{" "}
          Controleer Instellingen of activeer de verbinding.
          {hasStorageError ? (
            <p style={{ marginTop: "0.5rem", marginBottom: 0 }}>
              De opslag is momenteel niet bereikbaar.
            </p>
          ) : null}
        </div>
      </section>
    );
  }

  return (
    <section
      className="dashboard-panel"
      data-testid="portefeuille-realtime-section"
      data-state="connected"
    >
      <div className="panel-head">
        <h2>IBKR portefeuille</h2>
      </div>
      <div className="panel-body">
        <CashSummaryCard cash={cash} />
        <PositionsGrid positions={positions} marketData={marketData} />
      </div>
    </section>
  );
}


function CashSummaryCard({
  cash,
}: {
  cash: IbkrCashLatestResponse | null;
}) {
  if (!cash || cash.items.length === 0) {
    return (
      <div
        data-testid="cash-summary-card"
        data-state="empty"
        style={{
          padding: "1rem",
          background: "#f3f4f6",
          borderRadius: 6,
          marginBottom: "1rem",
        }}
      >
        <h3 style={{ marginTop: 0 }}>Kassaldo</h3>
        <p>Niet beschikbaar — nog geen cash-snapshot opgeslagen.</p>
      </div>
    );
  }
  return (
    <div
      data-testid="cash-summary-card"
      data-state="populated"
      style={{
        padding: "1rem",
        background: "#f3f4f6",
        borderRadius: 6,
        marginBottom: "1rem",
      }}
    >
      <h3 style={{ marginTop: 0 }}>Kassaldo</h3>
      <p style={{ marginBottom: "0.5rem", color: "#374151" }}>
        Bijgewerkt: {formatTimestamp(cash.as_of)}
      </p>
      <table
        style={{ width: "100%", borderCollapse: "collapse" }}
        aria-label="Cash-overzicht per valuta"
      >
        <thead>
          <tr>
            <th style={cellHead}>Valuta</th>
            <th style={cellHead}>Beschikbare middelen</th>
            <th style={cellHead}>Netto liquidatie</th>
            <th style={cellHead}>Totale cash</th>
            <th style={cellHead}>Buying power</th>
          </tr>
        </thead>
        <tbody>
          {cash.items.map((row) => (
            <tr key={row.currency}>
              <td style={cellBody}>{row.currency}</td>
              <td style={cellBody}>
                {formatCashLabel(row.currency, row.available_funds)}
              </td>
              <td style={cellBody}>
                {formatCashLabel(row.currency, row.net_liquidation_value)}
              </td>
              <td style={cellBody}>
                {formatCashLabel(row.currency, row.total_cash_value)}
              </td>
              <td style={cellBody}>
                {formatCashLabel(row.currency, row.buying_power)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


function PositionsGrid({
  positions,
  marketData,
}: {
  positions: IbkrPositionsLatestResponse | null;
  marketData: MarketDataByAccountResponse | null;
}) {
  if (!positions || positions.items.length === 0) {
    return (
      <div data-testid="positions-grid" data-state="empty">
        <h3 style={{ marginTop: 0 }}>Posities</h3>
        <p>Geen posities in deze rekening.</p>
      </div>
    );
  }
  const byConid = new Map<string, MarketDataByAccountRow>();
  if (marketData) {
    for (const row of marketData.items) {
      byConid.set(row.ibkr_conid, row);
    }
  }
  const subtitle =
    marketData && marketData.as_of_date
      ? `Prijzen bijgewerkt: ${marketData.as_of_date} via ${marketData.fetched_via ?? "onbekend"}`
      : "Prijzen nog niet opgehaald";
  return (
    <div data-testid="positions-grid" data-state="populated">
      <h3 style={{ marginTop: 0 }}>Posities</h3>
      <p
        data-testid="positions-grid-subtitle"
        style={{ color: "#374151", marginTop: 0, marginBottom: "0.5rem" }}
      >
        {subtitle}
      </p>
      <table
        style={{ width: "100%", borderCollapse: "collapse" }}
        aria-label="IBKR posities"
      >
        <thead>
          <tr>
            <th style={cellHead}>Symbool</th>
            <th style={cellHead}>Beurs</th>
            <th style={cellHead}>Aantal</th>
            <th style={cellHead}>Gem. kostprijs</th>
            <th style={cellHead}>Huidige prijs</th>
            <th style={cellHead}>Waarde (EUR)</th>
            <th style={cellHead}>Niet-gerealiseerde W/V</th>
            <th style={cellHead}>Verversingsstatus</th>
            <th style={cellHead}>Verversingsdatum</th>
          </tr>
        </thead>
        <tbody>
          {positions.items.map((row) => {
            const md = row.conid ? byConid.get(row.conid) : undefined;
            const currentPrice =
              md?.close_local ?? row.market_price;
            const valueEur = md?.close_eur ?? row.market_value;
            return (
              <tr key={`${row.symbol}-${row.conid ?? "x"}`}>
                <td style={cellBody}>{row.symbol}</td>
                <td style={cellBody}>
                  {row.exchange ?? NIET_BESCHIKBAAR}
                </td>
                <td style={cellBody}>{formatNumber(row.quantity)}</td>
                <td style={cellBody}>{formatNumber(row.avg_cost)}</td>
                <td style={cellBody}>{formatNumber(currentPrice)}</td>
                <td style={cellBody}>{formatNumber(valueEur)}</td>
                <td style={cellBody}>{formatNumber(row.unrealized_pnl)}</td>
                <td style={cellBody}>
                  <PriceFreshnessBadge
                    freshness={md?.freshness ?? "unavailable"}
                  />
                </td>
                <td style={cellBody}>{formatTimestamp(row.as_of)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}


const cellHead: React.CSSProperties = {
  textAlign: "left",
  padding: "0.5rem",
  borderBottom: "1px solid #d1d5db",
  background: "#e5e7eb",
};

const cellBody: React.CSSProperties = {
  padding: "0.5rem",
  borderBottom: "1px solid #e5e7eb",
};
