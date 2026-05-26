"use client";

import { useEffect, useMemo, useState } from "react";

import { CalibrationCoverageBadge } from "@/components/CalibrationCoverageBadge";
import { ChartPlaceholder } from "@/components/ChartPlaceholder";
import { ForecastDaySummaryWidget } from "@/components/ForecastDaySummaryWidget";
import { ReconciliationStatusWidget } from "@/components/ReconciliationStatusWidget";
import { DashboardPanel } from "@/components/DashboardPanel";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { SchedulerStatusBadge } from "@/components/SchedulerStatusBadge";
import { StatusCard } from "@/components/StatusCard";
import { SyncStatusBadge } from "@/components/SyncStatusBadge";
import { UiStatus } from "@/components/StatusBadge";
import { apiClient, IbkrStatusResponse, IbkrSyncStatusResponse, PortfolioValuationReadinessResponse, SystemStatusSummary } from "@/lib/apiClient";

function formatValuationValue(baseCurrency: string | null, value: string | null, available: boolean): string {
  if (!available || !value) {
    return "Niet beschikbaar: veilige totaalwaarde ontbreekt.";
  }
  return baseCurrency ? `${baseCurrency} ${value}` : value;
}

function getValuationDisplayStatus(readiness: PortfolioValuationReadinessResponse | null): UiStatus {
  if (!readiness) return "niet-beschikbaar";
  if (readiness.conversion_total_status.includes("blocked")) return "geblokkeerd";
  if (readiness.conversion_total_status.includes("control_needed")) return "aandacht";
  if (readiness.conversion_total_status === "conversion_not_required") return "info";
  if (readiness.conversion_total_status === "conversion_ready") return "ok";
  return "wacht";
}

