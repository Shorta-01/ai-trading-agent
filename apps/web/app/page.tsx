"use client";

import { FormEvent, useEffect, useState } from "react";

import { ApiUnavailableNotice } from "@/components/ApiUnavailableNotice";
import { EmptyState } from "@/components/EmptyState";
import { SectionHeader } from "@/components/SectionHeader";
import { StatusCard } from "@/components/StatusCard";
import { apiClient, AiUsageSummary, IbkrStatusResponse, IntegrationsSummary, SettingsSummary, StorageStatusSummary, SystemStatusSummary, TradingSettingsResponse } from "@/lib/apiClient";
import { uiText } from "@/lib/uiText";

export default function HomePage() {
  const [systemStatus, setSystemStatus] = useState<SystemStatusSummary | null>(null);
  const [settings, setSettings] = useState<SettingsSummary | null>(null);
  const [usage, setUsage] = useState<AiUsageSummary | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationsSummary | null>(null);
  const [storage, setStorage] = useState<StorageStatusSummary | null>(null);
  const [apiNotReachable, setApiNotReachable] = useState(false);

  const [tradingSettings, setTradingSettings] = useState<TradingSettingsResponse | null>(null);
  const [ibkrStatus, setIbkrStatus] = useState<IbkrStatusResponse | null>(null);
  const [saveStatus, setSaveStatus] = useState<string>(""
  );


  useEffect(() => {
    async function loadDashboardData() {
      const [systemResponse, settingsResponse, usageResponse, integrationsResponse, storageResponse, tradingResponse, ibkrStatusResponse] = await Promise.all([
        apiClient.getSystemStatus(),
        apiClient.getSettingsSummary(),
        apiClient.getAiUsageSummary(),
        apiClient.getIntegrationsSummary(),
        apiClient.getStorageStatus(),
        apiClient.getTradingSettings(),
        apiClient.getIbkrStatus(),
      ]);

      const hasError =
        !systemResponse.ok || !settingsResponse.ok || !usageResponse.ok || !integrationsResponse.ok || !storageResponse.ok || !tradingResponse.ok || !ibkrStatusResponse.ok;

      setApiNotReachable(hasError);
      setSystemStatus(systemResponse.ok ? systemResponse.data : null);
      setSettings(settingsResponse.ok ? settingsResponse.data : null);
      setUsage(usageResponse.ok ? usageResponse.data : null);
      setIntegrations(integrationsResponse.ok ? integrationsResponse.data : null);
      setStorage(storageResponse.ok ? storageResponse.data : null);
      setTradingSettings(tradingResponse.ok ? tradingResponse.data : null);
      setIbkrStatus(ibkrStatusResponse.ok ? ibkrStatusResponse.data : null);
    }

    void loadDashboardData();
  }, []);


  async function onSaveTradingSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!tradingSettings) return;
    setSaveStatus("Bezig met opslaan...");
    const response = await apiClient.updateTradingSettings({
      allowed_universe: tradingSettings.allowed_universe,
      user_strategy: tradingSettings.user_strategy,
      reason_nl: "Instellingen aangepast door gebruiker.",
    });
    if (!response.ok) {
      setSaveStatus("Instellingen niet opgeslagen. Controleer de melding.");
      return;
    }
    setTradingSettings(response.data);
    setSaveStatus(response.data.updated ? "Instellingen opgeslagen." : "Instellingen niet opgeslagen. Controleer de melding.");
  }

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
        <SectionHeader title="Opslag" helpText="Geplande database-status in eenvoudige Nederlandse taal." />
        <div className="grid one-column">
          <StatusCard
            titel="Database nog niet actief"
            status={storage?.implementation_status_nl ?? "Nog niet geïmplementeerd"}
            statusType="waarschuwing"
            hulptekst={storage?.help_nl ?? "De database is nog niet actief. Daarom kan de app je paper portefeuille nog niet echt bewaren."}
            extraRegels={[
              `Database: ${storage?.selected_database_nl ?? "PostgreSQL gepland"}`,
              `Migraties: ${storage?.migration_tool_nl ?? "Alembic gepland"}`,
              `Opslaan: ${storage?.can_persist_paper_setup ? "Mogelijk" : "Kan nog niet opslaan"}`,
            ]}
          />
        </div>
      </section>



      <section>
        <SectionHeader title="IBKR koppeling" helpText="Hier stel je later de veilige koppeling met IBKR in." />
        <div className="grid one-column">
          <StatusCard
            titel="Status"
            status={ibkrStatus?.status_nl ?? "Status niet beschikbaar"}
            statusType={ibkrStatus?.configured ? "actief" : "waarschuwing"}
            hulptekst={ibkrStatus?.message_nl ?? "IBKR-status is nu niet beschikbaar."}
            extraRegels={[
              ibkrStatus?.help_nl ?? "In versie 1 moet het gekoppelde IBKR-account paper-only zijn.",
              "Orders blijven geblokkeerd tot het account veilig is gecontroleerd.",
              "Er worden in deze versie van de instelling nog geen echte IBKR API-calls uitgevoerd.",
              "Sla hier geen wachtwoorden, tokens of API-sleutels op.",
            ]}
          />
          <p>IBKR koppeling inschakelen: {ibkrStatus?.enabled ? "Ja" : "Nee"}</p>
          <p>Verwachte accountmodus: {ibkrStatus?.expected_environment ?? "paper"}</p>
          <p>IBKR account hint: {ibkrStatus?.account_id_hint_present ? "Ingesteld" : "Niet ingesteld"}</p>
          <p>Gateway-adres: {ibkrStatus?.gateway_url_configured ? "Ingesteld" : "Niet ingesteld"}</p>
          <p>Statuscontrole inschakelen: {ibkrStatus?.status_check_enabled ? "Ja" : "Nee"}</p>
          <p>Orderblokkade: {ibkrStatus?.blocks_orders ? "Actief" : "Niet actief"}</p>
        </div>
      </section>

      <section>
        <SectionHeader title="Instellingen - Trading" helpText="Deze instellingen bepalen wat het systeem mag onderzoeken en wat bij je strategie past." />
        <form onSubmit={onSaveTradingSettings} className="grid one-column">
          <label><input type="checkbox" checked={Boolean(tradingSettings?.allowed_universe.allow_etfs)} onChange={(e)=>setTradingSettings((prev)=>prev?({...prev,allowed_universe:{...prev.allowed_universe,allow_etfs:e.target.checked}}):prev)} /> ETF’s toestaan</label>
          <label><input type="checkbox" checked={Boolean(tradingSettings?.allowed_universe.allow_stocks)} onChange={(e)=>setTradingSettings((prev)=>prev?({...prev,allowed_universe:{...prev.allowed_universe,allow_stocks:e.target.checked}}):prev)} /> Aandelen toestaan</label>
          <label><input type="checkbox" checked={Boolean(tradingSettings?.allowed_universe.allow_currencies_watch_only)} onChange={(e)=>setTradingSettings((prev)=>prev?({...prev,allowed_universe:{...prev.allowed_universe,allow_currencies_watch_only:e.target.checked}}):prev)} /> Valuta volgen, niet kopen</label>
          <p>Altijd geblokkeerd in versie 1: {(tradingSettings?.always_blocked_asset_types ?? []).join(", ")}</p>
          <p>{tradingSettings?.message_nl ?? "Laden..."}</p>
          <p>{saveStatus}</p>
          <button type="submit">Instellingen opslaan</button>
        </form>
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
