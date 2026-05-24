"use client";

import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { StatusBadge } from "@/components/StatusBadge";
import { PositionPlTraceDetails } from "@/components/PositionPlTraceDetails";
import { ValuationTraceDetails } from "@/components/ValuationTraceDetails";
import {
  apiClient,
  AssetActionDraftResponse,
  AssetDecisionPackageResponse,
  AssetForecastResponse,
  AssetSuggestionResponse,
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
  const [forecasts, setForecasts] = useState<AssetForecastResponse[]>([]);
  const [suggestions, setSuggestions] = useState<AssetSuggestionResponse[]>([]);
  const [decisionPackages, setDecisionPackages] = useState<AssetDecisionPackageResponse[]>([]);
  const [actionDrafts, setActionDrafts] = useState<AssetActionDraftResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const loadData = async () => {
    setLoading(true);
    const [statusRes, valuationRes, positionsRes, cashRes, ordersRes, executionsRes, forecastsRes, suggestionsRes, decisionPackagesRes, actionDraftsRes] = await Promise.all([
      apiClient.getIbkrSyncStatus(),
      apiClient.getPortfolioValuationReadiness(),
      apiClient.getIbkrPositions(),
      apiClient.getIbkrCash(),
      apiClient.getIbkrOpenOrders(),
      apiClient.getIbkrExecutions(),
      apiClient.getLatestForecasts(),
      apiClient.getLatestSuggestions(),
      apiClient.getLatestDecisionPackages(),
      apiClient.getLatestActionDrafts(),
    ]);

    setLoadFailed(!statusRes.ok && !valuationRes.ok && !positionsRes.ok && !cashRes.ok && !ordersRes.ok && !executionsRes.ok);
    if (statusRes.ok) setSyncStatus(statusRes.data);
    if (valuationRes.ok) setValuationReadiness(valuationRes.data);
    if (positionsRes.ok) setPositions(positionsRes.data.items ?? []);
    if (cashRes.ok) setCashItems(cashRes.data.items ?? []);
    if (ordersRes.ok) setOpenOrders(ordersRes.data.items ?? []);
    if (executionsRes.ok) setExecutions(executionsRes.data.items ?? []);
    if (forecastsRes.ok) setForecasts(forecastsRes.data.items ?? []);
    if (suggestionsRes.ok) setSuggestions(suggestionsRes.data.items ?? []);
    if (decisionPackagesRes.ok) setDecisionPackages(decisionPackagesRes.data.items ?? []);
    if (actionDraftsRes.ok) setActionDrafts(actionDraftsRes.data.items ?? []);
    setLoading(false);
  };

  const forecastBySymbol = useMemo(() => {
    const map: Record<string, AssetForecastResponse> = {};
    for (const forecast of forecasts) {
      // Latest forecast per symbol — items are already keyed by conid on the
      // backend, but on the web side we join by symbol to keep the read model
      // shape simple for V1.
      map[forecast.symbol] = forecast;
    }
    return map;
  }, [forecasts]);

  const forecastTone = (forecast: AssetForecastResponse | undefined): "ok" | "info" | "wacht" | "aandacht" | "geblokkeerd" => {
    if (!forecast || forecast.status !== "ready") return "info";
    const label = forecast.direction_label;
    if (label === "strong_up" || label === "slight_up") return "ok";
    if (label === "strong_down") return "geblokkeerd";
    if (label === "slight_down") return "aandacht";
    return "info";
  };

  const suggestionBySymbol = useMemo(() => {
    const map: Record<string, AssetSuggestionResponse> = {};
    for (const suggestion of suggestions) {
      map[suggestion.symbol] = suggestion;
    }
    return map;
  }, [suggestions]);

  const suggestionTone = (suggestion: AssetSuggestionResponse | undefined): "ok" | "info" | "wacht" | "aandacht" | "geblokkeerd" => {
    if (!suggestion) return "info";
    if (suggestion.status === "blocked") return "geblokkeerd";
    if (suggestion.status === "control_needed") return "wacht";
    switch (suggestion.action_label) {
      case "Kopen":
      case "Langzaam bijkopen":
        return "ok";
      case "Verkopen":
      case "Verminderen":
      case "Vermijden":
        return "aandacht";
      case "Geblokkeerd":
        return "geblokkeerd";
      case "Bekijken":
        return "wacht";
      default:
        return "info";
    }
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
          <table className="portfolio-table"><thead><tr><th>Asset / symbool</th><th>Type</th><th>Beurs</th><th>Valuta</th><th>Aantal</th><th>Gem. aankoopprijs</th><th>Laatste sync</th><th>Verwachte richting (1m)</th><th>Actie</th><th>Status</th></tr></thead><tbody>
            {positions.map((position, idx) => {
              const forecast = forecastBySymbol[position.symbol];
              const fTone = forecastTone(forecast);
              const directionLabel = forecast ? forecast.direction_label_nl : "Nog geen voorspelling";
              const directionTooltip = forecast
                ? `Baseline GBM • p10 ${forecast.p10_price} / p50 ${forecast.p50_price} / p90 ${forecast.p90_price} • kans op stijging ${forecast.prob_gain} • horizon ${forecast.horizon_days} dagen. Read-only baseline; geen suggesties of orders.`
                : "Geen voorspelling beschikbaar. Geen suggesties of orders.";

              const suggestion = suggestionBySymbol[position.symbol];
              const sTone = suggestionTone(suggestion);
              const actionLabel = suggestion ? suggestion.action_label_nl : "Nog geen advies";
              const actionTooltip = suggestion
                ? `${suggestion.rationale_nl} • Vertrouwen: ${suggestion.confidence_label_nl} (${suggestion.confidence_score}) • Risicoprofiel ${suggestion.risk_profile}. Geen action drafts of orders.`
                : "Geen suggestie beschikbaar. Geen action drafts of orders.";

              return (
                <tr key={`${position.sync_run_id}-${position.symbol}-${idx}`}>
                  <td>{position.symbol}</td>
                  <td>{position.security_type}</td>
                  <td>{displayValue(position.exchange)}</td>
                  <td>{position.currency}</td>
                  <td>{position.quantity}</td>
                  <td>{displayValue(position.average_cost)}</td>
                  <td>{displayValue(position.timestamp)}</td>
                  <td><StatusBadge label={directionLabel} status={fTone} title={directionTooltip} /></td>
                  <td><StatusBadge label={actionLabel} status={sTone} title={actionTooltip} /></td>
                  <td><StatusBadge label="Read-only" status="info" title="Snapshot uit IBKR-sync." /></td>
                </tr>
              );
            })}
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

      <section className="dashboard-panel">
        <h2>Action drafts (LMT / DAY / hele aandelen)</h2>
        <p className="top-sub">Bewerkbare drafts met Orderimpact en dry-run. Geen broker submission in deze fase.</p>
        {actionDrafts.length === 0 ? (
          <EmptyState
            title="Nog geen action drafts"
            message="Voer eerst decision-packages-sync uit en daarna action-drafts-sync."
          />
        ) : (
          <table className="portfolio-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Action</th>
                <th>Aantal</th>
                <th>Limit</th>
                <th>Orderwaarde</th>
                <th>Cash voor → na</th>
                <th>Positie voor → na</th>
                <th>Gewicht na</th>
                <th>Dry-run</th>
              </tr>
            </thead>
            <tbody>
              {actionDrafts.map((draft) => {
                const dryRunTone: "ok" | "info" | "wacht" | "aandacht" | "geblokkeerd" =
                  draft.dry_run_status === "passed" ? "ok" :
                  draft.dry_run_status === "failed" ? "geblokkeerd" : "info";
                const dryRunLabel = draft.dry_run_status === "passed" ? "Geslaagd" :
                  draft.dry_run_status === "failed" ? "Mislukt" : draft.dry_run_status;
                const dryRunTooltip = draft.dry_run_failures.length > 0
                  ? `Failures: ${draft.dry_run_failures.join(", ")}. Geen submission mogelijk.`
                  : `Onderbouwing: ${draft.rationale_nl}. Geen submission in deze fase.`;
                return (
                  <tr key={draft.draft_id}>
                    <td>{draft.symbol} ({draft.currency})</td>
                    <td>{draft.action_side} {draft.order_type}/{draft.tif}</td>
                    <td>{draft.quantity}</td>
                    <td>{draft.limit_price}</td>
                    <td>{displayValue(draft.estimated_order_value)}</td>
                    <td>{displayValue(draft.estimated_cash_before)} → {displayValue(draft.estimated_cash_after)}</td>
                    <td>{displayValue(draft.estimated_position_quantity_before)} → {displayValue(draft.estimated_position_quantity_after)}</td>
                    <td>{draft.estimated_portfolio_weight_after_pct ? `${draft.estimated_portfolio_weight_after_pct}%` : "Niet beschikbaar"}</td>
                    <td><StatusBadge label={dryRunLabel} status={dryRunTone} title={dryRunTooltip} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>

      <section className="dashboard-panel">
        <h2>Decision Packages</h2>
        <p className="top-sub">Immutable evidence-bundels die elke suggestion ondersteunen. Geen action drafts, geen orders.</p>
        {decisionPackages.length === 0 ? (
          <EmptyState
            title="Nog geen Decision Packages"
            message="Voer eerst suggesties-sync uit en daarna decision-packages-sync."
          />
        ) : (
          <div className="portfolio-meta-grid" style={{ gap: "1rem" }}>
            {decisionPackages.map((dp) => (
              <details
                key={dp.decision_package_id}
                style={{
                  border: "1px solid var(--ata-border, #334155)",
                  borderRadius: "0.5rem",
                  padding: "0.75rem 1rem",
                  background: "var(--ata-surface, transparent)",
                }}
              >
                <summary style={{ cursor: "pointer", fontWeight: 600 }}>
                  {dp.symbol} — {dp.suggestion_action_label_nl} (vertrouwen {dp.suggestion_confidence_label_nl})
                </summary>
                <div style={{ marginTop: "0.75rem", display: "grid", gap: "0.25rem", fontSize: "0.92rem" }}>
                  <div><strong>Gegenereerd:</strong> {displayValue(dp.generated_at)}</div>
                  <div><strong>Geldig tot:</strong> {displayValue(dp.valid_until)}</div>
                  <div><strong>Risicoprofiel:</strong> {dp.risk_profile}</div>
                  <div><strong>Conid:</strong> {dp.ibkr_conid} • <strong>Valuta:</strong> {dp.currency}</div>
                  <div><strong>Status:</strong> {dp.status}{dp.blocking_reason ? ` (${dp.blocking_reason})` : ""}</div>
                  <div><strong>Huidige prijs (markt):</strong> {displayValue(dp.market_last_price)} ({displayValue(dp.market_freshness_status)}, {displayValue(dp.market_provider_code)})</div>
                  <div>
                    <strong>Voorspelling:</strong>{" "}
                    p10 {displayValue(dp.forecast_p10_price)} /
                    p50 {displayValue(dp.forecast_p50_price)} /
                    p90 {displayValue(dp.forecast_p90_price)} •
                    kans op stijging {displayValue(dp.forecast_prob_gain)} •
                    horizon {displayValue(dp.forecast_horizon_days?.toString() ?? null)} dagen
                  </div>
                  <div><strong>Positie:</strong> {dp.has_position ? `${displayValue(dp.position_quantity)} stuks @ kost ${displayValue(dp.position_average_cost)}` : "Niet aangehouden"}</div>
                  <div><strong>Cash:</strong> {dp.cash_amount ? `${dp.cash_base_currency} ${dp.cash_amount}` : "Niet beschikbaar"}</div>
                  {dp.fx_pair ? <div><strong>FX {dp.fx_pair}:</strong> {dp.fx_rate} ({dp.fx_freshness_status})</div> : null}
                  <div><strong>Onderbouwing:</strong> {dp.rationale_nl}</div>
                  <div><strong>Toelichting:</strong> {dp.explanation_nl}</div>
                  <div><strong>Gate-uitkomsten:</strong> {dp.gate_outcomes.length > 0 ? dp.gate_outcomes.join(" • ") : "Geen"}</div>
                  <div><strong>Audit links:</strong> {dp.audit_links.length > 0 ? dp.audit_links.join(" • ") : "Geen"}</div>
                  <div style={{ fontSize: "0.82rem", opacity: 0.7 }}><strong>Content-hash:</strong> {dp.content_hash}</div>
                </div>
              </details>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
