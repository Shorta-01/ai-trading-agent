"use client";

import { useEffect, useState } from "react";

import { ApiUnavailableNotice } from "@/components/ApiUnavailableNotice";
import { EmptyState } from "@/components/EmptyState";
import { SectionHeader } from "@/components/SectionHeader";
import { StatusCard } from "@/components/StatusCard";
import { apiClient, AiUsageSummary, IntegrationsSummary, SettingsSummary, SystemStatusSummary } from "@/lib/apiClient";
import { uiText } from "@/lib/uiText";

export default function HomePage() {
  const [systemStatus, setSystemStatus] = useState<SystemStatusSummary | null>(null);
  const [settings, setSettings] = useState<SettingsSummary | null>(null);
  const [usage, setUsage] = useState<AiUsageSummary | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationsSummary | null>(null);
  const [apiNotReachable, setApiNotReachable] = useState(false);

  useEffect(() => {
    async function loadDashboardData() {
      const [systemResponse, settingsResponse, usageResponse, integrationsResponse] = await Promise.all([
        apiClient.getSystemStatus(),
        apiClient.getSettingsSummary(),
        apiClient.getAiUsageSummary(),
        apiClient.getIntegrationsSummary(),
      ]);

      const hasError =
        !systemResponse.ok || !settingsResponse.ok || !usageResponse.ok || !integrationsResponse.ok;

      setApiNotReachable(hasError);
      setSystemStatus(systemResponse.ok ? systemResponse.data : null);
      setSettings(settingsResponse.ok ? settingsResponse.data : null);
      setUsage(usageResponse.ok ? usageResponse.data : null);
      setIntegrations(integrationsResponse.ok ? integrationsResponse.data : null);
    }

    void loadDashboardData();
  }, []);

  return (
    <main className="container">
      <header className="hero">
        <div>
          <h1>{uiText.projectNaam}</h1>
          <p className="hero-subtitle">{uiText.projectSubtitel}</p>
        </div>
        <span className="paper-badge">{uiText.paperOnlyTitel}</span>
      </header>
      <p className="hero-message">{uiText.veiligeMelding}</p>
      <p className="help-text">Help: {uiText.paperOnlyHelp}</p>

      {apiNotReachable ? <ApiUnavailableNotice /> : null}

      <section>
        <SectionHeader title="Systeemstatus" helpText="Overzicht van veilige startstatus voor kernonderdelen." />
        <div className="grid">
          {systemStatus?.services.map((service) => (
            <StatusCard
              key={service.key}
              titel={service.label_nl}
              status={service.status_nl}
              statusType={service.status_key === "active" ? "actief" : service.status_key === "error" ? "fout" : "waarschuwing"}
              hulptekst={service.help_nl}
            />
          ))}
        </div>
      </section>

      <section>
        <SectionHeader title="Instellingen" helpText="Read-only overzicht zonder bewerkvelden of geheime invoer." />
        <div className="grid">
          <StatusCard
            titel="IBKR"
            status={settings?.ibkr.status_nl ?? "Niet ingesteld"}
            statusType="waarschuwing"
            hulptekst={settings?.ibkr.help_nl ?? "IBKR paper moet nog veilig worden ingesteld."}
            extraRegels={["Paper account verplicht", "Live orders niet toegestaan"]}
          />
          <StatusCard
            titel="OpenAI"
            status={settings?.openai.status_nl ?? "Niet ingesteld"}
            statusType="waarschuwing"
            hulptekst={settings?.openai.help_nl ?? "OpenAI is nog niet ingesteld voor onderzoek."}
            extraRegels={["API-sleutel niet ingesteld", "AI-verbruik nog niet beschikbaar"]}
          />
          <StatusCard
            titel="Veiligheid van geheime sleutels"
            status="Actief"
            statusType="actief"
            hulptekst={settings?.secret_safety.help_nl ?? "API-sleutels worden niet als gewone tekst getoond."}
            extraRegels={["API-sleutels worden niet als gewone tekst getoond"]}
          />
        </div>
      </section>

      <section>
        <SectionHeader title="AI-verbruik" helpText="Werkelijk verbruik verschijnt pas na een geldige OpenAI-koppeling." />
        <div className="grid one-column">
          <StatusCard
            titel="AI-verbruik"
            status={usage?.usage_available ? "Beschikbaar" : "Nog niet beschikbaar"}
            statusType={usage?.usage_available ? "actief" : "waarschuwing"}
            hulptekst={usage?.help_nl ?? "AI-verbruik is nog niet beschikbaar."}
            extraRegels={[
              `Geschatte kost (USD): ${usage?.estimated_cost_usd ?? "Niet beschikbaar"}`,
              `Geschatte kost (EUR): ${usage?.estimated_cost_eur ?? "Niet beschikbaar"}`,
              `Budgetstatus: ${usage?.budget_status_nl ?? "Niet ingesteld"}`,
            ]}
          />
        </div>
      </section>

      <section>
        <SectionHeader title="Koppelingen" helpText="Status van koppelingen zonder live broker- of AI-calls." />
        <div className="grid">
          {integrations?.cards.map((card) => (
            <StatusCard
              key={card.key}
              titel={card.label_nl}
              status={card.status_nl}
              statusType={card.connected ? "actief" : "waarschuwing"}
              hulptekst={card.help_nl}
              extraRegels={[
                card.configured ? "Ingesteld" : "Niet ingesteld",
                card.connected ? "Verbonden" : "Niet verbonden",
                card.blocks_related_jobs ? "Blokkeert gerelateerde taken" : "Blokkeert geen gerelateerde taken",
              ]}
            />
          ))}
        </div>
      </section>

      <section>
        <SectionHeader title="Actiesuggesties" helpText="Suggesties verschijnen pas na geldige instellingen, datakwaliteit en controles." />
        <EmptyState
          titel="Nog geen actiesuggesties"
          melding="Het systeem maakt pas suggesties als instellingen, datakwaliteit en controles klaar zijn."
          hulptekst="Er worden nu geen koop- of verkoopsuggesties getoond."
        />
      </section>

      <section>
        <SectionHeader title="Portefeuille" helpText="Pas later verschijnt hier echte paper-portefeuilledata." />
        <EmptyState
          titel="Nog geen portefeuilledata"
          melding="Later zie je hier je paper portefeuille, cash, winst/verlies en posities."
          hulptekst="Er worden geen voorbeeldbedragen of nep-posities getoond."
        />
      </section>
    </main>
  );
}
