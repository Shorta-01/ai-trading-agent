"use client";

import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { StatusBadge } from "@/components/StatusBadge";
import { PositionPlTraceDetails } from "@/components/PositionPlTraceDetails";
import { ValuationTraceDetails } from "@/components/ValuationTraceDetails";
import {
  apiClient,
  IbkrCashSnapshot,
  IbkrExecutionSnapshot,
  IbkrOpenOrderSnapshot,
  IbkrPositionSnapshot,
  IbkrSyncStatusResponse,
  PortfolioValuationReadinessRow,
  PortfolioValuationReadinessResponse,
} from "@/lib/apiClient";

function displayValue(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "Niet beschikbaar";
}

function formatValuationValue(baseCurrency: string | null, value: string | null, available: boolean): string {
  if (!available || !value) return "Niet beschikbaar: veilige totaalwaarde ontbreekt.";
  return baseCurrency ? `${baseCurrency} ${value}` : value;
}

function formatReadinessAmount(
  currency: string | null,
  value: string | null,
  available: boolean,
  helpText: string,
): string {
  if (!available || !value) {
    return helpText || "Niet beschikbaar: veilige waarde ontbreekt.";
  }
  return currency ? `${currency} ${value}` : value;
}

function formatMissingInputs(row: PortfolioValuationReadinessRow): string {
  const missing = [...row.missing_cost_basis_inputs, ...row.missing_pl_inputs];
  if (missing.length === 0) {
    return "Geen ontbrekende invoer";
  }
  return missing.join(", ");
}