export default function HomePage() {
  const [systemStatus, setSystemStatus] = useState<SystemStatusSummary | null>(null);
  const [ibkrStatus, setIbkrStatus] = useState<IbkrStatusResponse | null>(null);
  const [ibkrSyncStatus, setIbkrSyncStatus] = useState<IbkrSyncStatusResponse | null>(null);
  const [valuationReadiness, setValuationReadiness] = useState<PortfolioValuationReadinessResponse | null>(null);
  const [valuationLoading, setValuationLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const [system, ibkr, ibkrSync, valuation] = await Promise.all([
        apiClient.getSystemStatus(),
        apiClient.getIbkrStatus(),
        apiClient.getIbkrSyncStatus(),
        apiClient.getPortfolioValuationReadiness(),
      ]);
      setSystemStatus(system.ok ? system.data : null);
      setIbkrStatus(ibkr.ok ? ibkr.data : null);
      setIbkrSyncStatus(ibkrSync.ok ? ibkrSync.data : null);
      setValuationReadiness(valuation.ok ? valuation.data : null);
      setValuationLoading(false);
    }
    void load();
  }, []);

  const syncLabel = useMemo(() => {
    if (!ibkrStatus) return { label: "Niet beschikbaar", status: "niet-beschikbaar" as const, help: "IBKR-status nog niet bereikbaar." };
    if (ibkrStatus.configured) return { label: "Wacht op gegevens", status: "wacht" as const, help: ibkrStatus.message_nl };
    return { label: "Nog geen IBKR-sync", status: "aandacht" as const, help: ibkrStatus.message_nl };
  }, [ibkrStatus]);

  const valuationStatus = getValuationDisplayStatus(valuationReadiness);
  return (
    <main className="page-wrap">
      <section style={{ marginBottom: "0.75rem", display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <SchedulerStatusBadge />
        <CalibrationCoverageBadge />
      </section>
      <section style={{ marginBottom: "0.75rem" }}>
        <ForecastDaySummaryWidget />
      </section>
      <section style={{ marginBottom: "0.75rem" }}>
        <ReconciliationStatusWidget />
      </section>
      <section className="metrics-grid">
        <MetricCard
          title="Totale portefeuillewaarde"
          value={valuationLoading ? "Laden..." : formatValuationValue(valuationReadiness?.base_currency ?? null, valuationReadiness?.total_portfolio_value ?? null, valuationReadiness?.total_portfolio_value_available ?? false)}
          status={valuationLoading ? "wacht" : valuationStatus}
          help={valuationLoading ? "Som van veilige marktwaarde en cashwaarde in basismunt, alleen als invoer compleet en veilig is." : "Som van veilige marktwaarde en cashwaarde in basismunt, alleen als invoer compleet en veilig is."}
        />
        <MetricCard title="Dagresultaat" value="Niet beschikbaar" status="niet-beschikbaar" help="Deze waarde verschijnt zodra echte gegevens beschikbaar zijn." />
        <MetricCard title="Totaal resultaat" value="Niet beschikbaar" status="niet-beschikbaar" help="Deze waarde verschijnt zodra echte gegevens beschikbaar zijn." />
        <MetricCard
          title="Cashwaarde"
          value={valuationLoading ? "Laden..." : formatValuationValue(valuationReadiness?.base_currency ?? null, valuationReadiness?.total_cash_value ?? null, valuationReadiness?.total_cash_value_available ?? false)}
          status={valuationLoading ? "wacht" : valuationStatus}
          help={"Cash uit opgeslagen accountsnapshot; geen verzonnen fallback."}
        />
        <MetricCard title="Actieve suggesties" value="Niet beschikbaar" status="niet-beschikbaar" help="Suggestion runtime bestaat nog niet." />
        <MetricCard title="Te keuren acties" value="Niet beschikbaar" status="niet-beschikbaar" help="Action-draft runtime bestaat nog niet." />
      </section>

      <div className="dashboard-layout">
        <DashboardPanel title="Portefeuille-evolutie" help="Toont later waarde-evolutie, winst/verlies en markeringen voor koop/verkoop.">
          <ChartPlaceholder text="Portefeuille-evolutie verschijnt hier na IBKR-sync en marktdataverwerking." />
        </DashboardPanel>

        <DashboardPanel title="Waardering" help="Read-only status op basis van opgeslagen readiness-gegevens; geen browserberekening.">
          {valuationLoading ? <EmptyState title="Waardering laden" message="Even wachten, er worden geen waarden verzonnen." /> : null}
          {!valuationLoading && !valuationReadiness ? <EmptyState title="Waardering niet beschikbaar" message="De waarderingsstatus kon niet worden opgehaald. Er worden geen waarden verzonnen." /> : null}
          {valuationReadiness ? (
            <div className="status-list">
              <StatusCard title="Totale marktwaarde" description={"Marktwaarde uit opgeslagen snapshots; geen browserberekening."} statusLabel={formatValuationValue(valuationReadiness.base_currency, valuationReadiness.total_market_value, valuationReadiness.total_market_value_available)} status={valuationStatus} />
              <StatusCard title="Cashwaarde" description={"Cash uit opgeslagen accountsnapshot; geen verzonnen fallback."} statusLabel={formatValuationValue(valuationReadiness.base_currency, valuationReadiness.total_cash_value, valuationReadiness.total_cash_value_available)} status={valuationStatus} />
              <StatusCard title="Omrekening" description={"Status van omzetting naar basismunt op basis van opgeslagen wisselkoersen."} statusLabel={valuationReadiness.conversion_total_status_nl} status={valuationStatus} />
            </div>
          ) : null}
        </DashboardPanel>

        <DashboardPanel title="Synchronisatie en status" help="Toont actuele status zonder fake succesmeldingen.">
          <StatusCard title="IBKR synchronisatie" description={ibkrSyncStatus ? `Posities: ${ibkrSyncStatus.positions_count} · Open orders: ${ibkrSyncStatus.open_orders_count} · Executies: ${ibkrSyncStatus.executions_count}` : syncLabel.help} statusLabel={syncLabel.label} status={syncLabel.status} />
          <div className="sync-badges">
            <SyncStatusBadge label="Accountmodus" status="vergrendeld" help="Alleen paper-modus is toegestaan." />
            <SyncStatusBadge label="Marktdata" status="niet-beschikbaar" help="Runtime nog niet geïmplementeerd." />
            <SyncStatusBadge label="Suggesties" status="geblokkeerd" help="Suggestion runtime bestaat nog niet." />
            <SyncStatusBadge label="AI-briefing" status="geblokkeerd" help="AI runtime bestaat nog niet." />
          </div>
        </DashboardPanel>

        <DashboardPanel title="Systeemstatus" help="Samenvatting van huidige foundations.">
          <div className="status-list">
            {systemStatus?.services.map((service) => (
              <StatusCard
                key={service.key}
                title={service.label_nl}
                description={service.help_nl}
                statusLabel={service.status_nl}
                status={service.status_key === "active" ? "ok" : service.status_key === "error" ? "aandacht" : "wacht"}
              />
            )) ?? <EmptyState title="Status niet beschikbaar" message="Wacht op gegevens." />}
          </div>
        </DashboardPanel>
      </div>
    </main>
  );
}
