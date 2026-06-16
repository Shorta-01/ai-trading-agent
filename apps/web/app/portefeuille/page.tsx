"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { PortefeuilleRealtimeSection } from "@/components/PortefeuilleRealtimeSection";
import { ProfitHarvestCycleWidget } from "@/components/ProfitHarvestCycleWidget";
import { StatusBadge } from "@/components/StatusBadge";
import { PositionPlTraceDetails } from "@/components/PositionPlTraceDetails";
import { ValuationTraceDetails } from "@/components/ValuationTraceDetails";
import {
  apiClient,
  AssetActionDraftResponse,
  AssetDecisionPackageResponse,
  AssetForecastResponse,
  AssetSuggestionResponse,
  DailyBriefingResponse,
  DecisionPackageExplanationResponse,
  IbkrAccountModeResponse,
  IbkrCashSnapshot,
  IbkrExecutionSnapshot,
  IbkrOpenOrderSnapshot,
  IbkrPositionSnapshot,
  IbkrSyncStatusResponse,
  PortfolioValuationReadinessRow,
  PortfolioValuationReadinessResponse,
  SchedulerJobsResponse,
  SchedulerRunResponse,
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

// V1.2 §BZ vervolg: dismiss-with-reason banner voor IBKR-config
// SystemEvents. Operator klikt "Begrepen" → inline reden-veld
// verschijnt → "Bevestig" stuurt ``resolveSystemEvent`` met
// ``reason_nl``. Audit-trail krijgt zo operator-context
// (b.v. "live is intentional" vs "config-fout, account gefixt").
function IbkrConfigEventBanner({
  event,
  onDismissed,
}: {
  event: {
    system_event_id: string;
    event_code: string;
    title_nl: string;
    message_nl: string;
  };
  onDismissed: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function confirmDismiss() {
    setSubmitting(true);
    try {
      const trimmed = reason.trim();
      await apiClient.resolveSystemEvent(
        event.system_event_id,
        trimmed ? { reason_nl: trimmed } : undefined,
      );
      onDismissed();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      data-testid={`ibkr-config-event-banner-${event.event_code}`}
      data-event-code={event.event_code}
      role="alert"
      style={{
        padding: "0.7rem 0.9rem",
        borderRadius: "0.5rem",
        background:
          event.event_code === "order_session_live_account"
            ? "var(--ata-danger, #b91c1c)"
            : "var(--ata-warning, #f59e0b)",
        color: "white",
        marginBottom: "0.5rem",
        fontSize: "0.9rem",
        fontWeight: 500,
        lineHeight: 1.4,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "0.5rem",
        }}
      >
        <div style={{ flex: 1 }}>
          <strong style={{ display: "block", marginBottom: "0.2rem" }}>
            {event.event_code === "order_session_live_account" ? "🔴 " : "⚠️ "}
            {event.title_nl}
          </strong>
          {event.message_nl}
        </div>
        {!expanded ? (
          <button
            type="button"
            data-testid={`ibkr-config-event-banner-dismiss-${event.event_code}`}
            onClick={() => setExpanded(true)}
            title="Begrepen — verwijder deze melding"
            style={{
              background: "rgba(255,255,255,0.18)",
              color: "white",
              border: "1px solid rgba(255,255,255,0.4)",
              borderRadius: "0.3rem",
              padding: "0.2rem 0.55rem",
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            Begrepen
          </button>
        ) : null}
      </div>
      {expanded ? (
        <div
          data-testid={`ibkr-config-event-banner-reason-form-${event.event_code}`}
          style={{
            marginTop: "0.5rem",
            padding: "0.5rem",
            background: "rgba(255,255,255,0.12)",
            borderRadius: "0.3rem",
          }}
        >
          <label
            style={{
              display: "block",
              fontSize: "0.75rem",
              marginBottom: "0.25rem",
            }}
          >
            Optionele reden (b.v. &ldquo;live is intentional&rdquo;):
          </label>
          <input
            type="text"
            data-testid={`ibkr-config-event-banner-reason-input-${event.event_code}`}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reden voor audit-trail (optioneel)"
            style={{
              width: "100%",
              padding: "0.3rem 0.5rem",
              borderRadius: "0.25rem",
              border: "1px solid rgba(255,255,255,0.5)",
              background: "rgba(255,255,255,0.92)",
              color: "#1f2937",
              fontSize: "0.85rem",
            }}
            disabled={submitting}
          />
          <div
            style={{
              display: "flex",
              gap: "0.4rem",
              marginTop: "0.4rem",
              justifyContent: "flex-end",
            }}
          >
            <button
              type="button"
              data-testid={`ibkr-config-event-banner-reason-cancel-${event.event_code}`}
              onClick={() => {
                setExpanded(false);
                setReason("");
              }}
              disabled={submitting}
              style={{
                background: "rgba(255,255,255,0.18)",
                color: "white",
                border: "1px solid rgba(255,255,255,0.4)",
                borderRadius: "0.25rem",
                padding: "0.2rem 0.55rem",
                fontSize: "0.8rem",
                cursor: "pointer",
              }}
            >
              Annuleer
            </button>
            <button
              type="button"
              data-testid={`ibkr-config-event-banner-reason-confirm-${event.event_code}`}
              onClick={confirmDismiss}
              disabled={submitting}
              style={{
                background: "white",
                color: "#1f2937",
                border: "none",
                borderRadius: "0.25rem",
                padding: "0.2rem 0.7rem",
                fontSize: "0.8rem",
                fontWeight: 700,
                cursor: submitting ? "wait" : "pointer",
              }}
            >
              {submitting ? "Bezig…" : "Bevestig"}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function PortfolioPage() {
  const [explanations, setExplanations] = useState<Record<string, DecisionPackageExplanationResponse | null>>({});
  const [explanationStatuses, setExplanationStatuses] = useState<Record<string, string>>({});
  const [syncing, setSyncing] = useState(false);

  const dataQuery = useQuery({
    queryKey: ["portefeuille-data"],
    queryFn: async () => {
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
      return {
        syncStatus: statusRes.ok ? statusRes.data : null,
        valuationReadiness: valuationRes.ok ? valuationRes.data : null,
        positions: positionsRes.ok ? (positionsRes.data.items ?? []) : [],
        cashItems: cashRes.ok ? (cashRes.data.items ?? []) : [],
        openOrders: ordersRes.ok ? (ordersRes.data.items ?? []) : [],
        executions: executionsRes.ok ? (executionsRes.data.items ?? []) : [],
        forecasts: forecastsRes.ok ? (forecastsRes.data.items ?? []) : [],
        suggestions: suggestionsRes.ok ? (suggestionsRes.data.items ?? []) : [],
        decisionPackages: decisionPackagesRes.ok ? (decisionPackagesRes.data.items ?? []) : [],
        actionDrafts: actionDraftsRes.ok ? (actionDraftsRes.data.items ?? []) : [],
        loadFailed: !statusRes.ok && !valuationRes.ok && !positionsRes.ok && !cashRes.ok && !ordersRes.ok && !executionsRes.ok,
      };
    },
  });
  const syncStatus: IbkrSyncStatusResponse | null = dataQuery.data?.syncStatus ?? null;
  const valuationReadiness: PortfolioValuationReadinessResponse | null = dataQuery.data?.valuationReadiness ?? null;
  const positions: IbkrPositionSnapshot[] = dataQuery.data?.positions ?? [];
  const cashItems: IbkrCashSnapshot[] = dataQuery.data?.cashItems ?? [];
  const openOrders: IbkrOpenOrderSnapshot[] = dataQuery.data?.openOrders ?? [];
  const executions: IbkrExecutionSnapshot[] = dataQuery.data?.executions ?? [];
  const forecasts: AssetForecastResponse[] = useMemo(
    () => dataQuery.data?.forecasts ?? [],
    [dataQuery.data],
  );
  const suggestions: AssetSuggestionResponse[] = useMemo(
    () => dataQuery.data?.suggestions ?? [],
    [dataQuery.data],
  );
  const decisionPackages: AssetDecisionPackageResponse[] = dataQuery.data?.decisionPackages ?? [];
  const actionDrafts: AssetActionDraftResponse[] = dataQuery.data?.actionDrafts ?? [];
  const loading = dataQuery.isFetching;
  const loadFailed = dataQuery.data?.loadFailed ?? false;

  const dailyBriefingQuery = useQuery({
    queryKey: ["portefeuille-daily-briefing"],
    queryFn: async (): Promise<DailyBriefingResponse | null> => {
      const res = await apiClient.getLatestDailyBriefing();
      return res.ok ? res.data.item : null;
    },
  });
  const dailyBriefing = dailyBriefingQuery.data ?? null;

  const accountModeQuery = useQuery({
    queryKey: ["portefeuille-account-mode"],
    queryFn: async (): Promise<IbkrAccountModeResponse | null> => {
      const res = await apiClient.getIbkrAccountMode();
      return res.ok ? res.data : null;
    },
  });
  const accountMode = accountModeQuery.data ?? null;

  const queryClient = useQueryClient();

  // V1.2 §BZ vervolg: query active system events zodat
  // ``order_session_live_account`` (worker) en
  // ``account_id_mismatch`` (api sync) ook prominent op
  // /portefeuille worden getoond, niet alleen op /systeemmeldingen.
  const ibkrConfigEventsQuery = useQuery({
    queryKey: ["portefeuille-ibkr-config-events"],
    queryFn: async () => {
      const res = await apiClient.getActiveSystemEvents();
      if (!res.ok) return [];
      return res.data.events.filter(
        (e) =>
          e.status === "open"
          && (e.event_code === "order_session_live_account"
            || e.event_code === "account_id_mismatch"
            || e.category === "ibkr_config_mismatch"),
      );
    },
  });
  const ibkrConfigEvents = ibkrConfigEventsQuery.data ?? [];

  const schedulerQuery = useQuery({
    queryKey: ["portefeuille-scheduler"],
    queryFn: async () => {
      const [jobsRes, runRes, recentRes] = await Promise.all([
        apiClient.getSchedulerJobs(),
        apiClient.getLatestSchedulerRun(),
        apiClient.getRecentSchedulerRuns(10),
      ]);
      return {
        schedulerJobs: jobsRes.ok ? jobsRes.data : null,
        latestSchedulerRun: runRes.ok ? runRes.data.item : null,
        recentSchedulerRuns: recentRes.ok ? recentRes.data.items : [],
      };
    },
  });
  const schedulerJobs: SchedulerJobsResponse | null = schedulerQuery.data?.schedulerJobs ?? null;
  const latestSchedulerRun: SchedulerRunResponse | null = schedulerQuery.data?.latestSchedulerRun ?? null;
  const recentSchedulerRuns: SchedulerRunResponse[] = schedulerQuery.data?.recentSchedulerRuns ?? [];

  const loadExplanation = async (decisionPackageId: string) => {
    const res = await apiClient.getDecisionPackageExplanation(decisionPackageId);
    if (res.ok) {
      setExplanations((prev) => ({ ...prev, [decisionPackageId]: res.data.item }));
      setExplanationStatuses((prev) => ({ ...prev, [decisionPackageId]: res.data.status }));
    }
  };

  const loadDailyBriefing = () => {
    void dailyBriefingQuery.refetch();
  };

  const loadSchedulerInfo = () => {
    void schedulerQuery.refetch();
  };

  const runDailyBriefing = async () => {
    const res = await apiClient.runDailyBriefing();
    if (res.ok && res.data.briefing_id) {
      await dailyBriefingQuery.refetch();
    }
  };

  const runExplanation = async (decisionPackageId: string) => {
    setExplanationStatuses((prev) => ({ ...prev, [decisionPackageId]: "running" }));
    const res = await apiClient.runDecisionPackageExplanation(decisionPackageId);
    if (res.ok) {
      setExplanationStatuses((prev) => ({ ...prev, [decisionPackageId]: res.data.status }));
      if (res.data.explanation) {
        setExplanations((prev) => ({ ...prev, [decisionPackageId]: res.data.explanation }));
      }
    } else {
      setExplanationStatuses((prev) => ({ ...prev, [decisionPackageId]: "request_failed" }));
    }
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
    await dataQuery.refetch();
    setSyncing(false);
  };

  return (
    <main className="page-wrap">
      <PortefeuilleRealtimeSection />
      <ProfitHarvestCycleWidget />
      <section className="dashboard-panel">
        <div className="panel-head">
          <h2>Portefeuille</h2>
          <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
            {accountMode ? (
              <a
                href="/admin/audit/ibkr-config"
                data-testid="account-mode-pill-link"
                title={`${accountMode.help_nl} — klik voor het audit-trail`}
                style={{
                  padding: "0.15rem 0.5rem",
                  borderRadius: "0.4rem",
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  letterSpacing: "0.05em",
                  background: accountMode.mode === "live"
                    ? "var(--ata-warning, #f59e0b)"
                    : accountMode.mode === "paper"
                      ? "var(--ata-info, #38bdf8)"
                      : "var(--ata-muted, #64748b)",
                  color: "white",
                  textDecoration: "none",
                }}
              >
                {accountMode.display_label}
              </a>
            ) : null}
            <button className="sync-button" type="button" onClick={() => void runSync()} disabled={syncing}>
              {syncing ? "Synchroniseren..." : "Synchroniseer snapshots"}
            </button>
          </div>
        </div>
        <p className="top-sub">Read-only weergave van laatst opgeslagen IBKR snapshots voor posities, cash, open orders en uitvoeringen.</p>

        {ibkrConfigEvents.length > 0 ? (
          <div data-testid="ibkr-config-events-banner-list">
            {ibkrConfigEvents.map((event) => (
              <IbkrConfigEventBanner
                key={event.system_event_id}
                event={event}
                onDismissed={() => {
                  void queryClient.invalidateQueries({
                    queryKey: ["portefeuille-ibkr-config-events"],
                  });
                }}
              />
            ))}
          </div>
        ) : null}

        {accountMode?.hint_mismatch ? (
          <div
            data-testid="account-mode-hint-mismatch-banner"
            role="alert"
            style={{
              padding: "0.7rem 0.9rem",
              borderRadius: "0.5rem",
              background: "var(--ata-warning, #f59e0b)",
              color: "white",
              marginBottom: "0.8rem",
              fontSize: "0.9rem",
              fontWeight: 500,
              lineHeight: 1.4,
            }}
          >
            <strong style={{ display: "block", marginBottom: "0.2rem" }}>
              ⚠️ IBKR account-mismatch
            </strong>
            {accountMode.hint_mismatch_nl}
          </div>
        ) : null}

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
        <div className="panel-head">
          <h2>Dagbriefing</h2>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button type="button" onClick={() => void runDailyBriefing()} style={{ fontSize: "0.85rem", padding: "0.2rem 0.6rem" }}>
              Genereer briefing
            </button>
            <button type="button" onClick={() => void loadDailyBriefing()} style={{ fontSize: "0.85rem", padding: "0.2rem 0.6rem" }}>
              Vernieuw
            </button>
          </div>
        </div>
        <p className="top-sub">Deterministische dagsamenvatting + alerts; geen AI auteur, geen broker actie.</p>
        {dailyBriefing ? (
          <div>
            <div style={{ marginBottom: "0.5rem", fontSize: "0.92rem" }}>{dailyBriefing.summary_nl}</div>
            <div style={{ fontSize: "0.85rem", opacity: 0.75 }}>
              briefing-datum: {dailyBriefing.briefing_date}
              {" • "}
              alerts: {dailyBriefing.alert_count}
              {" • "}
              positions: {dailyBriefing.position_count}
            </div>
            {dailyBriefing.alerts.length > 0 ? (
              <ul style={{ marginTop: "0.5rem", paddingLeft: "1.1rem" }}>
                {dailyBriefing.alerts.map((alert) => (
                  <li
                    key={alert.alert_id}
                    style={{
                      fontSize: "0.88rem",
                      color: alert.severity === "critical"
                        ? "var(--ata-warning, #f97316)"
                        : alert.severity === "warning"
                          ? "var(--ata-warning, #f59e0b)"
                          : undefined,
                    }}
                  >
                    <strong>[{alert.severity}]</strong> {alert.title_nl} — {alert.body_nl}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : (
          <EmptyState
            title="Nog geen dagbriefing"
            message="Druk op 'Genereer briefing' om een deterministische samenvatting op te slaan."
          />
        )}
      </section>

      <section className="dashboard-panel">
        <div className="panel-head">
          <h2>Scheduler</h2>
          <button type="button" onClick={() => void loadSchedulerInfo()} style={{ fontSize: "0.85rem", padding: "0.2rem 0.6rem" }}>
            Vernieuw
          </button>
        </div>
        <p className="top-sub">
          APScheduler in-process voor de 07:00 Brussel-briefing. Disabled-by-default; een scheduled run promoveert nooit naar een order.
        </p>
        {schedulerJobs ? (
          <div className="portfolio-meta-grid">
            <div><strong>Status:</strong> {schedulerJobs.status === "ok" ? "Actief" : "Uitgeschakeld"}</div>
            <div><strong>Tijdzone:</strong> {schedulerJobs.scheduler_timezone}</div>
            <div><strong>Daily cron:</strong> {schedulerJobs.scheduler_daily_briefing_cron}</div>
            <div>
              <strong>Volgende fire:</strong>{" "}
              {schedulerJobs.items[0]?.next_run_at ?? "Niet beschikbaar (scheduler is uitgeschakeld of nog niet gestart)"}
            </div>
            <div>
              <strong>Laatste run:</strong>{" "}
              {latestSchedulerRun
                ? `${latestSchedulerRun.status} @ ${latestSchedulerRun.started_at}${latestSchedulerRun.error_text ? ` — fout: ${latestSchedulerRun.error_text}` : ""}`
                : "Nog geen scheduler-run."}
            </div>
          </div>
        ) : (
          <EmptyState title="Scheduler info niet beschikbaar" message="Endpoint nog niet geladen." />
        )}
        <div data-testid="scheduler-recent-runs" style={{ marginTop: "0.75rem" }}>
          <strong style={{ fontSize: "0.9rem" }}>Recente daily-briefing runs</strong>
          {recentSchedulerRuns.length === 0 ? (
            <p style={{ color: "#6b7280", fontSize: 13, marginTop: 4 }}>
              Nog geen runs.
            </p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, marginTop: 4 }}>
              <thead>
                <tr style={{ background: "#f3f4f6" }}>
                  <th style={{ textAlign: "left", padding: 6 }}>Gestart</th>
                  <th style={{ textAlign: "left", padding: 6 }}>Status</th>
                  <th style={{ textAlign: "left", padding: 6 }}>Fout</th>
                </tr>
              </thead>
              <tbody>
                {recentSchedulerRuns.map((row) => (
                  <tr key={row.run_id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                    <td style={{ padding: 6, fontFamily: "monospace" }}>{row.started_at}</td>
                    <td style={{ padding: 6 }}>{row.status}</td>
                    <td style={{ padding: 6, color: row.error_text ? "#b91c1c" : "#6b7280" }}>
                      {row.error_text ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

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
                <th>TOB (BE)</th>
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
                    <td title={draft.belgian_tob_security_class ? `Beurstaks tarief: ${draft.belgian_tob_security_class}` : "Geen TOB beschikbaar"}>{displayValue(draft.estimated_belgian_tob)}</td>
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
                  <div style={{
                    marginTop: "0.5rem",
                    padding: "0.5rem 0.75rem",
                    borderLeft: "3px solid var(--ata-accent, #38bdf8)",
                    background: "rgba(56,189,248,0.05)",
                  }}>
                    <div><strong>Onderzoek:</strong> {dp.research_evidence_count} bron(nen) {dp.research_credibility_summary ? `• ${dp.research_credibility_summary} credibility` : ""}{dp.research_freshness_status ? ` • ${dp.research_freshness_status}` : ""}</div>
                    {dp.research_blocking_reason ? (
                      <div style={{ color: "var(--ata-warning, #f97316)" }}>
                        <strong>Onderzoek block:</strong> {dp.research_blocking_reason}
                      </div>
                    ) : null}
                    <div style={{ fontSize: "0.88rem", opacity: 0.85 }}>{dp.research_snippet_nl ?? "Geen onderzoek-snippet."}</div>
                  </div>
                  <div style={{
                    marginTop: "0.5rem",
                    padding: "0.5rem 0.75rem",
                    borderLeft: "3px solid var(--ata-info, #a78bfa)",
                    background: "rgba(167,139,250,0.06)",
                  }}>
                    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
                      <strong>AI uitleg:</strong>
                      <button
                        type="button"
                        onClick={() => runExplanation(dp.decision_package_id)}
                        style={{ fontSize: "0.85rem", padding: "0.2rem 0.5rem" }}
                      >
                        Genereer / vernieuw
                      </button>
                      <button
                        type="button"
                        onClick={() => loadExplanation(dp.decision_package_id)}
                        style={{ fontSize: "0.85rem", padding: "0.2rem 0.5rem" }}
                      >
                        Lees laatste
                      </button>
                      {explanationStatuses[dp.decision_package_id] ? (
                        <span style={{ fontSize: "0.82rem", opacity: 0.7 }}>
                          status: {explanationStatuses[dp.decision_package_id]}
                        </span>
                      ) : null}
                    </div>
                    {explanations[dp.decision_package_id] ? (
                      <div style={{ marginTop: "0.4rem" }}>
                        <div style={{ fontSize: "0.82rem", opacity: 0.75 }}>
                          provider: {explanations[dp.decision_package_id]?.model_provider_code}
                          {" • "}
                          model: {explanations[dp.decision_package_id]?.model_name} ({explanations[dp.decision_package_id]?.model_version})
                          {" • "}
                          status: {explanations[dp.decision_package_id]?.status}
                        </div>
                        {explanations[dp.decision_package_id]?.blocking_reason ? (
                          <div style={{ color: "var(--ata-warning, #f97316)", fontSize: "0.85rem" }}>
                            <strong>Geblokkeerd:</strong> {explanations[dp.decision_package_id]?.blocking_reason}
                            {explanations[dp.decision_package_id] && (explanations[dp.decision_package_id]?.hallucinated_numbers.length ?? 0) > 0
                              ? ` (verzonnen getallen: ${explanations[dp.decision_package_id]?.hallucinated_numbers.join(", ")})`
                              : ""}
                          </div>
                        ) : null}
                        <p style={{ marginTop: "0.4rem", fontSize: "0.9rem", whiteSpace: "pre-wrap" }}>
                          {explanations[dp.decision_package_id]?.explanation_nl}
                        </p>
                        <div style={{ fontSize: "0.78rem", opacity: 0.6 }}>
                          input-hash: {explanations[dp.decision_package_id]?.input_evidence_hash.slice(0, 12)}…
                        </div>
                      </div>
                    ) : (
                      <div style={{ fontSize: "0.85rem", opacity: 0.7, marginTop: "0.3rem" }}>
                        Nog geen AI uitleg geladen. AI bedacht nooit een getal; lees of genereer een samenvatting.
                      </div>
                    )}
                  </div>
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