export default function PortfolioPage() {
  const [syncStatus, setSyncStatus] = useState<IbkrSyncStatusResponse | null>(null);
  const [valuationReadiness, setValuationReadiness] = useState<PortfolioValuationReadinessResponse | null>(null);
  const [positions, setPositions] = useState<IbkrPositionSnapshot[]>([]);
  const [cashItems, setCashItems] = useState<IbkrCashSnapshot[]>([]);
  const [openOrders, setOpenOrders] = useState<IbkrOpenOrderSnapshot[]>([]);
  const [executions, setExecutions] = useState<IbkrExecutionSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const loadData = async () => {
    setLoading(true);
    const [statusRes, valuationRes, positionsRes, cashRes, ordersRes, executionsRes] = await Promise.all([
      apiClient.getIbkrSyncStatus(),
      apiClient.getPortfolioValuationReadiness(),
      apiClient.getIbkrPositions(),
      apiClient.getIbkrCash(),
      apiClient.getIbkrOpenOrders(),
      apiClient.getIbkrExecutions(),
    ]);

    setLoadFailed(!statusRes.ok && !valuationRes.ok && !positionsRes.ok && !cashRes.ok && !ordersRes.ok && !executionsRes.ok);
    if (statusRes.ok) setSyncStatus(statusRes.data);
    if (valuationRes.ok) setValuationReadiness(valuationRes.data);
    if (positionsRes.ok) setPositions(positionsRes.data.items ?? []);
    if (cashRes.ok) setCashItems(cashRes.data.items ?? []);
    if (ordersRes.ok) setOpenOrders(ordersRes.data.items ?? []);
    if (executionsRes.ok) setExecutions(executionsRes.data.items ?? []);
    setLoading(false);
  };

  useEffect(() => {
    void loadData();
  }, []);

  const statusTone = useMemo(() => {
    if (!syncStatus?.configured) return "aandacht" as const;
    if (syncStatus.status_nl.toLowerCase().includes("mislukt")) return "geblokkeerd" as const;
    if (syncStatus.status_nl.toLowerCase().includes("nog niet")) return "wacht" as const;
    return "ok" as const;
  }, [syncStatus]);

  const valuationStatusTone = useMemo(() => {
    if (!valuationReadiness) return "niet-beschikbaar" as const;
    if (valuationReadiness.conversion_total_status.includes("blocked")) return "geblokkeerd" as const;
    if (valuationReadiness.conversion_total_status.includes("control_needed")) return "aandacht" as const;
    if (valuationReadiness.conversion_total_status === "conversion_ready") return "ok" as const;
    if (valuationReadiness.conversion_total_status === "conversion_not_required") return "info" as const;
    return "wacht" as const;
  }, [valuationReadiness]);

  const runSync = async () => {
    setSyncing(true);
    await apiClient.runIbkrSync();
    await loadData();
    setSyncing(false);
  };

  return (
    <main className="page-wrap">
      <section className="dashboard-panel">
        <div className="panel-head">
          <h2>Portefeuille</h2>
          <button className="sync-button" type="button" onClick={() => void runSync()} disabled={syncing}>
            {syncing ? "Synchroniseren..." : "Synchroniseer snapshots"}
          </button>
        </div>
        <p className="top-sub">Read-only weergave van laatst opgeslagen IBKR snapshots voor posities, cash, open orders en uitvoeringen.</p>

        {loading ? <EmptyState title="Waardering laden" message="Even wachten, er worden geen waarden verzonnen." /> : null}
        {!loading && !valuationReadiness ? <EmptyState title="Waardering niet beschikbaar" message="De waarderingsstatus kon niet worden opgehaald. Er worden geen waarden verzonnen." /> : null}
        {valuationReadiness ? (
          <div className="portfolio-meta-grid" style={{ marginBottom: "1rem" }}>
            <div><strong>Totale portefeuillewaarde:</strong> {formatValuationValue(valuationReadiness.base_currency, valuationReadiness.total_portfolio_value, valuationReadiness.total_portfolio_value_available)} <em>— Som van veilige marktwaarde en cashwaarde in basismunt, alleen als invoer compleet en veilig is.</em></div>
            <div><strong>Totale marktwaarde:</strong> {formatValuationValue(valuationReadiness.base_currency, valuationReadiness.total_market_value, valuationReadiness.total_market_value_available)} <em>— Marktwaarde uit opgeslagen snapshots; geen browserberekening.</em></div>
            <div><strong>Cashwaarde:</strong> {formatValuationValue(valuationReadiness.base_currency, valuationReadiness.total_cash_value, valuationReadiness.total_cash_value_available)} <em>— Cash uit opgeslagen accountsnapshot; geen verzonnen fallback.</em></div>
            <div><strong>Basismunt:</strong> {displayValue(valuationReadiness.base_currency)} <em>— Valuta waarin totalen worden getoond als omrekening veilig beschikbaar is.</em></div>
            <div><strong>Omrekening:</strong> <StatusBadge label={valuationReadiness.conversion_total_status_nl} status={valuationStatusTone} title="Status van omzetting naar basismunt op basis van opgeslagen wisselkoersen." /> <em>— Status van omzetting naar basismunt op basis van opgeslagen wisselkoersen.</em></div>
            <div><strong>Toelichting:</strong> {valuationReadiness.conversion_total_help_nl || "Niet beschikbaar: controle en herkomst ontbreken."}</div>
          </div>
        ) : null}
        {valuationReadiness ? <ValuationTraceDetails readiness={valuationReadiness} /> : null}

        <div className="portfolio-meta-grid">
          <div><strong>Status:</strong> <StatusBadge label={syncStatus?.status_nl ?? "Niet beschikbaar"} status={statusTone} title={syncStatus?.help_nl ?? "Nog geen syncstatus."} /></div>
          <div><strong>Laatste sync:</strong> {displayValue(syncStatus?.last_sync_at)}</div>
          <div><strong>Posities:</strong> {syncStatus?.positions_count ?? positions.length}</div>
          <div><strong>Cash snapshot:</strong> {syncStatus?.cash_available ? "Beschikbaar" : "Niet beschikbaar"}</div>
          <div><strong>Open orders:</strong> {syncStatus?.open_orders_count ?? openOrders.length}</div>
          <div><strong>Executions/fills:</strong> {syncStatus?.executions_count ?? executions.length}</div>
        </div>
      </section>

      {loading ? <EmptyState title="Laden..." message="IBKR snapshots worden opgehaald." /> : null}
      {!loading && loadFailed ? <EmptyState title="Sync mislukt. Controleer de IBKR-koppeling." message="Nog geen IBKR-sync uitgevoerd" /> : null}

      <section className="dashboard-panel">
        <h2>Posities</h2>
        {positions.length === 0 ? <EmptyState title="Geen posities gevonden in de laatste snapshot" message="Nog geen IBKR-sync uitgevoerd" /> : (
          <table className="portfolio-table"><thead><tr><th>Asset / symbool</th><th>Type</th><th>Beurs</th><th>Valuta</th><th>Aantal</th><th>Gem. aankoopprijs</th><th>Laatste sync</th><th>Status</th></tr></thead><tbody>
            {positions.map((position, idx) => (
              <tr key={`${position.sync_run_id}-${position.symbol}-${idx}`}><td>{position.symbol}</td><td>{position.security_type}</td><td>{displayValue(position.exchange)}</td><td>{position.currency}</td><td>{position.quantity}</td><td>{displayValue(position.average_cost)}</td><td>{displayValue(position.timestamp)}</td><td><StatusBadge label="Read-only" status="info" title="Snapshot uit IBKR-sync." /></td></tr>
            ))}
          </tbody></table>
        )}
      </section>

      <section className="dashboard-panel">
        <h2>Kostbasis en winst/verlies</h2>
        {!valuationReadiness ? (
          <EmptyState title="Nog geen kostbasis- of winst/verliesgegevens" message="De readiness-gegevens zijn niet beschikbaar. Er worden geen waarden verzonnen." />
        ) : valuationReadiness.rows.length === 0 ? (
          <EmptyState title="Nog geen kostbasis- of winst/verliesgegevens beschikbaar" message="Er worden geen waarden verzonnen." />
        ) : (
          <table className="portfolio-table">
            <thead>
              <tr>
                <th>Asset / symbool</th>
                <th>Valuta</th>
                <th>Aantal</th>
                <th>Kostbasis</th>
                <th>Status kostbasis</th>
                <th>Ongerealiseerde winst/verlies</th>
                <th>Winst/verlies %</th>
                <th>Status winst/verlies</th>
                <th>Ontbrekende invoer</th>
                <th>Toelichting</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {valuationReadiness.rows.map((row, idx) => (
                <tr key={`${row.conid ?? row.symbol ?? "row"}-${idx}`}>
                  <td>{displayValue(row.symbol)}</td>
                  <td>{displayValue(row.currency)}</td>
                  <td>{displayValue(row.quantity)}</td>
                  <td>{formatReadinessAmount(row.cost_basis_currency, row.cost_basis, row.cost_basis_available, row.cost_basis_help_nl)}</td>
                  <td>{row.cost_basis_status_nl || "Controle nodig"}</td>
                  <td>{formatReadinessAmount(row.unrealized_pl_currency, row.unrealized_pl, row.unrealized_pl_available, row.unrealized_pl_help_nl)}</td>
                  <td>{formatReadinessAmount(null, row.unrealized_pl_percent, row.unrealized_pl_percent_available, row.unrealized_pl_help_nl)}</td>
                  <td>{row.unrealized_pl_status_nl || "Controle nodig"}</td>
                  <td>{formatMissingInputs(row)}</td>
                  <td>{row.cost_basis_help_nl || row.unrealized_pl_help_nl || "Controle nodig"}</td>
                  <td><PositionPlTraceDetails row={row} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="dashboard-panel">
        <h2>Cash</h2>
        {cashItems.length === 0 ? <EmptyState title="Cashgegevens niet beschikbaar" message="Nog geen IBKR-sync uitgevoerd" /> : cashItems.slice(0, 1).map((cash) => (
          <div key={`${cash.sync_run_id}-${cash.account_ref}`} className="portfolio-meta-grid">
            <div><strong>Basisvaluta:</strong> {cash.base_currency}</div>
            <div><strong>Cash:</strong> {cash.cash}</div>
            <div><strong>Available funds:</strong> {displayValue(cash.available_funds)}</div>
            <div><strong>Buying power:</strong> {displayValue(cash.buying_power)}</div>
            <div><strong>Laatste sync:</strong> {displayValue(cash.timestamp)}</div>
            <div><strong>Status:</strong> Snapshot beschikbaar</div>
          </div>
        ))}
      </section>

      <section className="dashboard-panel">
        <h2>Open orders</h2>
        {openOrders.length === 0 ? <EmptyState title="Open orders verschijnen hier na sync" message="Nog geen IBKR-sync uitgevoerd" /> : (
          <table className="portfolio-table"><thead><tr><th>Order-ID</th><th>Symbool</th><th>Koop/verkoop</th><th>Ordertype</th><th>Aantal</th><th>Status</th><th>Gevuld</th><th>Resterend</th><th>Laatste status</th></tr></thead><tbody>
            {openOrders.map((order) => (
              <tr key={`${order.sync_run_id}-${order.ibkr_order_id}`}><td>{order.ibkr_order_id}</td><td>{order.symbol}</td><td>{displayValue(order.action_side)}</td><td>{displayValue(order.order_type)}</td><td>{order.quantity}</td><td>{order.status}</td><td>{order.filled_quantity}</td><td>{order.remaining_quantity}</td><td>{displayValue(order.last_status_at)}</td></tr>
            ))}
          </tbody></table>
        )}
      </section>

      <section className="dashboard-panel">
        <h2>Executions/fills</h2>
        {executions.length === 0 ? <EmptyState title="Uitvoeringen/fills verschijnen hier na sync" message="Nog geen IBKR-sync uitgevoerd" /> : (
          <table className="portfolio-table"><thead><tr><th>Execution-ID</th><th>Symbool</th><th>Koop/verkoop</th><th>Aantal</th><th>Prijs</th><th>Tijd</th><th>Valuta</th></tr></thead><tbody>
            {executions.map((execution) => (
              <tr key={`${execution.sync_run_id}-${execution.execution_id}`}><td>{execution.execution_id}</td><td>{execution.symbol}</td><td>{execution.side}</td><td>{execution.quantity}</td><td>{execution.price}</td><td>{execution.execution_time}</td><td>{execution.currency}</td></tr>
            ))}
          </tbody></table>
        )}
      </section>
    </main>
  );
}
