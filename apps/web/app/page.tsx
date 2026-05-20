"use client";

import { useEffect, useMemo, useState } from "react";

import { ChartPlaceholder } from "@/components/ChartPlaceholder";
import { DashboardPanel } from "@/components/DashboardPanel";
import { EmptyState } from "@/components/EmptyState";
import { MetricCard } from "@/components/MetricCard";
import { StatusCard } from "@/components/StatusCard";
import { SyncStatusBadge } from "@/components/SyncStatusBadge";
import { apiClient, IbkrStatusResponse, IbkrSyncStatusResponse, SystemStatusSummary } from "@/lib/apiClient";

const metrics = [
  "Totale portefeuillewaarde",
  "Dagresultaat",
  "Totaal resultaat",
  "Beschikbare cash",
  "Actieve suggesties",
  "Te keuren acties",
] as const;

export default function HomePage() {
  const [systemStatus, setSystemStatus] = useState<SystemStatusSummary | null>(null);
  const [ibkrStatus, setIbkrStatus] = useState<IbkrStatusResponse | null>(null);
  const [ibkrSyncStatus, setIbkrSyncStatus] = useState<IbkrSyncStatusResponse | null>(null);

  useEffect(() => {
    async function load() {
      const [system, ibkr, ibkrSync] = await Promise.all([apiClient.getSystemStatus(), apiClient.getIbkrStatus(), apiClient.getIbkrSyncStatus()]);
      setSystemStatus(system.ok ? system.data : null);
      setIbkrStatus(ibkr.ok ? ibkr.data : null);
      setIbkrSyncStatus(ibkrSync.ok ? ibkrSync.data : null);
    }
    void load();
  }, []);

  const syncLabel = useMemo(() => {
    if (!ibkrStatus) return { label: "Niet beschikbaar", status: "niet-beschikbaar" as const, help: "IBKR-status nog niet bereikbaar." };
    if (ibkrStatus.configured) return { label: "Wacht op gegevens", status: "wacht" as const, help: ibkrStatus.message_nl };
    return { label: "Nog geen IBKR-sync", status: "aandacht" as const, help: ibkrStatus.message_nl };
  }, [ibkrStatus]);

  return (
    <main className="page-wrap">
      <section className="metrics-grid">
        {metrics.map((title) => (
          <MetricCard key={title} title={title} value="Niet beschikbaar" status="niet-beschikbaar" help="Deze waarde verschijnt zodra echte gegevens beschikbaar zijn." />
        ))}
      </section>

      <div className="dashboard-layout">
        <DashboardPanel title="Portefeuille-evolutie" help="Toont later waarde-evolutie, winst/verlies en markeringen voor koop/verkoop.">
          <ChartPlaceholder text="Portefeuille-evolutie verschijnt hier na IBKR-sync en marktdataverwerking." />
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

        <DashboardPanel title="Samenstelling" help="Toont later verdeling per asset, sector, valuta en cash/invested.">
          <EmptyState title="Nog leeg" message="Samenstelling verschijnt na portfolio-sync." />
        </DashboardPanel>

        <DashboardPanel title="Suggesties en aandacht" help="Toont later actieve, geblokkeerde en verlopen suggesties plus te keuren acties.">
          <EmptyState title="Nog geen suggesties" message="Nog geen suggesties beschikbaar." />
        </DashboardPanel>

        <DashboardPanel title="Dagelijkse briefing" help="Toont later samenvatting van AI, nieuws en uploads.">
          <EmptyState title="Briefing niet beschikbaar" message="Dagelijkse briefing verschijnt zodra AI-analyse en databronnen actief zijn." />
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
