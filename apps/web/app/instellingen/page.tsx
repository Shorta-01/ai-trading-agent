"use client";

/**
 * Task 138: full Instellingen (Settings) page.
 *
 * Three editable sections, each loaded with its current-or-default values and
 * saved independently:
 *   1. Risico-limieten  — the 9 behavioural-guardrail thresholds
 *      (GET/PUT /settings/risk-limits).
 *   2. Strategie        — the UserStrategySettings preference layer.
 *   3. Beleggingsuniversum — the AllowedUniverseSettings hard filter.
 * Sections 2 & 3 reuse the existing /settings/trading endpoint; when saving we
 * spread the full existing object and override only the edited fields so no
 * unrendered field is dropped (the backend re-validates the whole object).
 *
 * The IBKR connection + Claude AI settings are now editable too
 *   4. Verbinding & AI — the IBKR connection and Claude AI explanation
 *      settings (GET/PUT /settings/connection), persisted in runtime_config and
 *      overlaid onto the API settings at startup. The Claude API key is
 *      write-only: the response only reports whether a key is set, and a blank
 *      key input is omitted from the payload so the stored key is preserved.
 *
 * NOTE: a Next.js page module may export ONLY the default component, so any
 * shared option metadata lives in ``@/lib/instellingenOptions``.
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { HelpTooltip } from "@/components/HelpTooltip";
import { ProfitTargetSetting } from "@/components/ProfitTargetSetting";
import { WatchlistPreferencesSettings } from "@/components/WatchlistPreferencesSettings";
import {
  apiClient,
  type ConnectionSettingsResponse,
  type RiskLimitsResponse,
  type RiskLimitsUpdateInput,
  type TradingSettingsResponse,
} from "@/lib/apiClient";
import {
  ALLOWED_EXCHANGE_TOGGLES,
  ALLOWED_UNIVERSE_TOGGLES,
  ASSET_MIX_OPTIONS,
  CURRENCY_PREFERENCE_OPTIONS,
  PORTFOLIO_GOAL_OPTIONS,
  REGION_OPTIONS,
  RISK_LEVEL_OPTIONS,
  RISK_LIMIT_FIELDS,
  SECTOR_OPTIONS,
  type SelectOption,
} from "@/lib/instellingenOptions";

const SECTION_STYLE: React.CSSProperties = {
  marginTop: 16,
  padding: 16,
  border: "1px solid #d1d5db",
  borderRadius: 8,
};

const LABEL_STYLE: React.CSSProperties = {
  display: "grid",
  gap: 4,
  maxWidth: 420,
  marginTop: 12,
};

const LABEL_TEXT_STYLE: React.CSSProperties = { fontWeight: 600, fontSize: 13 };

const HELP_STYLE: React.CSSProperties = { color: "#6b7280", fontSize: 12 };

const BUTTON_STYLE: React.CSSProperties = {
  padding: "8px 16px",
  background: "#1d4ed8",
  color: "#ffffff",
  border: "none",
  borderRadius: 6,
  fontWeight: 600,
};

function SaveBar({
  testId,
  saving,
  savedMessage,
  error,
  onSave,
}: {
  testId: string;
  saving: boolean;
  savedMessage: string | null;
  error: string | null;
  onSave: () => void;
}) {
  return (
    <>
      <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
        <button
          type="button"
          data-testid={`${testId}-save-button`}
          onClick={onSave}
          disabled={saving}
          style={{ ...BUTTON_STYLE, cursor: saving ? "wait" : "pointer" }}
        >
          {saving ? "Bezig…" : "Opslaan"}
        </button>
        {savedMessage ? (
          <span
            data-testid={`${testId}-saved-message`}
            style={{ alignSelf: "center", color: "#15803d", fontSize: 13 }}
          >
            {savedMessage}
          </span>
        ) : null}
      </div>
      {error ? (
        <div
          data-testid={`${testId}-error`}
          style={{
            marginTop: 12,
            background: "#fee2e2",
            color: "#7f1d1d",
            padding: 8,
            borderRadius: 4,
            fontSize: 13,
          }}
        >
          {error}
        </div>
      ) : null}
    </>
  );
}

function FieldLabel({
  label_nl,
  help_nl,
}: {
  label_nl: string;
  help_nl: string;
}) {
  return (
    <span style={LABEL_TEXT_STYLE}>
      {label_nl} <HelpTooltip text={help_nl} />
    </span>
  );
}

// V1.2 §BZ vervolg: real-time PAPER/LIVE mode-preview onder het IBKR
// account-id veld. Helpt de operator voor save al zien of hij paper
// of live aan het configureren is.
function AccountIdModePreview({ accountId }: { accountId: string }) {
  const trimmed = accountId.trim().toUpperCase();
  const mode: "paper" | "live" | "unknown" = trimmed.startsWith("DU")
    || trimmed.startsWith("DF")
    ? "paper"
    : trimmed.startsWith("U")
      ? "live"
      : "unknown";

  if (mode === "unknown") {
    return (
      <span
        data-testid="instellingen-account-id-mode-preview"
        data-mode="unknown"
        style={{
          marginTop: 4,
          fontSize: 12,
          color: "#6b7280",
        }}
      >
        Onbekend account-prefix — controleer of dit klopt (DU*/DF* = paper, U* = live).
      </span>
    );
  }

  if (mode === "live") {
    return (
      <span
        data-testid="instellingen-account-id-mode-preview"
        data-mode="live"
        role="alert"
        style={{
          marginTop: 4,
          padding: "4px 8px",
          borderRadius: 4,
          background: "#fef2f2",
          color: "#7f1d1d",
          border: "1px solid #b91c1c",
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        ⚠️ LIVE account — orders gaan met ECHT geld naar de markt.
      </span>
    );
  }

  return (
    <span
      data-testid="instellingen-account-id-mode-preview"
      data-mode="paper"
      style={{
        marginTop: 4,
        padding: "4px 8px",
        borderRadius: 4,
        background: "#eff6ff",
        color: "#1e3a8a",
        border: "1px solid #93c5fd",
        fontSize: 12,
        fontWeight: 600,
      }}
    >
      PAPER account — orders gaan naar IBKR paper (geen echt geld).
    </span>
  );
}

function Dropdown({
  id,
  testId,
  value,
  options,
  onChange,
}: {
  id: string;
  testId: string;
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
}) {
  return (
    <select
      id={id}
      data-testid={testId}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label_nl}
        </option>
      ))}
    </select>
  );
}

function CheckboxGroup({
  testIdPrefix,
  options,
  selected,
  onToggle,
}: {
  testIdPrefix: string;
  options: SelectOption[];
  selected: string[];
  onToggle: (value: string, checked: boolean) => void;
}) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
      {options.map((opt) => (
        <label
          key={opt.value}
          style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}
        >
          <input
            type="checkbox"
            data-testid={`${testIdPrefix}-${opt.value}`}
            checked={selected.includes(opt.value)}
            onChange={(event) => onToggle(opt.value, event.target.checked)}
          />
          {opt.label_nl}
        </label>
      ))}
    </div>
  );
}

type StrategyState = {
  portfolio_goal: string;
  risk_level: string;
  asset_mix_preference: string;
  currency_preference: string;
  preferred_regions: string[];
  preferred_sectors: string[];
  avoided_sectors: string[];
  max_position_pct: string;
  min_cash_reserve_pct: string;
  user_buffer_eur: string;
  prefer_simple_belgian_tax_admin: boolean;
  // V1.2 profit-harvest cycle parameters — surfaced so the user can
  // tune the doctrine without code changes.
  trading_target_net_pct: string;
  trading_horizon_min_months: string;
  trading_horizon_max_months: string;
  trading_min_position_eur: string;
  trading_max_position_eur: string;
  trading_confidence_threshold_pct: string;
  trading_max_sector_pct: string;
  trading_min_market_cap_eur: string;
  trading_max_annual_volatility_pct: string;
  trading_total_budget_eur: string;
  // V1.2 §Q/R/S additions surfaced alongside the original 10 cycle
  // parameters so the user can tune the full doctrine in one place.
  trading_fat_tail_factor: string;
  trading_earnings_block_days: string;
  trading_news_buy_bias_max_boost_pct: string;
};

function strategyStateFromRecord(record: Record<string, unknown>): StrategyState {
  const str = (key: string, fallback: string): string => {
    const value = record[key];
    return value === undefined || value === null ? fallback : String(value);
  };
  const list = (key: string): string[] => {
    const value = record[key];
    return Array.isArray(value) ? value.map((v) => String(v)) : [];
  };
  return {
    portfolio_goal: str("portfolio_goal", "balanced_growth_risk"),
    risk_level: str("risk_level", "medium"),
    asset_mix_preference: str("asset_mix_preference", "etf_and_stock_mix"),
    currency_preference: str(
      "currency_preference",
      "eur_preferred_usd_allowed",
    ),
    preferred_regions: list("preferred_regions"),
    preferred_sectors: list("preferred_sectors"),
    avoided_sectors: list("avoided_sectors"),
    max_position_pct: str("max_position_pct", "10"),
    min_cash_reserve_pct: str("min_cash_reserve_pct", "5"),
    user_buffer_eur: str("user_buffer_eur", "0"),
    prefer_simple_belgian_tax_admin:
      record.prefer_simple_belgian_tax_admin !== false,
    // Profit-harvest defaults — match domain settings.py defaults so
    // the form always renders sensible numbers on a fresh install.
    trading_target_net_pct: str("trading_target_net_pct", "4"),
    trading_horizon_min_months: str("trading_horizon_min_months", "3"),
    trading_horizon_max_months: str("trading_horizon_max_months", "6"),
    trading_min_position_eur: str("trading_min_position_eur", "25000"),
    trading_max_position_eur: str("trading_max_position_eur", "100000"),
    trading_confidence_threshold_pct: str(
      "trading_confidence_threshold_pct",
      "70",
    ),
    trading_max_sector_pct: str("trading_max_sector_pct", "25"),
    trading_min_market_cap_eur: str(
      "trading_min_market_cap_eur",
      "5000000000",
    ),
    trading_max_annual_volatility_pct: str(
      "trading_max_annual_volatility_pct",
      "30",
    ),
    trading_total_budget_eur: str("trading_total_budget_eur", "1000000"),
    trading_fat_tail_factor: str("trading_fat_tail_factor", "1.15"),
    trading_earnings_block_days: str("trading_earnings_block_days", "5"),
    trading_news_buy_bias_max_boost_pct: str(
      "trading_news_buy_bias_max_boost_pct",
      "5",
    ),
  };
}

const EMPTY_RISK_LIMITS: RiskLimitsUpdateInput = {
  daily_max_approvals: 5,
  cooldown_seconds: 60,
  anti_revenge_window_hours: 72,
  anti_revenge_loss_threshold_pct: "1.0",
  soft_drawdown_pct: "5.0",
  soft_drawdown_window_days: 5,
  hard_drawdown_pct: "10.0",
  hard_drawdown_window_days: 20,
  fomo_drift_pct: "1.5",
};

// Section 4 — connection + AI. Number/text inputs are held as strings so the
// form round-trips cleanly; they are coerced on save. The API key is never
// loaded into the form (write-only); ``keySet`` tracks whether one is stored.
type ConnectionState = {
  ibkr_enabled: boolean;
  ibkr_account_id: string;
  ibkr_host: string;
  ibkr_port: string;
  ibkr_client_id: string;
  ai_explanation_enabled: boolean;
  claude_ai_explanation_model: string;
  claude_ai_budget_monthly_eur: string;
  // Settings UI PR L — AI feature toggles.
  ai_explanation_morning_batch_enabled: boolean;
  ai_email_summary_enabled: boolean;
  research_ai_extraction_enabled: boolean;
};

const EMPTY_CONNECTION: ConnectionState = {
  ibkr_enabled: false,
  ibkr_account_id: "",
  ibkr_host: "",
  ibkr_port: "",
  ibkr_client_id: "",
  ai_explanation_enabled: false,
  claude_ai_explanation_model: "",
  claude_ai_budget_monthly_eur: "",
  ai_explanation_morning_batch_enabled: false,
  ai_email_summary_enabled: false,
  research_ai_extraction_enabled: false,
};

function connectionStateFromResponse(
  data: ConnectionSettingsResponse,
): ConnectionState {
  return {
    ibkr_enabled: data.ibkr_enabled,
    ibkr_account_id: data.ibkr_account_id ?? "",
    ibkr_host: data.ibkr_host ?? "",
    ibkr_port: data.ibkr_port === null ? "" : String(data.ibkr_port),
    ibkr_client_id:
      data.ibkr_client_id === null ? "" : String(data.ibkr_client_id),
    ai_explanation_enabled: data.ai_explanation_enabled,
    claude_ai_explanation_model: data.claude_ai_explanation_model ?? "",
    claude_ai_budget_monthly_eur: data.claude_ai_budget_monthly_eur ?? "",
    ai_explanation_morning_batch_enabled:
      data.ai_explanation_morning_batch_enabled,
    ai_email_summary_enabled: data.ai_email_summary_enabled,
    research_ai_extraction_enabled: data.research_ai_extraction_enabled,
  };
}

const RISK_LIMITS_KEY = ["instellingen", "risk-limits"] as const;
const TRADING_SETTINGS_KEY = ["instellingen", "trading-settings"] as const;
const CONNECTION_SETTINGS_KEY = ["instellingen", "connection-settings"] as const;

// Server reads that seed editable form fields use these options: never
// auto-refetch (window focus, reconnect, polling) — a refetch silently
// resets the user's in-progress edits. Refreshes are explicit, fired
// after each successful save so the form re-syncs with the server's
// normalized response.
const FORM_QUERY_OPTIONS = {
  staleTime: Infinity,
  refetchOnWindowFocus: false,
  refetchOnReconnect: false,
  refetchOnMount: false,
} as const;

export default function Page() {
  const queryClient = useQueryClient();
  // ``loading`` and ``loadError`` are derived from the three queries below
  // (see further down), so they don't need their own useState slots.

  // Section 1 — risk limits.
  const [riskLimits, setRiskLimits] =
    useState<RiskLimitsUpdateInput>(EMPTY_RISK_LIMITS);
  const [riskAccountId, setRiskAccountId] = useState<string>("");
  const [riskSaving, setRiskSaving] = useState(false);
  const [riskSaved, setRiskSaved] = useState<string | null>(null);
  const [riskError, setRiskError] = useState<string | null>(null);

  // Sections 2 & 3 — trading settings.
  const [trading, setTrading] = useState<TradingSettingsResponse | null>(null);
  const [strategy, setStrategy] = useState<StrategyState | null>(null);
  const [universe, setUniverse] = useState<Record<string, boolean>>({});
  const [blockedAssetTypes, setBlockedAssetTypes] = useState<string[]>([]);
  const [strategySaving, setStrategySaving] = useState(false);
  const [strategySaved, setStrategySaved] = useState<string | null>(null);
  const [strategyError, setStrategyError] = useState<string | null>(null);
  const [universeSaving, setUniverseSaving] = useState(false);
  const [universeSaved, setUniverseSaved] = useState<string | null>(null);
  const [universeError, setUniverseError] = useState<string | null>(null);

  // Section 4 — connection + AI.
  const [connection, setConnection] =
    useState<ConnectionState>(EMPTY_CONNECTION);
  const [connectionKeySet, setConnectionKeySet] = useState(false);
  const [connectionKeyInput, setConnectionKeyInput] = useState<string>("");
  const [connectionSaving, setConnectionSaving] = useState(false);
  const [connectionSaved, setConnectionSaved] = useState<string | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Section 5 — universe scan markets (multi-select).
  const [universeScanSelected, setUniverseScanSelected] = useState<string[]>([]);
  // Settings UI PR A — order policy + suggestion filters.
  const [orderPolicy, setOrderPolicy] = useState({
    default_buy_value_eur: "",
    default_top_up_pct: "",
    default_reduce_pct: "",
    max_sector_pct: "",
    cost_dominates_ratio: "",
    suggestion_valid_minutes: 1440,
  });
  const [orderPolicyHelp, setOrderPolicyHelp] = useState<string>("");
  const [orderPolicySaving, setOrderPolicySaving] = useState(false);
  const [orderPolicySaved, setOrderPolicySaved] = useState<string | null>(null);
  const [orderPolicyError, setOrderPolicyError] = useState<string | null>(null);
  // Settings UI PR B — scheduler cadence.
  const [schedulerForm, setSchedulerForm] = useState({
    scheduler_daily_briefing_cron: "",
    ibkr_sync_interval_minutes: 15,
  });
  const [schedulerHelp, setSchedulerHelp] = useState<string>("");
  const [schedulerSaving, setSchedulerSaving] = useState(false);
  const [schedulerSaved, setSchedulerSaved] = useState<string | null>(null);
  const [schedulerError, setSchedulerError] = useState<string | null>(null);
  // Settings UI PR C — data-window knobs.
  const [dataWindowForm, setDataWindowForm] = useState({
    forecast_history_lookback_days: 400,
    forecast_minimum_bars_required: 60,
    daily_briefing_lookback_hours: 24,
    universe_scan_cache_ttl_hours: 24,
  });
  const [dataWindowHelp, setDataWindowHelp] = useState<string>("");
  const [dataWindowSaving, setDataWindowSaving] = useState(false);
  const [dataWindowSaved, setDataWindowSaved] = useState<string | null>(null);
  const [dataWindowError, setDataWindowError] = useState<string | null>(null);
  // Settings UI PR D — worker-side sweeps + EODHD.
  const [workerSweepForm, setWorkerSweepForm] = useState({
    sweep_interval_seconds: 60,
    sweep_retry_max_attempts: 3,
    sweep_retry_backoff_seconds: "2.0",
    sweep_alert_after_consecutive_errors: 3,
    eodhd_rate_limit_per_second: 10,
  });
  const [workerSweepHelp, setWorkerSweepHelp] = useState<string>("");
  const [workerSweepSaving, setWorkerSweepSaving] = useState(false);
  const [workerSweepSaved, setWorkerSweepSaved] = useState<string | null>(null);
  const [workerSweepError, setWorkerSweepError] = useState<string | null>(null);
  // Settings UI PR E — Tier-2 advanced (power-user) knobs.
  const [advancedForm, setAdvancedForm] = useState({
    ensemble_weight_strategy: "equal_weight",
    gbm_drift_window_days: null as number | null,
    action_draft_approval_valid_minutes: 5,
    ai_explanation_provider_code: "stub",
    sharpe_strong_threshold: "1.0",
    sharpe_slight_threshold: "0.3",
  });
  const [advancedHelp, setAdvancedHelp] = useState<string>("");
  const [advancedSaving, setAdvancedSaving] = useState(false);
  const [advancedSaved, setAdvancedSaved] = useState<string | null>(null);
  const [advancedError, setAdvancedError] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  // Settings UI PR G — forecast horizon, ensemble toggle, risk profile,
  // universe set, market-data feed toggles.
  const [forecastMarketForm, setForecastMarketForm] = useState({
    forecast_horizon_trading_days: 21,
    forecast_ensemble_enabled: false,
    suggestions_risk_profile: "Gebalanceerd",
    universe_set: "SP500",
    market_data_provider: "none",
    market_data_sync_enabled: false,
    ibkr_market_data_enabled: false,
    ibkr_market_data_type: "delayed",
  });
  const [forecastMarketHelp, setForecastMarketHelp] = useState<string>("");
  const [forecastMarketSaving, setForecastMarketSaving] = useState(false);
  const [forecastMarketSaved, setForecastMarketSaved] = useState<string | null>(
    null,
  );
  const [forecastMarketError, setForecastMarketError] = useState<string | null>(
    null,
  );
  // Settings UI PR H — execution gates (safety-critical).
  const [executionGateForm, setExecutionGateForm] = useState({
    ibkr_paper_order_submission_enabled: false,
    submission_sweep_enabled: false,
    cancel_sweep_enabled: false,
    morning_chain_after_pre_briefing: false,
  });
  const [executionGateHelp, setExecutionGateHelp] = useState<string>("");
  const [executionGateSaving, setExecutionGateSaving] = useState(false);
  const [executionGateSaved, setExecutionGateSaved] = useState<string | null>(
    null,
  );
  const [executionGateError, setExecutionGateError] = useState<string | null>(
    null,
  );
  // Settings UI PR I — predictor tuning (power-user).
  const [predictorTuningForm, setPredictorTuningForm] = useState({
    forecast_valid_minutes: 1440,
    decision_packages_valid_minutes: 1440,
    prediction_diary_inconclusive_tolerance_pct: "0.25",
    gbm_regime_shift_enabled: false,
    gbm_regime_shift_threshold_pct: "5.0",
  });
  const [predictorTuningHelp, setPredictorTuningHelp] = useState<string>("");
  const [predictorTuningSaving, setPredictorTuningSaving] = useState(false);
  const [predictorTuningSaved, setPredictorTuningSaved] = useState<string | null>(
    null,
  );
  const [predictorTuningError, setPredictorTuningError] = useState<string | null>(
    null,
  );
  const [predictorTuningOpen, setPredictorTuningOpen] = useState(false);
  // Settings UI PR J — market-aware scheduler (Markt-events).
  const [marketEventsForm, setMarketEventsForm] = useState({
    per_market_close_digest_enabled: true,
    per_market_open_alerts_enabled: false,
  });
  const [marketEventsHelp, setMarketEventsHelp] = useState<string>("");
  const [marketEventsFires, setMarketEventsFires] = useState<
    Array<{
      market_code: string;
      market_label_nl: string;
      timezone: string;
      event_kind: "open" | "close";
      fire_hour: number;
      fire_minute: number;
    }>
  >([]);
  const [marketEventsActiveSessions, setMarketEventsActiveSessions] = useState<
    string[]
  >([]);
  const [marketEventsSaving, setMarketEventsSaving] = useState(false);
  const [marketEventsSaved, setMarketEventsSaved] = useState<string | null>(
    null,
  );
  const [marketEventsError, setMarketEventsError] = useState<string | null>(
    null,
  );
  // Settings UI PR K — email notifications.
  const [notificationsForm, setNotificationsForm] = useState({
    smtp_host: "" as string | null,
    smtp_port: 587,
    smtp_username: "" as string | null,
    smtp_password: "" as string | null,
    smtp_from: "" as string | null,
    smtp_to: "" as string | null,
    smtp_use_tls: true,
    notifications_email_enabled: false,
    notification_send_on_nav_drop: true,
    notification_send_on_position_drop: true,
    notification_send_on_high_confidence_sell: true,
  });
  const [notificationsPasswordSet, setNotificationsPasswordSet] =
    useState(false);
  const [notificationsRealClientEnabled, setNotificationsRealClientEnabled] =
    useState(false);
  const [notificationsHelp, setNotificationsHelp] = useState<string>("");
  const [notificationsSaving, setNotificationsSaving] = useState(false);
  const [notificationsSaved, setNotificationsSaved] = useState<string | null>(
    null,
  );
  const [notificationsError, setNotificationsError] = useState<string | null>(
    null,
  );
  const [notificationsTestSending, setNotificationsTestSending] = useState(false);
  const [notificationsTestResult, setNotificationsTestResult] = useState<{
    status: string;
    detail_nl: string;
    sent: boolean;
  } | null>(null);
  const [universeScanAvailable, setUniverseScanAvailable] = useState<
    Array<{ code: string; label_nl: string }>
  >([]);
  const [universeScanHelp, setUniverseScanHelp] = useState<string>("");
  const [universeScanSaving, setUniverseScanSaving] = useState(false);
  const [universeScanSaved, setUniverseScanSaved] = useState<string | null>(null);
  const [universeScanError, setUniverseScanError] = useState<string | null>(null);

  const riskQuery = useQuery({
    queryKey: RISK_LIMITS_KEY,
    queryFn: async () => {
      const result = await apiClient.getRiskLimits();
      if (!result.ok) throw new Error("risk-limits-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    if (riskQuery.data) applyRiskLimits(riskQuery.data);
  }, [riskQuery.data]);

  function applyRiskLimits(data: RiskLimitsResponse) {
    setRiskAccountId(data.ibkr_account_id);
    setRiskLimits({
      daily_max_approvals: data.daily_max_approvals,
      cooldown_seconds: data.cooldown_seconds,
      anti_revenge_window_hours: data.anti_revenge_window_hours,
      anti_revenge_loss_threshold_pct: data.anti_revenge_loss_threshold_pct,
      soft_drawdown_pct: data.soft_drawdown_pct,
      soft_drawdown_window_days: data.soft_drawdown_window_days,
      hard_drawdown_pct: data.hard_drawdown_pct,
      hard_drawdown_window_days: data.hard_drawdown_window_days,
      fomo_drift_pct: data.fomo_drift_pct,
    });
  }

  const tradingQuery = useQuery({
    queryKey: TRADING_SETTINGS_KEY,
    queryFn: async () => {
      const result = await apiClient.getTradingSettings();
      if (!result.ok) throw new Error("trading-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    if (tradingQuery.data) applyTrading(tradingQuery.data);
  }, [tradingQuery.data]);

  function applyTrading(data: TradingSettingsResponse) {
    setTrading(data);
    setStrategy(strategyStateFromRecord(data.user_strategy ?? {}));
    setUniverse({ ...(data.allowed_universe ?? {}) });
    const blocked = (data.user_strategy as Record<string, unknown>)
      ?.blocked_asset_types;
    const universeBlocked = (data.allowed_universe as Record<string, unknown>)
      ?.blocked_asset_types;
    const fromAlways = Array.isArray(data.always_blocked_asset_types)
      ? data.always_blocked_asset_types
      : [];
    const fromUniverse = Array.isArray(universeBlocked)
      ? universeBlocked.map((v) => String(v))
      : [];
    const fromStrategy = Array.isArray(blocked)
      ? blocked.map((v) => String(v))
      : [];
    setBlockedAssetTypes(
      fromAlways.length > 0
        ? fromAlways
        : fromUniverse.length > 0
          ? fromUniverse
          : fromStrategy,
    );
  }

  const universeScanQuery = useQuery({
    queryKey: ["instellingen", "universe-scan"] as const,
    queryFn: async () => {
      const result = await apiClient.getUniverseScanSettings();
      if (!result.ok) throw new Error("universe-scan-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    const data = universeScanQuery.data;
    if (!data) return;
    setUniverseScanSelected(data.selected_codes);
    setUniverseScanAvailable(data.available_codes);
    setUniverseScanHelp(data.help_nl);
  }, [universeScanQuery.data]);

  function toggleUniverseScanCode(code: string, checked: boolean) {
    setUniverseScanSelected((prev) =>
      checked ? (prev.includes(code) ? prev : [...prev, code]) : prev.filter((c) => c !== code),
    );
  }

  // Settings UI PR A — order-policy query + save.
  const orderPolicyQuery = useQuery({
    queryKey: ["instellingen", "order-policy"] as const,
    queryFn: async () => {
      const result = await apiClient.getOrderPolicySettings();
      if (!result.ok) throw new Error("order-policy-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    const data = orderPolicyQuery.data;
    if (!data) return;
    setOrderPolicy({
      default_buy_value_eur: data.default_buy_value_eur,
      default_top_up_pct: data.default_top_up_pct,
      default_reduce_pct: data.default_reduce_pct,
      max_sector_pct: data.max_sector_pct,
      cost_dominates_ratio: data.cost_dominates_ratio,
      suggestion_valid_minutes: data.suggestion_valid_minutes,
    });
    setOrderPolicyHelp(data.help_nl);
  }, [orderPolicyQuery.data]);

  function setOrderPolicyField<K extends keyof typeof orderPolicy>(
    key: K,
    value: (typeof orderPolicy)[K],
  ) {
    setOrderPolicy((prev) => ({ ...prev, [key]: value }));
  }

  // Settings UI PR B — scheduler query + save.
  const schedulerQuery = useQuery({
    queryKey: ["instellingen", "scheduler"] as const,
    queryFn: async () => {
      const result = await apiClient.getSchedulerSettings();
      if (!result.ok) throw new Error("scheduler-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    const data = schedulerQuery.data;
    if (!data) return;
    setSchedulerForm({
      scheduler_daily_briefing_cron: data.scheduler_daily_briefing_cron,
      ibkr_sync_interval_minutes: data.ibkr_sync_interval_minutes,
    });
    setSchedulerHelp(data.help_nl);
  }, [schedulerQuery.data]);

  // Settings UI PR C — data-window query + save.
  const dataWindowQuery = useQuery({
    queryKey: ["instellingen", "data-windows"] as const,
    queryFn: async () => {
      const result = await apiClient.getDataWindowSettings();
      if (!result.ok) throw new Error("data-window-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    const data = dataWindowQuery.data;
    if (!data) return;
    setDataWindowForm({
      forecast_history_lookback_days: data.forecast_history_lookback_days,
      forecast_minimum_bars_required: data.forecast_minimum_bars_required,
      daily_briefing_lookback_hours: data.daily_briefing_lookback_hours,
      universe_scan_cache_ttl_hours: data.universe_scan_cache_ttl_hours,
    });
    setDataWindowHelp(data.help_nl);
  }, [dataWindowQuery.data]);

  // Settings UI PR D — worker sweeps query + save.
  const workerSweepQuery = useQuery({
    queryKey: ["instellingen", "worker-sweeps"] as const,
    queryFn: async () => {
      const result = await apiClient.getWorkerSweepSettings();
      if (!result.ok) throw new Error("worker-sweep-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    const data = workerSweepQuery.data;
    if (!data) return;
    setWorkerSweepForm({
      sweep_interval_seconds: data.sweep_interval_seconds,
      sweep_retry_max_attempts: data.sweep_retry_max_attempts,
      sweep_retry_backoff_seconds: data.sweep_retry_backoff_seconds,
      sweep_alert_after_consecutive_errors:
        data.sweep_alert_after_consecutive_errors,
      eodhd_rate_limit_per_second: data.eodhd_rate_limit_per_second,
    });
    setWorkerSweepHelp(data.help_nl);
  }, [workerSweepQuery.data]);

  async function handleSaveWorkerSweeps() {
    setWorkerSweepSaving(true);
    setWorkerSweepError(null);
    setWorkerSweepSaved(null);
    const result = await apiClient.updateWorkerSweepSettings(workerSweepForm);
    setWorkerSweepSaving(false);
    if (!result.ok) {
      setWorkerSweepError(
        "Opslaan mislukt. Controleer dat alle waarden ≥ 1 zijn (backoff mag 0).",
      );
      return;
    }
    queryClient.setQueryData(["instellingen", "worker-sweeps"], result.data);
    setWorkerSweepSaved("Worker-sweep instellingen opgeslagen.");
  }

  // Settings UI PR E — Tier-2 advanced query + save.
  const advancedQuery = useQuery({
    queryKey: ["instellingen", "advanced"] as const,
    queryFn: async () => {
      const result = await apiClient.getAdvancedSettings();
      if (!result.ok) throw new Error("advanced-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    const data = advancedQuery.data;
    if (!data) return;
    setAdvancedForm({
      ensemble_weight_strategy: data.ensemble_weight_strategy,
      gbm_drift_window_days: data.gbm_drift_window_days,
      action_draft_approval_valid_minutes:
        data.action_draft_approval_valid_minutes,
      ai_explanation_provider_code: data.ai_explanation_provider_code,
      sharpe_strong_threshold: data.sharpe_strong_threshold,
      sharpe_slight_threshold: data.sharpe_slight_threshold,
    });
    setAdvancedHelp(data.help_nl);
  }, [advancedQuery.data]);

  async function handleSaveAdvanced() {
    setAdvancedSaving(true);
    setAdvancedError(null);
    setAdvancedSaved(null);
    const result = await apiClient.updateAdvancedSettings(advancedForm);
    setAdvancedSaving(false);
    if (!result.ok) {
      setAdvancedError(
        "Opslaan mislukt. Controleer dat alle waarden binnen het toegestane bereik liggen.",
      );
      return;
    }
    queryClient.setQueryData(["instellingen", "advanced"], result.data);
    setAdvancedSaved("Geavanceerde instellingen opgeslagen.");
  }

  // Settings UI PR G — forecast & market query + save.
  const forecastMarketQuery = useQuery({
    queryKey: ["instellingen", "forecast-market"] as const,
    queryFn: async () => {
      const result = await apiClient.getForecastMarketSettings();
      if (!result.ok) throw new Error("forecast-market-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    const data = forecastMarketQuery.data;
    if (!data) return;
    setForecastMarketForm({
      forecast_horizon_trading_days: data.forecast_horizon_trading_days,
      forecast_ensemble_enabled: data.forecast_ensemble_enabled,
      suggestions_risk_profile: data.suggestions_risk_profile,
      universe_set: data.universe_set,
      market_data_provider: data.market_data_provider,
      market_data_sync_enabled: data.market_data_sync_enabled,
      ibkr_market_data_enabled: data.ibkr_market_data_enabled,
      ibkr_market_data_type: data.ibkr_market_data_type,
    });
    setForecastMarketHelp(data.help_nl);
  }, [forecastMarketQuery.data]);

  async function handleSaveForecastMarket() {
    setForecastMarketSaving(true);
    setForecastMarketError(null);
    setForecastMarketSaved(null);
    const result =
      await apiClient.updateForecastMarketSettings(forecastMarketForm);
    setForecastMarketSaving(false);
    if (!result.ok) {
      setForecastMarketError(
        "Opslaan mislukt. Controleer dat alle waarden binnen het toegestane bereik liggen.",
      );
      return;
    }
    queryClient.setQueryData(["instellingen", "forecast-market"], result.data);
    setForecastMarketSaved("Voorspellings- en marktdata-instellingen opgeslagen.");
  }

  // Settings UI PR H — execution gates query + save.
  const executionGateQuery = useQuery({
    queryKey: ["instellingen", "execution-gates"] as const,
    queryFn: async () => {
      const result = await apiClient.getExecutionGateSettings();
      if (!result.ok) throw new Error("execution-gates-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    const data = executionGateQuery.data;
    if (!data) return;
    setExecutionGateForm({
      ibkr_paper_order_submission_enabled:
        data.ibkr_paper_order_submission_enabled,
      submission_sweep_enabled: data.submission_sweep_enabled,
      cancel_sweep_enabled: data.cancel_sweep_enabled,
      morning_chain_after_pre_briefing: data.morning_chain_after_pre_briefing,
    });
    setExecutionGateHelp(data.help_nl);
  }, [executionGateQuery.data]);

  async function handleSaveExecutionGates() {
    setExecutionGateSaving(true);
    setExecutionGateError(null);
    setExecutionGateSaved(null);
    const result =
      await apiClient.updateExecutionGateSettings(executionGateForm);
    setExecutionGateSaving(false);
    if (!result.ok) {
      setExecutionGateError(
        "Opslaan mislukt. Controleer dat alle waarden correct zijn.",
      );
      return;
    }
    queryClient.setQueryData(["instellingen", "execution-gates"], result.data);
    setExecutionGateSaved("Uitvoerings-poorten opgeslagen.");
  }

  // Settings UI PR I — predictor tuning query + save.
  const predictorTuningQuery = useQuery({
    queryKey: ["instellingen", "predictor-tuning"] as const,
    queryFn: async () => {
      const result = await apiClient.getPredictorTuningSettings();
      if (!result.ok) throw new Error("predictor-tuning-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    const data = predictorTuningQuery.data;
    if (!data) return;
    setPredictorTuningForm({
      forecast_valid_minutes: data.forecast_valid_minutes,
      decision_packages_valid_minutes: data.decision_packages_valid_minutes,
      prediction_diary_inconclusive_tolerance_pct:
        data.prediction_diary_inconclusive_tolerance_pct,
      gbm_regime_shift_enabled: data.gbm_regime_shift_enabled,
      gbm_regime_shift_threshold_pct: data.gbm_regime_shift_threshold_pct,
    });
    setPredictorTuningHelp(data.help_nl);
  }, [predictorTuningQuery.data]);

  async function handleSavePredictorTuning() {
    setPredictorTuningSaving(true);
    setPredictorTuningError(null);
    setPredictorTuningSaved(null);
    const result =
      await apiClient.updatePredictorTuningSettings(predictorTuningForm);
    setPredictorTuningSaving(false);
    if (!result.ok) {
      setPredictorTuningError(
        "Opslaan mislukt. Controleer dat alle waarden binnen het toegestane bereik liggen.",
      );
      return;
    }
    queryClient.setQueryData(
      ["instellingen", "predictor-tuning"],
      result.data,
    );
    setPredictorTuningSaved("Voorspeller-tuning opgeslagen.");
  }

  // Settings UI PR J — market-aware scheduler query + save.
  const marketEventsQuery = useQuery({
    queryKey: ["instellingen", "market-events"] as const,
    queryFn: async () => {
      const result = await apiClient.getMarketEventsSettings();
      if (!result.ok) throw new Error("market-events-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    const data = marketEventsQuery.data;
    if (!data) return;
    setMarketEventsForm({
      per_market_close_digest_enabled: data.per_market_close_digest_enabled,
      per_market_open_alerts_enabled: data.per_market_open_alerts_enabled,
    });
    setMarketEventsHelp(data.help_nl);
    setMarketEventsFires(data.fires);
    setMarketEventsActiveSessions(data.active_sessions);
  }, [marketEventsQuery.data]);

  async function handleSaveMarketEvents() {
    setMarketEventsSaving(true);
    setMarketEventsError(null);
    setMarketEventsSaved(null);
    const result =
      await apiClient.updateMarketEventsSettings(marketEventsForm);
    setMarketEventsSaving(false);
    if (!result.ok) {
      setMarketEventsError(
        "Opslaan mislukt. Controleer de opslag-verbinding en probeer opnieuw.",
      );
      return;
    }
    queryClient.setQueryData(["instellingen", "market-events"], result.data);
    setMarketEventsSaved(
      "Markt-events opgeslagen. Werkt vanaf de eerstvolgende worker-restart.",
    );
  }

  // Settings UI PR K — notifications query + save + test.
  const notificationsQuery = useQuery({
    queryKey: ["instellingen", "notifications"] as const,
    queryFn: async () => {
      const result = await apiClient.getNotificationSettings();
      if (!result.ok) throw new Error("notifications-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    const data = notificationsQuery.data;
    if (!data) return;
    setNotificationsForm({
      smtp_host: data.smtp_host,
      smtp_port: data.smtp_port,
      smtp_username: data.smtp_username,
      // The password is never echoed back; keep the input blank.
      smtp_password: "",
      smtp_from: data.smtp_from,
      smtp_to: data.smtp_to,
      smtp_use_tls: data.smtp_use_tls,
      notifications_email_enabled: data.notifications_email_enabled,
      notification_send_on_nav_drop: data.notification_send_on_nav_drop,
      notification_send_on_position_drop:
        data.notification_send_on_position_drop,
      notification_send_on_high_confidence_sell:
        data.notification_send_on_high_confidence_sell,
    });
    setNotificationsPasswordSet(data.smtp_password_set);
    setNotificationsRealClientEnabled(
      data.notifications_email_real_client_enabled,
    );
    setNotificationsHelp(data.help_nl);
  }, [notificationsQuery.data]);

  async function handleSaveNotifications() {
    setNotificationsSaving(true);
    setNotificationsError(null);
    setNotificationsSaved(null);
    setNotificationsTestResult(null);
    const result =
      await apiClient.updateNotificationSettings(notificationsForm);
    setNotificationsSaving(false);
    if (!result.ok) {
      setNotificationsError(
        "Opslaan mislukt. Controleer de waarden en probeer opnieuw.",
      );
      return;
    }
    queryClient.setQueryData(
      ["instellingen", "notifications"],
      result.data,
    );
    setNotificationsSaved(
      "Notificaties opgeslagen. Gebruik 'Test e-mail' om SMTP te verifiëren.",
    );
    // Clear the password input — it's been persisted, never echo it.
    setNotificationsForm((prev) => ({ ...prev, smtp_password: "" }));
    setNotificationsPasswordSet(result.data.smtp_password_set);
  }

  async function handleSendTestEmail() {
    setNotificationsTestSending(true);
    setNotificationsTestResult(null);
    const result = await apiClient.sendTestEmail();
    setNotificationsTestSending(false);
    if (!result.ok) {
      setNotificationsTestResult({
        sent: false,
        status: "network_error",
        detail_nl: "Netwerkfout bij verzenden van test-e-mail.",
      });
      return;
    }
    setNotificationsTestResult({
      sent: result.data.sent,
      status: result.data.status,
      detail_nl: result.data.detail_nl,
    });
  }

  async function handleSaveDataWindows() {
    setDataWindowSaving(true);
    setDataWindowError(null);
    setDataWindowSaved(null);
    const result = await apiClient.updateDataWindowSettings(dataWindowForm);
    setDataWindowSaving(false);
    if (!result.ok) {
      setDataWindowError(
        "Opslaan mislukt. Controleer dat alle waarden ≥ 1 zijn en dat het minimum koersdagen niet groter is dan de lookback.",
      );
      return;
    }
    queryClient.setQueryData(["instellingen", "data-windows"], result.data);
    setDataWindowSaved("Data-vensters opgeslagen.");
  }

  async function handleSaveScheduler() {
    setSchedulerSaving(true);
    setSchedulerError(null);
    setSchedulerSaved(null);
    const result = await apiClient.updateSchedulerSettings(schedulerForm);
    setSchedulerSaving(false);
    if (!result.ok) {
      setSchedulerError(
        "Opslaan mislukt. Controleer dat de cron-uitdrukking 5 velden heeft en niet samenvalt met de 06:00 worker-slot.",
      );
      return;
    }
    queryClient.setQueryData(["instellingen", "scheduler"], result.data);
    setSchedulerSaved("Planning opgeslagen.");
  }

  async function handleSaveOrderPolicy() {
    setOrderPolicySaving(true);
    setOrderPolicyError(null);
    setOrderPolicySaved(null);
    const result = await apiClient.updateOrderPolicySettings(orderPolicy);
    setOrderPolicySaving(false);
    if (!result.ok) {
      setOrderPolicyError(
        "Opslaan mislukt. Controleer de waarden (alle bedragen + percentages > 0).",
      );
      return;
    }
    queryClient.setQueryData(["instellingen", "order-policy"], result.data);
    setOrderPolicySaved("Order- en suggestie-instellingen opgeslagen.");
  }

  async function handleSaveUniverseScan() {
    setUniverseScanSaving(true);
    setUniverseScanError(null);
    setUniverseScanSaved(null);
    const result = await apiClient.updateUniverseScanSettings({
      selected_codes: universeScanSelected,
    });
    setUniverseScanSaving(false);
    if (!result.ok) {
      setUniverseScanError(
        "Opslaan mislukt. Controleer de selectie en of de API beschikbaar is.",
      );
      return;
    }
    queryClient.setQueryData(
      ["instellingen", "universe-scan"],
      result.data,
    );
    setUniverseScanSaved("Scan-universum opgeslagen.");
  }

  const connectionQuery = useQuery({
    queryKey: CONNECTION_SETTINGS_KEY,
    queryFn: async () => {
      const result = await apiClient.getConnectionSettings();
      if (!result.ok) throw new Error("connection-settings-unavailable");
      return result.data;
    },
    ...FORM_QUERY_OPTIONS,
  });
  useEffect(() => {
    if (connectionQuery.data) applyConnection(connectionQuery.data);
  }, [connectionQuery.data]);

  function applyConnection(data: ConnectionSettingsResponse) {
    setConnection(connectionStateFromResponse(data));
    setConnectionKeySet(data.claude_ai_api_key_set);
    // Never reflect the (masked) key back into the input — keep it blank so a
    // save without typing omits the field and preserves the stored key.
    setConnectionKeyInput("");
  }

  const loading =
    riskQuery.isPending
    || tradingQuery.isPending
    || connectionQuery.isPending
    || universeScanQuery.isPending
    || orderPolicyQuery.isPending
    || schedulerQuery.isPending
    || dataWindowQuery.isPending
    || workerSweepQuery.isPending
    || advancedQuery.isPending
    || forecastMarketQuery.isPending
    || executionGateQuery.isPending
    || predictorTuningQuery.isPending
    || marketEventsQuery.isPending
    || notificationsQuery.isPending;
  const loadError =
    riskQuery.isError
    && tradingQuery.isError
    && connectionQuery.isError
    && universeScanQuery.isError
    && orderPolicyQuery.isError
    && schedulerQuery.isError
    && dataWindowQuery.isError
    && workerSweepQuery.isError
      ? "Instellingen konden niet worden geladen."
      : null;

  function setRiskField(
    key: keyof RiskLimitsUpdateInput,
    raw: string,
    decimal: boolean,
  ) {
    setRiskLimits((prev) => ({
      ...prev,
      [key]: decimal ? raw : raw === "" ? 0 : Number(raw),
    }));
  }

  async function handleSaveRiskLimits() {
    setRiskSaving(true);
    setRiskError(null);
    setRiskSaved(null);
    const result = await apiClient.updateRiskLimits(riskLimits);
    setRiskSaving(false);
    if (!result.ok) {
      setRiskError(
        "Opslaan mislukt. Controleer de waarden en of de API beschikbaar is.",
      );
      return;
    }
    applyRiskLimits(result.data);
    queryClient.setQueryData(RISK_LIMITS_KEY, result.data);
    setRiskSaved("Risico-limieten opgeslagen.");
  }

  async function handleSaveStrategy() {
    if (trading === null || strategy === null) return;
    setStrategySaving(true);
    setStrategyError(null);
    setStrategySaved(null);
    const next_user_strategy = {
      ...(trading.user_strategy as Record<string, unknown>),
      portfolio_goal: strategy.portfolio_goal,
      risk_level: strategy.risk_level,
      asset_mix_preference: strategy.asset_mix_preference,
      currency_preference: strategy.currency_preference,
      preferred_regions: strategy.preferred_regions,
      preferred_sectors: strategy.preferred_sectors,
      avoided_sectors: strategy.avoided_sectors,
      max_position_pct: strategy.max_position_pct,
      min_cash_reserve_pct: strategy.min_cash_reserve_pct,
      user_buffer_eur: strategy.user_buffer_eur,
      prefer_simple_belgian_tax_admin: strategy.prefer_simple_belgian_tax_admin,
      trading_target_net_pct: strategy.trading_target_net_pct,
      trading_horizon_min_months: strategy.trading_horizon_min_months,
      trading_horizon_max_months: strategy.trading_horizon_max_months,
      trading_min_position_eur: strategy.trading_min_position_eur,
      trading_max_position_eur: strategy.trading_max_position_eur,
      trading_confidence_threshold_pct: strategy.trading_confidence_threshold_pct,
      trading_max_sector_pct: strategy.trading_max_sector_pct,
      trading_min_market_cap_eur: strategy.trading_min_market_cap_eur,
      trading_max_annual_volatility_pct: strategy.trading_max_annual_volatility_pct,
      trading_total_budget_eur: strategy.trading_total_budget_eur,
      trading_fat_tail_factor: strategy.trading_fat_tail_factor,
      trading_earnings_block_days: strategy.trading_earnings_block_days,
      trading_news_buy_bias_max_boost_pct:
        strategy.trading_news_buy_bias_max_boost_pct,
    };
    const result = await apiClient.updateTradingSettings({
      allowed_universe: trading.allowed_universe,
      user_strategy: next_user_strategy,
      reason_nl: "Strategie-instellingen aangepast.",
    });
    setStrategySaving(false);
    if (!result.ok) {
      setStrategyError(
        "Opslaan mislukt. Controleer de waarden en of de API beschikbaar is.",
      );
      return;
    }
    applyTrading(result.data);
    queryClient.setQueryData(TRADING_SETTINGS_KEY, result.data);
    setStrategySaved("Strategie opgeslagen.");
  }

  async function handleSaveUniverse() {
    if (trading === null) return;
    setUniverseSaving(true);
    setUniverseError(null);
    setUniverseSaved(null);
    const next_allowed_universe = {
      ...(trading.allowed_universe as Record<string, boolean>),
      ...universe,
    };
    const result = await apiClient.updateTradingSettings({
      allowed_universe: next_allowed_universe,
      user_strategy: trading.user_strategy,
      reason_nl: "Beleggingsuniversum aangepast.",
    });
    setUniverseSaving(false);
    if (!result.ok) {
      setUniverseError(
        "Opslaan mislukt. Controleer of de API beschikbaar is.",
      );
      return;
    }
    applyTrading(result.data);
    queryClient.setQueryData(TRADING_SETTINGS_KEY, result.data);
    setUniverseSaved("Beleggingsuniversum opgeslagen.");
  }

  function toggleMulti(
    current: string[],
    value: string,
    checked: boolean,
  ): string[] {
    if (checked) {
      return current.includes(value) ? current : [...current, value];
    }
    return current.filter((v) => v !== value);
  }

  function setConnectionField<K extends keyof ConnectionState>(
    key: K,
    value: ConnectionState[K],
  ) {
    setConnection((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSaveConnection() {
    setConnectionSaving(true);
    setConnectionError(null);
    setConnectionSaved(null);
    const trimmedKey = connectionKeyInput.trim();
    const result = await apiClient.updateConnectionSettings({
      ibkr_enabled: connection.ibkr_enabled,
      ibkr_account_id: connection.ibkr_account_id.trim() || null,
      ibkr_host: connection.ibkr_host.trim() || null,
      ibkr_port:
        connection.ibkr_port.trim() === ""
          ? null
          : Number(connection.ibkr_port),
      ibkr_client_id:
        connection.ibkr_client_id.trim() === ""
          ? null
          : Number(connection.ibkr_client_id),
      ai_explanation_enabled: connection.ai_explanation_enabled,
      claude_ai_explanation_model:
        connection.claude_ai_explanation_model.trim() || null,
      claude_ai_budget_monthly_eur:
        connection.claude_ai_budget_monthly_eur.trim() || null,
      // Only send the key when the operator typed one; omit it otherwise so
      // the previously-stored key is preserved.
      ...(trimmedKey ? { claude_ai_api_key: trimmedKey } : {}),
      ai_explanation_morning_batch_enabled:
        connection.ai_explanation_morning_batch_enabled,
      ai_email_summary_enabled: connection.ai_email_summary_enabled,
      research_ai_extraction_enabled: connection.research_ai_extraction_enabled,
    });
    setConnectionSaving(false);
    if (!result.ok) {
      setConnectionError(
        "Opslaan mislukt. Controleer de waarden en of de API beschikbaar is.",
      );
      return;
    }
    applyConnection(result.data);
    queryClient.setQueryData(CONNECTION_SETTINGS_KEY, result.data);
    setConnectionSaved("Verbinding & AI opgeslagen.");
  }

  return (
    <main className="page-wrap" data-testid="instellingen-page">
      <h2>Instellingen</h2>

      {loading ? (
        <p>Bezig met laden…</p>
      ) : loadError ? (
        <p data-testid="instellingen-load-error">{loadError}</p>
      ) : (
        <>
          {/* Section 1 — Risk limits. */}
          <section style={SECTION_STYLE} data-testid="instellingen-risk-section">
            <h3 style={{ marginTop: 0 }}>Risico-limieten</h3>
            <p style={HELP_STYLE}>
              Gedragslimieten beschermen je tegen impulsieve acties en grote
              verliezen. Rekening: {riskAccountId || "DEFAULT"}.
            </p>
            {RISK_LIMIT_FIELDS.map((field) => (
              <label
                key={field.key}
                style={LABEL_STYLE}
                htmlFor={`risk-${field.key}`}
              >
                <FieldLabel label_nl={field.label_nl} help_nl={field.help_nl} />
                <input
                  id={`risk-${field.key}`}
                  data-testid={`instellingen-risk-${field.key}`}
                  type="number"
                  min={String(field.min)}
                  step={field.decimal ? "0.1" : "1"}
                  value={String(riskLimits[field.key])}
                  onChange={(event) =>
                    setRiskField(field.key, event.target.value, field.decimal)
                  }
                />
              </label>
            ))}
            <SaveBar
              testId="instellingen-risk"
              saving={riskSaving}
              savedMessage={riskSaved}
              error={riskError}
              onSave={() => void handleSaveRiskLimits()}
            />
          </section>

          {/* Section 2 — Strategy. */}
          {strategy !== null ? (
            <section
              style={SECTION_STYLE}
              data-testid="instellingen-strategy-section"
            >
              <h3 style={{ marginTop: 0 }}>Strategie</h3>
              <p style={HELP_STYLE}>
                Je voorkeurlaag voor ranking en fit — dit zijn voorkeuren, geen
                harde blokkeringen.
              </p>

              <label style={LABEL_STYLE} htmlFor="strategy-portfolio_goal">
                <FieldLabel
                  label_nl="Portefeuilledoel"
                  help_nl="Het hoofddoel waarop voorstellen worden afgestemd."
                />
                <Dropdown
                  id="strategy-portfolio_goal"
                  testId="instellingen-strategy-portfolio_goal"
                  value={strategy.portfolio_goal}
                  options={PORTFOLIO_GOAL_OPTIONS}
                  onChange={(value) =>
                    setStrategy({ ...strategy, portfolio_goal: value })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-risk_level">
                <FieldLabel
                  label_nl="Risiconiveau"
                  help_nl="Hoeveel risico je strategie mag nemen."
                />
                <Dropdown
                  id="strategy-risk_level"
                  testId="instellingen-strategy-risk_level"
                  value={strategy.risk_level}
                  options={RISK_LEVEL_OPTIONS}
                  onChange={(value) =>
                    setStrategy({ ...strategy, risk_level: value })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-asset_mix_preference">
                <FieldLabel
                  label_nl="Voorkeur assetmix"
                  help_nl="Voorkeur voor de verhouding tussen ETF’s en aandelen."
                />
                <Dropdown
                  id="strategy-asset_mix_preference"
                  testId="instellingen-strategy-asset_mix_preference"
                  value={strategy.asset_mix_preference}
                  options={ASSET_MIX_OPTIONS}
                  onChange={(value) =>
                    setStrategy({ ...strategy, asset_mix_preference: value })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-currency_preference">
                <FieldLabel
                  label_nl="Valutavoorkeur"
                  help_nl="Voorkeur voor euro en het toelaten van dollarposities."
                />
                <Dropdown
                  id="strategy-currency_preference"
                  testId="instellingen-strategy-currency_preference"
                  value={strategy.currency_preference}
                  options={CURRENCY_PREFERENCE_OPTIONS}
                  onChange={(value) =>
                    setStrategy({ ...strategy, currency_preference: value })
                  }
                />
              </label>

              <div style={{ marginTop: 12 }}>
                <FieldLabel
                  label_nl="Voorkeursregio’s"
                  help_nl="Regio’s die de voorkeur krijgen bij voorstellen."
                />
                <div style={{ marginTop: 4 }}>
                  <CheckboxGroup
                    testIdPrefix="instellingen-strategy-preferred_regions"
                    options={REGION_OPTIONS}
                    selected={strategy.preferred_regions}
                    onToggle={(value, checked) =>
                      setStrategy({
                        ...strategy,
                        preferred_regions: toggleMulti(
                          strategy.preferred_regions,
                          value,
                          checked,
                        ),
                      })
                    }
                  />
                </div>
              </div>

              <div style={{ marginTop: 12 }}>
                <FieldLabel
                  label_nl="Voorkeurssectoren"
                  help_nl="Sectoren die de voorkeur krijgen bij voorstellen."
                />
                <div style={{ marginTop: 4 }}>
                  <CheckboxGroup
                    testIdPrefix="instellingen-strategy-preferred_sectors"
                    options={SECTOR_OPTIONS}
                    selected={strategy.preferred_sectors}
                    onToggle={(value, checked) =>
                      setStrategy({
                        ...strategy,
                        preferred_sectors: toggleMulti(
                          strategy.preferred_sectors,
                          value,
                          checked,
                        ),
                      })
                    }
                  />
                </div>
              </div>

              <div style={{ marginTop: 12 }}>
                <FieldLabel
                  label_nl="Te vermijden sectoren"
                  help_nl="Sectoren die je liever vermijdt bij voorstellen."
                />
                <div style={{ marginTop: 4 }}>
                  <CheckboxGroup
                    testIdPrefix="instellingen-strategy-avoided_sectors"
                    options={SECTOR_OPTIONS}
                    selected={strategy.avoided_sectors}
                    onToggle={(value, checked) =>
                      setStrategy({
                        ...strategy,
                        avoided_sectors: toggleMulti(
                          strategy.avoided_sectors,
                          value,
                          checked,
                        ),
                      })
                    }
                  />
                </div>
              </div>

              <label style={LABEL_STYLE} htmlFor="strategy-max_position_pct">
                <FieldLabel
                  label_nl="Maximum positie per asset (%)"
                  help_nl="Hoeveel één belegging maximaal van de portefeuille mag worden."
                />
                <input
                  id="strategy-max_position_pct"
                  data-testid="instellingen-strategy-max_position_pct"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={strategy.max_position_pct}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      max_position_pct: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-min_cash_reserve_pct">
                <FieldLabel
                  label_nl="Minimale cashreserve (%)"
                  help_nl="Welk minimum deel van de portefeuille cash moet blijven."
                />
                <input
                  id="strategy-min_cash_reserve_pct"
                  data-testid="instellingen-strategy-min_cash_reserve_pct"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={strategy.min_cash_reserve_pct}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      min_cash_reserve_pct: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-user_buffer_eur">
                <FieldLabel
                  label_nl="Cashbuffer voor actiedrafts (EUR)"
                  help_nl="Dit bedrag wordt afgetrokken van je beschikbare cash voordat de aankoophoeveelheid wordt berekend. Standaard €0."
                />
                <input
                  id="strategy-user_buffer_eur"
                  data-testid="instellingen-user-buffer-input"
                  type="number"
                  min="0"
                  step="1"
                  value={strategy.user_buffer_eur}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      user_buffer_eur: event.target.value,
                    })
                  }
                />
              </label>

              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginTop: 12,
                  fontSize: 13,
                }}
                htmlFor="strategy-prefer_simple_belgian_tax_admin"
              >
                <input
                  id="strategy-prefer_simple_belgian_tax_admin"
                  data-testid="instellingen-strategy-prefer_simple_belgian_tax_admin"
                  type="checkbox"
                  checked={strategy.prefer_simple_belgian_tax_admin}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      prefer_simple_belgian_tax_admin: event.target.checked,
                    })
                  }
                />
                Voorkeur voor eenvoudige Belgische fiscale administratie
                <HelpTooltip text="Geeft voorrang aan beleggingen die je Belgische belastingaangifte eenvoudig houden." />
              </label>

              {/* V1.2 profit-harvest cycle parameters. Grouped under a
               * sub-heading so they're visually distinct from the
               * existing strategy preferences. */}
              <h3
                style={{ marginTop: 24, fontSize: 14, fontWeight: 700 }}
                data-testid="instellingen-profit-harvest-heading"
              >
                Winst-cyclus instellingen
              </h3>
              <p style={HELP_STYLE}>
                Parameters voor de {`"`}kopen → wachten tot +X % netto →
                verkopen → herinvesteren{`"`} strategie. De software gebruikt
                deze waarden om suggesties te filteren en posities te
                grootten.
              </p>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_target_net_pct">
                <FieldLabel
                  label_nl="Winstdoel per cyclus (netto %)"
                  help_nl="Wanneer een aandeel dit netto winstpercentage haalt verkoopt het systeem automatisch. De verkoop-LMT wordt boven dit doel gezet om Belgische beurstaks te compenseren. Standaard 4 %."
                />
                <input
                  id="strategy-trading_target_net_pct"
                  data-testid="instellingen-strategy-trading_target_net_pct"
                  type="number"
                  min="1"
                  max="50"
                  step="0.1"
                  value={strategy.trading_target_net_pct}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_target_net_pct: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_horizon_min_months">
                <FieldLabel
                  label_nl="Minimale horizon (maanden)"
                  help_nl="Onderkant van het tijdsvenster waarin het systeem het winstdoel verwacht te halen. Standaard 3."
                />
                <input
                  id="strategy-trading_horizon_min_months"
                  data-testid="instellingen-strategy-trading_horizon_min_months"
                  type="number"
                  min="1"
                  max="24"
                  step="1"
                  value={strategy.trading_horizon_min_months}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_horizon_min_months: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_horizon_max_months">
                <FieldLabel
                  label_nl="Maximale horizon (maanden)"
                  help_nl="Bovenkant van het tijdsvenster voor het winstdoel. Het systeem berekent de kans op +X % binnen deze periode. Standaard 6."
                />
                <input
                  id="strategy-trading_horizon_max_months"
                  data-testid="instellingen-strategy-trading_horizon_max_months"
                  type="number"
                  min="1"
                  max="24"
                  step="1"
                  value={strategy.trading_horizon_max_months}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_horizon_max_months: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_min_position_eur">
                <FieldLabel
                  label_nl="Minimale positie per aandeel (EUR)"
                  help_nl="Ondergrens voor de overtuiging-gewogen positiegrootte. Bij lage overtuiging krijgt een aandeel dit minimumbedrag. Standaard €25.000."
                />
                <input
                  id="strategy-trading_min_position_eur"
                  data-testid="instellingen-strategy-trading_min_position_eur"
                  type="number"
                  min="1"
                  step="1000"
                  value={strategy.trading_min_position_eur}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_min_position_eur: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_max_position_eur">
                <FieldLabel
                  label_nl="Maximale positie per aandeel (EUR)"
                  help_nl="Bovengrens voor de overtuiging-gewogen positiegrootte. Bij maximale overtuiging krijgt een aandeel dit maximumbedrag. Standaard €100.000."
                />
                <input
                  id="strategy-trading_max_position_eur"
                  data-testid="instellingen-strategy-trading_max_position_eur"
                  type="number"
                  min="1"
                  step="1000"
                  value={strategy.trading_max_position_eur}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_max_position_eur: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_confidence_threshold_pct">
                <FieldLabel
                  label_nl="Minimum overtuiging voor suggestie (%)"
                  help_nl="Een aandeel verschijnt alleen als suggestie als het model deze kans of meer berekent op het halen van het winstdoel binnen de horizon. Standaard 70 %."
                />
                <input
                  id="strategy-trading_confidence_threshold_pct"
                  data-testid="instellingen-strategy-trading_confidence_threshold_pct"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={strategy.trading_confidence_threshold_pct}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_confidence_threshold_pct: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_max_sector_pct">
                <FieldLabel
                  label_nl="Maximum per sector (%)"
                  help_nl="Begrenst hoeveel van het trading-budget in één sector mag zitten om concentratierisico te beperken. Standaard 25 %."
                />
                <input
                  id="strategy-trading_max_sector_pct"
                  data-testid="instellingen-strategy-trading_max_sector_pct"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={strategy.trading_max_sector_pct}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_max_sector_pct: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_min_market_cap_eur">
                <FieldLabel
                  label_nl="Minimum marktkapitalisatie (EUR)"
                  help_nl="Aandelen met een marktkapitalisatie onder deze grens worden niet voorgesteld — small-caps en penny stocks worden uitgesloten. Standaard €5 miljard."
                />
                <input
                  id="strategy-trading_min_market_cap_eur"
                  data-testid="instellingen-strategy-trading_min_market_cap_eur"
                  type="number"
                  min="1"
                  step="100000000"
                  value={strategy.trading_min_market_cap_eur}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_min_market_cap_eur: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_max_annual_volatility_pct">
                <FieldLabel
                  label_nl="Maximum jaarvolatiliteit (%)"
                  help_nl="Aandelen met een jaarvolatiliteit boven deze grens worden niet voorgesteld — hoge volatiliteit verhoogt kapitaalverliesrisico. Standaard 30 %."
                />
                <input
                  id="strategy-trading_max_annual_volatility_pct"
                  data-testid="instellingen-strategy-trading_max_annual_volatility_pct"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={strategy.trading_max_annual_volatility_pct}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_max_annual_volatility_pct: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_total_budget_eur">
                <FieldLabel
                  label_nl="Totale trading-budget (EUR)"
                  help_nl="Totaal bedrag dat het systeem mag inzetten in de profit-harvest strategie. Rest blijft op cash/termijnrekening. Standaard €1.000.000."
                />
                <input
                  id="strategy-trading_total_budget_eur"
                  data-testid="instellingen-strategy-trading_total_budget_eur"
                  type="number"
                  min="1"
                  step="10000"
                  value={strategy.trading_total_budget_eur}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_total_budget_eur: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_fat_tail_factor">
                <FieldLabel
                  label_nl="Fat-tail correctie"
                  help_nl="Vermenigvuldigt de volatiliteit in de kans-berekening om rekening te houden met extreme bewegingen. 1.0 = geen correctie (Gaussisch); 1.15 ≈ Student-t met df ≈ 5 (empirisch passend voor aandelen). Standaard 1.15."
                />
                <input
                  id="strategy-trading_fat_tail_factor"
                  data-testid="instellingen-strategy-trading_fat_tail_factor"
                  type="number"
                  min="0.5"
                  max="2.5"
                  step="0.05"
                  value={strategy.trading_fat_tail_factor}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_fat_tail_factor: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_earnings_block_days">
                <FieldLabel
                  label_nl="Earnings-blokkering (dagen)"
                  help_nl="Aantal kalenderdagen vóór een earnings-publicatie waarin het systeem geen nieuwe BUY-suggesties doet. Earnings zijn binaire events; een aandeel kan ±20% springen. 0 = uit. Standaard 5."
                />
                <input
                  id="strategy-trading_earnings_block_days"
                  data-testid="instellingen-strategy-trading_earnings_block_days"
                  type="number"
                  min="0"
                  max="30"
                  step="1"
                  value={strategy.trading_earnings_block_days}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_earnings_block_days: event.target.value,
                    })
                  }
                />
              </label>

              <label style={LABEL_STYLE} htmlFor="strategy-trading_news_buy_bias_max_boost_pct">
                <FieldLabel
                  label_nl="Nieuws-overtuiging boost (max %)"
                  help_nl="Bij positieve nieuwsstroom (analist-verhoging, dividendverhoging, contractwinst, insider-aankopen) verhoogt het systeem de overtuigingsscore met maximaal dit percentage. 0 = uit. Standaard 5."
                />
                <input
                  id="strategy-trading_news_buy_bias_max_boost_pct"
                  data-testid="instellingen-strategy-trading_news_buy_bias_max_boost_pct"
                  type="number"
                  min="0"
                  max="20"
                  step="1"
                  value={strategy.trading_news_buy_bias_max_boost_pct}
                  onChange={(event) =>
                    setStrategy({
                      ...strategy,
                      trading_news_buy_bias_max_boost_pct: event.target.value,
                    })
                  }
                />
              </label>

              <SaveBar
                testId="instellingen-strategy"
                saving={strategySaving}
                savedMessage={strategySaved}
                error={strategyError}
                onSave={() => void handleSaveStrategy()}
              />
            </section>
          ) : null}

          {/* Section 3 — Universe. */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-universe-section"
          >
            <h3 style={{ marginTop: 0 }}>Beleggingsuniversum</h3>
            <p style={HELP_STYLE}>
              De harde veiligheidsfilter voor toegestane beleggingen. Wat hier
              uit staat, wordt nooit voorgesteld.
            </p>

            {ALLOWED_UNIVERSE_TOGGLES.map((toggle) => (
              <label
                key={toggle.key}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginTop: 10,
                  fontSize: 13,
                }}
                htmlFor={`universe-${toggle.key}`}
              >
                <input
                  id={`universe-${toggle.key}`}
                  data-testid={`instellingen-universe-${toggle.key}`}
                  type="checkbox"
                  checked={universe[toggle.key] === true}
                  onChange={(event) =>
                    setUniverse({
                      ...universe,
                      [toggle.key]: event.target.checked,
                    })
                  }
                />
                {toggle.label_nl}
                <HelpTooltip text={toggle.help_nl} />
              </label>
            ))}

            {/* V1.2 §BQ / CLAUDE.md §4: per-beurs vinkjes. */}
            <div
              style={{ marginTop: 18 }}
              data-testid="instellingen-exchanges-section"
            >
              <FieldLabel
                label_nl="Beurzen (per-exchange aan/uit)"
                help_nl="Kies welke beurzen het systeem in de universum-scan en suggesties opneemt. CLAUDE.md §4 default: alles aan."
              />
              {ALLOWED_EXCHANGE_TOGGLES.map((toggle) => (
                <label
                  key={toggle.key}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginTop: 8,
                    fontSize: 13,
                  }}
                  htmlFor={`exchange-${toggle.key}`}
                >
                  <input
                    id={`exchange-${toggle.key}`}
                    data-testid={`instellingen-exchange-${toggle.key}`}
                    type="checkbox"
                    checked={universe[toggle.key] === true}
                    onChange={(event) =>
                      setUniverse({
                        ...universe,
                        [toggle.key]: event.target.checked,
                      })
                    }
                  />
                  {toggle.label_nl}
                  <HelpTooltip text={toggle.help_nl} />
                </label>
              ))}
            </div>

            <div style={{ marginTop: 16 }}>
              <FieldLabel
                label_nl="Altijd geblokkeerd (versie 1)"
                help_nl="Deze assettypes zijn in versie 1 altijd geblokkeerd en kunnen hier niet worden aangezet."
              />
              <p
                data-testid="instellingen-universe-blocked"
                style={{ ...HELP_STYLE, marginTop: 4 }}
              >
                {blockedAssetTypes.length > 0
                  ? blockedAssetTypes.join(", ")
                  : "Geen"}
              </p>
            </div>

            <SaveBar
              testId="instellingen-universe"
              saving={universeSaving}
              savedMessage={universeSaved}
              error={universeError}
              onSave={() => void handleSaveUniverse()}
            />
          </section>

          {/* Section 4a-bis — Watchlist favorites + exclusions (V1.2 §AU). */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-watchlist-preferences-section"
          >
            <WatchlistPreferencesSettings />
          </section>

          {/* Section 4a-ter — Operator-configureerbaar winstdoel (§AZ). */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-profit-target-section"
          >
            <ProfitTargetSetting />
          </section>

          {/* Section 4b — Scan markets (multi-select). */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-universe-scan-section"
          >
            <h2 style={{ margin: 0 }}>Scan-universum (beurzen)</h2>
            <p style={{ marginTop: 4, color: "#374151", fontSize: 13 }}>
              {universeScanHelp || "Kies welke beurzen het systeem dagelijks scant."}
            </p>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                gap: 6,
                marginTop: 10,
              }}
            >
              {universeScanAvailable.map((option) => (
                <label
                  key={option.code}
                  data-testid={`instellingen-universe-scan-option-${option.code}`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "4px 6px",
                    border: "1px solid #e5e7eb",
                    borderRadius: 4,
                    fontSize: 13,
                  }}
                >
                  <input
                    type="checkbox"
                    checked={universeScanSelected.includes(option.code)}
                    onChange={(e) =>
                      toggleUniverseScanCode(option.code, e.target.checked)
                    }
                  />
                  <span>{option.label_nl}</span>
                </label>
              ))}
            </div>
            <div style={{ marginTop: 12, display: "flex", gap: 12, alignItems: "center" }}>
              <button
                type="button"
                onClick={() => void handleSaveUniverseScan()}
                disabled={universeScanSaving}
                data-testid="instellingen-universe-scan-save"
                style={{
                  background: "#1f2937",
                  color: "#ffffff",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: 4,
                  cursor: universeScanSaving ? "not-allowed" : "pointer",
                  fontSize: 14,
                }}
              >
                {universeScanSaving ? "Opslaan…" : "Scan-universum opslaan"}
              </button>
              {universeScanSaved ? (
                <span style={{ color: "#15803d", fontSize: 13 }}>
                  {universeScanSaved}
                </span>
              ) : null}
              {universeScanError ? (
                <span
                  data-testid="instellingen-universe-scan-error"
                  style={{ color: "#b91c1c", fontSize: 13 }}
                >
                  {universeScanError}
                </span>
              ) : null}
            </div>
          </section>

          {/* Section 4c — Order policy + suggestion filters (PR A). */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-order-policy-section"
          >
            <h2 style={{ margin: 0 }}>Orders &amp; suggesties</h2>
            <p style={{ marginTop: 4, color: "#374151", fontSize: 13 }}>
              {orderPolicyHelp
                || "Standaard order-grootte en suggestie-filters. Suggesties blijven alleen-lezen advies; niets wordt automatisch geplaatst."}
            </p>
            <div className="grid one-column" style={{ marginTop: 10 }}>
              <label>
                Standaard koopbedrag (EUR)
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  data-testid="instellingen-order-policy-default_buy_value_eur"
                  value={orderPolicy.default_buy_value_eur}
                  onChange={(e) =>
                    setOrderPolicyField("default_buy_value_eur", e.target.value)
                  }
                />
                <span className="help-text">
                  Wat het systeem standaard voorstelt bij elke &ldquo;Kopen&rdquo;
                  suggestie. Verhoog voor grotere posities; verlaag voor
                  voorzichtigere instap.
                </span>
              </label>
              <label>
                Bijkoop-percentage (0–1, bv 0.25 = 25%)
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  data-testid="instellingen-order-policy-default_top_up_pct"
                  value={orderPolicy.default_top_up_pct}
                  onChange={(e) =>
                    setOrderPolicyField("default_top_up_pct", e.target.value)
                  }
                />
                <span className="help-text">
                  Bij &ldquo;Langzaam bijkopen&rdquo;: hoeveel van je huidige
                  positie er voorgesteld wordt om bij te kopen. 0.25 = 25%.
                </span>
              </label>
              <label>
                Verminder-percentage (0–1)
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  data-testid="instellingen-order-policy-default_reduce_pct"
                  value={orderPolicy.default_reduce_pct}
                  onChange={(e) =>
                    setOrderPolicyField("default_reduce_pct", e.target.value)
                  }
                />
                <span className="help-text">
                  Bij &ldquo;Verminderen&rdquo;: hoeveel van je positie er
                  voorgesteld wordt te verkopen.
                </span>
              </label>
              <label>
                Sectorconcentratie-cap (%)
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  data-testid="instellingen-order-policy-max_sector_pct"
                  value={orderPolicy.max_sector_pct}
                  onChange={(e) =>
                    setOrderPolicyField("max_sector_pct", e.target.value)
                  }
                />
                <span className="help-text">
                  Boven dit percentage per sector downgradet het systeem
                  nieuwe &ldquo;Kopen&rdquo; voorstellen naar &ldquo;Bekijken&rdquo;
                  (diversificatie-gate).
                </span>
              </label>
              <label>
                Kosten-vs-rendement drempel
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  data-testid="instellingen-order-policy-cost_dominates_ratio"
                  value={orderPolicy.cost_dominates_ratio}
                  onChange={(e) =>
                    setOrderPolicyField("cost_dominates_ratio", e.target.value)
                  }
                />
                <span className="help-text">
                  Als verwacht rendement minder is dan deze factor maal de
                  geschatte transactiekosten, dan &ldquo;Bekijken&rdquo; in
                  plaats van &ldquo;Kopen&rdquo;. Standaard 3× — verlaag voor
                  een toleranter filter.
                </span>
              </label>
              <label>
                Suggestiegeldigheid (minuten)
                <input
                  type="number"
                  step="1"
                  min="1"
                  data-testid="instellingen-order-policy-suggestion_valid_minutes"
                  value={orderPolicy.suggestion_valid_minutes}
                  onChange={(e) =>
                    setOrderPolicyField(
                      "suggestion_valid_minutes",
                      Number(e.target.value),
                    )
                  }
                />
                <span className="help-text">
                  Hoe lang een suggestie geldig blijft voordat hij automatisch
                  als &ldquo;expired&rdquo; gemarkeerd wordt. 1440 = 24 uur.
                </span>
              </label>
            </div>
            <div style={{ marginTop: 12, display: "flex", gap: 12, alignItems: "center" }}>
              <button
                type="button"
                onClick={() => void handleSaveOrderPolicy()}
                disabled={orderPolicySaving}
                data-testid="instellingen-order-policy-save"
                style={{
                  background: "#1f2937",
                  color: "#ffffff",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: 4,
                  cursor: orderPolicySaving ? "not-allowed" : "pointer",
                  fontSize: 14,
                }}
              >
                {orderPolicySaving ? "Opslaan…" : "Orders & suggesties opslaan"}
              </button>
              {orderPolicySaved ? (
                <span style={{ color: "#15803d", fontSize: 13 }}>
                  {orderPolicySaved}
                </span>
              ) : null}
              {orderPolicyError ? (
                <span
                  data-testid="instellingen-order-policy-error"
                  style={{ color: "#b91c1c", fontSize: 13 }}
                >
                  {orderPolicyError}
                </span>
              ) : null}
            </div>
          </section>

          {/* Section 4d — Scheduler cadence (PR B). */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-scheduler-section"
          >
            <h2 style={{ margin: 0 }}>Planning &amp; cadans</h2>
            <p style={{ marginTop: 4, color: "#374151", fontSize: 13 }}>
              {schedulerHelp
                || "Wanneer de morgenbriefing klaarstaat en hoe vaak IBKR-posities worden bijgewerkt."}
            </p>
            <div className="grid one-column" style={{ marginTop: 10 }}>
              <label>
                Morgenbriefing-cron (5 velden, Europe/Brussels)
                <input
                  type="text"
                  data-testid="instellingen-scheduler-cron"
                  value={schedulerForm.scheduler_daily_briefing_cron}
                  onChange={(e) =>
                    setSchedulerForm((p) => ({
                      ...p,
                      scheduler_daily_briefing_cron: e.target.value,
                    }))
                  }
                  placeholder="30 6 * * *"
                />
                <span className="help-text">
                  Standaard <code>30 6 * * *</code> (06:30). Mag niet
                  samenvallen met de worker&rsquo;s vergrendelde 06:00 slot.
                  Wijzigingen gelden vanaf de eerstvolgende API-herstart.
                </span>
              </label>
              <label>
                IBKR-sync interval (minuten)
                <input
                  type="number"
                  step="1"
                  min="1"
                  data-testid="instellingen-scheduler-ibkr_sync"
                  value={schedulerForm.ibkr_sync_interval_minutes}
                  onChange={(e) =>
                    setSchedulerForm((p) => ({
                      ...p,
                      ibkr_sync_interval_minutes: Number(e.target.value),
                    }))
                  }
                />
                <span className="help-text">
                  Hoe vaak posities/cash bij IBKR opgehaald worden. Lager
                  = verser; hoger = minder API-belasting. Wijziging is
                  direct actief op de volgende tick.
                </span>
              </label>
            </div>
            <div style={{ marginTop: 12, display: "flex", gap: 12, alignItems: "center" }}>
              <button
                type="button"
                onClick={() => void handleSaveScheduler()}
                disabled={schedulerSaving}
                data-testid="instellingen-scheduler-save"
                style={{
                  background: "#1f2937",
                  color: "#ffffff",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: 4,
                  cursor: schedulerSaving ? "not-allowed" : "pointer",
                  fontSize: 14,
                }}
              >
                {schedulerSaving ? "Opslaan…" : "Planning opslaan"}
              </button>
              {schedulerSaved ? (
                <span style={{ color: "#15803d", fontSize: 13 }}>
                  {schedulerSaved}
                </span>
              ) : null}
              {schedulerError ? (
                <span
                  data-testid="instellingen-scheduler-error"
                  style={{ color: "#b91c1c", fontSize: 13 }}
                >
                  {schedulerError}
                </span>
              ) : null}
            </div>
          </section>

          {/* Section 4e — Data windows (PR C). */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-data-windows-section"
          >
            <h2 style={{ margin: 0 }}>Marktdata &amp; modellen</h2>
            <p style={{ marginTop: 4, color: "#374151", fontSize: 13 }}>
              {dataWindowHelp
                || "Lookbacks en cache-vensters die de morgenchain gebruikt."}
            </p>
            <div className="grid one-column" style={{ marginTop: 10 }}>
              <label>
                Voorspellings-lookback (dagen)
                <input
                  type="number"
                  step="1"
                  min="1"
                  data-testid="instellingen-data-history_lookback"
                  value={dataWindowForm.forecast_history_lookback_days}
                  onChange={(e) =>
                    setDataWindowForm((p) => ({
                      ...p,
                      forecast_history_lookback_days: Number(e.target.value),
                    }))
                  }
                />
                <span className="help-text">
                  Hoe ver het model terugkijkt om voorspellingen te bouwen.
                  Standaard 400. Hoger = robuuster maar meer EODHD-calls.
                </span>
              </label>
              <label>
                Minimum koersdagen voor GBM-fit
                <input
                  type="number"
                  step="1"
                  min="1"
                  data-testid="instellingen-data-min_bars"
                  value={dataWindowForm.forecast_minimum_bars_required}
                  onChange={(e) =>
                    setDataWindowForm((p) => ({
                      ...p,
                      forecast_minimum_bars_required: Number(e.target.value),
                    }))
                  }
                />
                <span className="help-text">
                  Zonder zoveel handelsdagen historie wordt geen GBM-voorspelling
                  gemaakt. 60 is het wiskundige minimum voor stabiele
                  parameters.
                </span>
              </label>
              <label>
                Briefing-tijdvenster (uren)
                <input
                  type="number"
                  step="1"
                  min="1"
                  data-testid="instellingen-data-briefing_lookback"
                  value={dataWindowForm.daily_briefing_lookback_hours}
                  onChange={(e) =>
                    setDataWindowForm((p) => ({
                      ...p,
                      daily_briefing_lookback_hours: Number(e.target.value),
                    }))
                  }
                />
                <span className="help-text">
                  Welke periode de morgenbriefing samenvat. 24u = sinds
                  gisteren.
                </span>
              </label>
              <label>
                Scan-cache TTL (uren)
                <input
                  type="number"
                  step="1"
                  min="0"
                  data-testid="instellingen-data-scan_cache_ttl"
                  value={dataWindowForm.universe_scan_cache_ttl_hours}
                  onChange={(e) =>
                    setDataWindowForm((p) => ({
                      ...p,
                      universe_scan_cache_ttl_hours: Number(e.target.value),
                    }))
                  }
                />
                <span className="help-text">
                  Hoe lang opgeslagen scan-resultaten hergebruikt worden
                  voordat ze opnieuw opgehaald worden. 0 = altijd ververwen
                  (kostbaarste optie); 24 is de standaard.
                </span>
              </label>
            </div>
            <div style={{ marginTop: 12, display: "flex", gap: 12, alignItems: "center" }}>
              <button
                type="button"
                onClick={() => void handleSaveDataWindows()}
                disabled={dataWindowSaving}
                data-testid="instellingen-data-windows-save"
                style={{
                  background: "#1f2937",
                  color: "#ffffff",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: 4,
                  cursor: dataWindowSaving ? "not-allowed" : "pointer",
                  fontSize: 14,
                }}
              >
                {dataWindowSaving ? "Opslaan…" : "Data-vensters opslaan"}
              </button>
              {dataWindowSaved ? (
                <span style={{ color: "#15803d", fontSize: 13 }}>
                  {dataWindowSaved}
                </span>
              ) : null}
              {dataWindowError ? (
                <span
                  data-testid="instellingen-data-windows-error"
                  style={{ color: "#b91c1c", fontSize: 13 }}
                >
                  {dataWindowError}
                </span>
              ) : null}
            </div>
          </section>

          {/* Section 4f — Worker sweeps + EODHD (PR D). */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-worker-sweeps-section"
          >
            <h2 style={{ margin: 0 }}>Worker-sweeps &amp; EODHD</h2>
            <p style={{ marginTop: 4, color: "#374151", fontSize: 13 }}>
              {workerSweepHelp
                || "Worker-zijde cadens en EODHD-rate-limit. Sweep-interval geldt vanaf de eerstvolgende worker-restart; retry/alert/rate-limit nemen direct effect."}
            </p>
            <div className="grid one-column" style={{ marginTop: 10 }}>
              <label>
                Sweep-interval (seconden)
                <input
                  type="number"
                  step="1"
                  min="1"
                  data-testid="instellingen-worker-sweep_interval"
                  value={workerSweepForm.sweep_interval_seconds}
                  onChange={(e) =>
                    setWorkerSweepForm((p) => ({
                      ...p,
                      sweep_interval_seconds: Number(e.target.value),
                    }))
                  }
                />
                <span className="help-text">
                  Hoe vaak de worker openstaande orders + cancels naar IBKR
                  verzendt. Standaard 60s. Wijziging vereist een
                  worker-restart om door te dringen tot de interval-job
                  registratie.
                </span>
              </label>
              <label>
                Sweep-retry pogingen
                <input
                  type="number"
                  step="1"
                  min="1"
                  data-testid="instellingen-worker-sweep_retries"
                  value={workerSweepForm.sweep_retry_max_attempts}
                  onChange={(e) =>
                    setWorkerSweepForm((p) => ({
                      ...p,
                      sweep_retry_max_attempts: Number(e.target.value),
                    }))
                  }
                />
                <span className="help-text">
                  Max aantal pogingen binnen één tick voordat een
                  voorbijgaande IBKR-fout als blijvend telt. Standaard 3.
                </span>
              </label>
              <label>
                Sweep-retry backoff (seconden)
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  data-testid="instellingen-worker-sweep_backoff"
                  value={workerSweepForm.sweep_retry_backoff_seconds}
                  onChange={(e) =>
                    setWorkerSweepForm((p) => ({
                      ...p,
                      sweep_retry_backoff_seconds: e.target.value,
                    }))
                  }
                />
                <span className="help-text">
                  Tussen elke retry wacht het systeem
                  <code> backoff × 2^(poging-1)</code> seconden. Standaard
                  2.0 = 2s, 4s, 8s.
                </span>
              </label>
              <label>
                Foutdrempel voor alert
                <input
                  type="number"
                  step="1"
                  min="1"
                  data-testid="instellingen-worker-sweep_alert"
                  value={workerSweepForm.sweep_alert_after_consecutive_errors}
                  onChange={(e) =>
                    setWorkerSweepForm((p) => ({
                      ...p,
                      sweep_alert_after_consecutive_errors: Number(
                        e.target.value,
                      ),
                    }))
                  }
                />
                <span className="help-text">
                  Na hoeveel opeenvolgende foute sweep-ticks de operator
                  een systeemmelding krijgt. Standaard 3.
                </span>
              </label>
              <label>
                EODHD rate-limit (req/sec)
                <input
                  type="number"
                  step="1"
                  min="1"
                  data-testid="instellingen-worker-eodhd_rate"
                  value={workerSweepForm.eodhd_rate_limit_per_second}
                  onChange={(e) =>
                    setWorkerSweepForm((p) => ({
                      ...p,
                      eodhd_rate_limit_per_second: Number(e.target.value),
                    }))
                  }
                />
                <span className="help-text">
                  Maximaal aantal EODHD-requests per seconde. Onder je
                  abonnementsplan houden om throttling te voorkomen.
                </span>
              </label>
            </div>
            <div style={{ marginTop: 12, display: "flex", gap: 12, alignItems: "center" }}>
              <button
                type="button"
                onClick={() => void handleSaveWorkerSweeps()}
                disabled={workerSweepSaving}
                data-testid="instellingen-worker-sweeps-save"
                style={{
                  background: "#1f2937",
                  color: "#ffffff",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: 4,
                  cursor: workerSweepSaving ? "not-allowed" : "pointer",
                  fontSize: 14,
                }}
              >
                {workerSweepSaving ? "Opslaan…" : "Worker-sweeps opslaan"}
              </button>
              {workerSweepSaved ? (
                <span style={{ color: "#15803d", fontSize: 13 }}>
                  {workerSweepSaved}
                </span>
              ) : null}
              {workerSweepError ? (
                <span
                  data-testid="instellingen-worker-sweeps-error"
                  style={{ color: "#b91c1c", fontSize: 13 }}
                >
                  {workerSweepError}
                </span>
              ) : null}
            </div>
          </section>

          {/* Section 4i — Uitvoerings-poorten (PR H). Safety-critical;
              rendered with a red-bordered warning callout. */}
          <section
            style={{
              ...SECTION_STYLE,
              border: "2px solid #fca5a5",
              background: "#fef2f2",
            }}
            data-testid="instellingen-execution-gates-section"
          >
            <h2 style={{ margin: 0, color: "#991b1b" }}>
              Uitvoerings-poorten
            </h2>
            <p
              style={{
                marginTop: 4,
                color: "#7f1d1d",
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              WAARSCHUWING — veiligheids-kritisch. Deze toggles openen
              stap voor stap de weg van suggestie naar live IBKR-order.
              Schakel alleen in als je het volledig begrijpt.
            </p>
            <p style={{ marginTop: 4, color: "#374151", fontSize: 13 }}>
              {executionGateHelp
                || "Veiligheids-kritische uitvoerings-poorten. Sweep- en morgen-chain-toggles zijn worker-zijde en gelden vanaf de eerstvolgende worker-restart."}
            </p>
            <div className="grid one-column" style={{ marginTop: 10 }}>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-execution-paper-submit"
                  checked={
                    executionGateForm.ibkr_paper_order_submission_enabled
                  }
                  onChange={(e) =>
                    setExecutionGateForm((p) => ({
                      ...p,
                      ibkr_paper_order_submission_enabled: e.target.checked,
                    }))
                  }
                />{" "}
                IBKR paper-order submit inschakelen (API)
                <span className="help-text">
                  Master switch voor alle order-submissies naar IBKR
                  (paper-account). Uit (standaard) = de API plaatst nooit
                  een order, ook niet na goedkeuring. Aan = goedgekeurde
                  Action Drafts worden via TWS verzonden.
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-execution-submission-sweep"
                  checked={executionGateForm.submission_sweep_enabled}
                  onChange={(e) =>
                    setExecutionGateForm((p) => ({
                      ...p,
                      submission_sweep_enabled: e.target.checked,
                    }))
                  }
                />{" "}
                Worker-submission-sweep inschakelen
                <span className="help-text">
                  Uit (standaard) = worker doet geen periodieke order-
                  submissies. Aan = worker checkt elke sweep-tick of er
                  klaarstaande goedgekeurde drafts zijn en stuurt die
                  naar IBKR. Werkt alleen als de API-toggle hierboven
                  ook aan staat.
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-execution-cancel-sweep"
                  checked={executionGateForm.cancel_sweep_enabled}
                  onChange={(e) =>
                    setExecutionGateForm((p) => ({
                      ...p,
                      cancel_sweep_enabled: e.target.checked,
                    }))
                  }
                />{" "}
                Worker-cancel-sweep inschakelen
                <span className="help-text">
                  Uit (standaard) = worker stuurt geen cancel-instructies
                  naar IBKR. Aan = openstaande cancels worden periodiek
                  doorgestuurd. Vereist een actieve order-sessie.
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-execution-morning-chain"
                  checked={
                    executionGateForm.morning_chain_after_pre_briefing
                  }
                  onChange={(e) =>
                    setExecutionGateForm((p) => ({
                      ...p,
                      morning_chain_after_pre_briefing: e.target.checked,
                    }))
                  }
                />{" "}
                Morgen-chain direct na pre-briefing
                <span className="help-text">
                  Uit (standaard) = morgen-chain (sync → forecast →
                  suggesties) draait alleen op de eigen cron. Aan = de
                  chain wordt ook direct na elke pre-briefing getrigger,
                  zodat een nieuwe briefing meteen verse suggesties geeft.
                </span>
              </label>
            </div>
            <div
              style={{
                marginTop: 12,
                display: "flex",
                gap: 12,
                alignItems: "center",
              }}
            >
              <button
                type="button"
                onClick={() => void handleSaveExecutionGates()}
                disabled={executionGateSaving}
                data-testid="instellingen-execution-gates-save"
                style={{
                  background: "#991b1b",
                  color: "#ffffff",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: 4,
                  cursor: executionGateSaving ? "not-allowed" : "pointer",
                  fontSize: 14,
                }}
              >
                {executionGateSaving
                  ? "Opslaan…"
                  : "Uitvoerings-poorten opslaan"}
              </button>
              {executionGateSaved ? (
                <span style={{ color: "#15803d", fontSize: 13 }}>
                  {executionGateSaved}
                </span>
              ) : null}
              {executionGateError ? (
                <span
                  data-testid="instellingen-execution-gates-error"
                  style={{ color: "#b91c1c", fontSize: 13 }}
                >
                  {executionGateError}
                </span>
              ) : null}
            </div>
          </section>

          {/* Section 4h — Forecast & marktdata (PR G). */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-forecast-market-section"
          >
            <h2 style={{ margin: 0 }}>Voorspelling &amp; marktdata</h2>
            <p style={{ marginTop: 4, color: "#374151", fontSize: 13 }}>
              {forecastMarketHelp
                || "Hoe ver het systeem vooruitkijkt, welke modellen meedoen, welk risico-profiel suggesties hebben, en welke marktdata-feeds actief zijn."}
            </p>
            <div className="grid one-column" style={{ marginTop: 10 }}>
              <label>
                Voorspellings-horizon (handelsdagen)
                <input
                  type="number"
                  step="1"
                  min="1"
                  data-testid="instellingen-forecast-horizon"
                  value={forecastMarketForm.forecast_horizon_trading_days}
                  onChange={(e) =>
                    setForecastMarketForm((p) => ({
                      ...p,
                      forecast_horizon_trading_days: Number(e.target.value),
                    }))
                  }
                />
                <span className="help-text">
                  Hoeveel handelsdagen vooruit de modellen voorspellen.
                  Standaard 21 (≈ één maand). Hoger = bredere
                  onzekerheidsband, lager = scherper maar korter zicht.
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-forecast-ensemble"
                  checked={forecastMarketForm.forecast_ensemble_enabled}
                  onChange={(e) =>
                    setForecastMarketForm((p) => ({
                      ...p,
                      forecast_ensemble_enabled: e.target.checked,
                    }))
                  }
                />{" "}
                Ensemble-voorspelling inschakelen
                <span className="help-text">
                  Uit (standaard) = alleen GBM. Aan = GBM + Momentum +
                  Mean-reversion (en QVM als er een fundamentele
                  universum-set is). Combineert meerdere modellen voor
                  robuustere voorspellingen.
                </span>
              </label>
              <label>
                Risico-profiel voor suggesties
                <select
                  data-testid="instellingen-forecast-risk-profile"
                  value={forecastMarketForm.suggestions_risk_profile}
                  onChange={(e) =>
                    setForecastMarketForm((p) => ({
                      ...p,
                      suggestions_risk_profile: e.target.value,
                    }))
                  }
                >
                  <option value="Voorzichtig">Voorzichtig</option>
                  <option value="Gebalanceerd">Gebalanceerd</option>
                  <option value="Groei">Groei</option>
                </select>
                <span className="help-text">
                  Profiel dat de suggestie-engine toepast. Voorzichtig =
                  meer cash, strikter; Groei = meer aandelen, ruimer.
                </span>
              </label>
              <label>
                Universum-set
                <select
                  data-testid="instellingen-forecast-universe-set"
                  value={forecastMarketForm.universe_set}
                  onChange={(e) =>
                    setForecastMarketForm((p) => ({
                      ...p,
                      universe_set: e.target.value,
                    }))
                  }
                >
                  <option value="SP500">SP500 (~500 namen)</option>
                  <option value="EU600">EU600 (~600 namen)</option>
                  <option value="ALL_5K">ALL_5K (volledige scope)</option>
                </select>
                <span className="help-text">
                  De vaste universum-set die het systeem scant. Wordt
                  overschreven door de per-beurs multi-selectie hierboven
                  als die niet leeg is.
                </span>
              </label>
              <label>
                Marktdata-provider
                <select
                  data-testid="instellingen-forecast-md-provider"
                  value={forecastMarketForm.market_data_provider}
                  onChange={(e) =>
                    setForecastMarketForm((p) => ({
                      ...p,
                      market_data_provider: e.target.value,
                    }))
                  }
                >
                  <option value="none">Geen (gebruik snapshots)</option>
                  <option value="eodhd">EODHD</option>
                  <option value="ibkr">IBKR</option>
                </select>
                <span className="help-text">
                  Bron voor end-of-day prijzen. Geen = alleen
                  laatst-opgeslagen snapshots; EODHD = dagelijkse pull
                  via API (vereist EODHD-key); IBKR = live via TWS.
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-forecast-md-sync"
                  checked={forecastMarketForm.market_data_sync_enabled}
                  onChange={(e) =>
                    setForecastMarketForm((p) => ({
                      ...p,
                      market_data_sync_enabled: e.target.checked,
                    }))
                  }
                />{" "}
                Marktdata-sync inschakelen
                <span className="help-text">
                  Uit (standaard) = geen automatische prijs-pull. Aan =
                  het systeem haalt periodiek nieuwe prijzen op via de
                  geselecteerde provider.
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-forecast-ibkr-md-enabled"
                  checked={forecastMarketForm.ibkr_market_data_enabled}
                  onChange={(e) =>
                    setForecastMarketForm((p) => ({
                      ...p,
                      ibkr_market_data_enabled: e.target.checked,
                    }))
                  }
                />{" "}
                IBKR live marktdata inschakelen
                <span className="help-text">
                  Uit (standaard) = alleen end-of-day data. Aan =
                  realtime/delayed quotes via TWS-marktdata-sessie. Let
                  op: verbruikt IBKR-marktdata-quotum.
                </span>
              </label>
              <label>
                IBKR marktdata-type
                <select
                  data-testid="instellingen-forecast-ibkr-md-type"
                  value={forecastMarketForm.ibkr_market_data_type}
                  onChange={(e) =>
                    setForecastMarketForm((p) => ({
                      ...p,
                      ibkr_market_data_type: e.target.value,
                    }))
                  }
                >
                  <option value="delayed">delayed (15min vertraagd)</option>
                  <option value="realtime">realtime (live)</option>
                  <option value="delayed_frozen">delayed_frozen</option>
                  <option value="frozen">frozen</option>
                </select>
                <span className="help-text">
                  Welk soort marktdata IBKR moet leveren. Delayed is
                  gratis; realtime kost een abonnement. Frozen-varianten
                  bevriezen de laatste prijs buiten beurstijd.
                </span>
              </label>
            </div>
            <div
              style={{
                marginTop: 12,
                display: "flex",
                gap: 12,
                alignItems: "center",
              }}
            >
              <button
                type="button"
                onClick={() => void handleSaveForecastMarket()}
                disabled={forecastMarketSaving}
                data-testid="instellingen-forecast-market-save"
                style={{
                  background: "#1f2937",
                  color: "#ffffff",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: 4,
                  cursor: forecastMarketSaving ? "not-allowed" : "pointer",
                  fontSize: 14,
                }}
              >
                {forecastMarketSaving
                  ? "Opslaan…"
                  : "Voorspelling & marktdata opslaan"}
              </button>
              {forecastMarketSaved ? (
                <span style={{ color: "#15803d", fontSize: 13 }}>
                  {forecastMarketSaved}
                </span>
              ) : null}
              {forecastMarketError ? (
                <span
                  data-testid="instellingen-forecast-market-error"
                  style={{ color: "#b91c1c", fontSize: 13 }}
                >
                  {forecastMarketError}
                </span>
              ) : null}
            </div>
          </section>

          {/* Section 4j — Markt-events (PR J). Market-aware scheduler. */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-market-events-section"
          >
            <h2 style={{ margin: 0 }}>Markt-events</h2>
            <p style={{ marginTop: 4, color: "#374151", fontSize: 13 }}>
              {marketEventsHelp
                || "Markt-bewuste scheduler: vuurt alleen wanneer een markt die je volgt opent of sluit, in plaats van elk uur."}
            </p>
            <div className="grid one-column" style={{ marginTop: 10 }}>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-market-events-close-enabled"
                  checked={marketEventsForm.per_market_close_digest_enabled}
                  onChange={(e) =>
                    setMarketEventsForm((p) => ({
                      ...p,
                      per_market_close_digest_enabled: e.target.checked,
                    }))
                  }
                />{" "}
                Close-digest per gevolgde markt inschakelen
                <span className="help-text">
                  Aan (standaard) = na sluiting van elke gevolgde markt
                  vuurt een fire (~15 min na slot) die marktdata
                  ververst en een einde-dag samenvatting voorbereidt.
                  Uit = geen close-fire (slechts de 07:00 ochtend-chain
                  draait).
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-market-events-open-enabled"
                  checked={marketEventsForm.per_market_open_alerts_enabled}
                  onChange={(e) =>
                    setMarketEventsForm((p) => ({
                      ...p,
                      per_market_open_alerts_enabled: e.target.checked,
                    }))
                  }
                />{" "}
                Open-check per gevolgde markt inschakelen (optioneel)
                <span className="help-text">
                  Uit (standaard) = geen open-fire. Aan = kort na opening
                  (~5 min) vuurt een fire die IBKR-posities ververst en
                  eventuele overnachte gaps signaleert. Vereist een
                  actieve IBKR-sync.
                </span>
              </label>
            </div>

            {marketEventsActiveSessions.length > 0 ? (
              <div
                data-testid="instellingen-market-events-active-sessions"
                style={{
                  marginTop: 12,
                  padding: 10,
                  background: "#f9fafb",
                  borderRadius: 4,
                }}
              >
                <strong style={{ fontSize: 13 }}>
                  Actieve markten op basis van je universe-selectie:
                </strong>
                <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
                  {marketEventsActiveSessions.map((session) => (
                    <li
                      key={session}
                      style={{ fontSize: 13, color: "#374151" }}
                    >
                      {session}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div
                data-testid="instellingen-market-events-no-sessions"
                style={{
                  marginTop: 12,
                  padding: 10,
                  background: "#fef3c7",
                  borderRadius: 4,
                  fontSize: 13,
                  color: "#92400e",
                }}
              >
                Geen markten geselecteerd. Kies markten in de
                Universe-scan sectie hierboven om markt-events te
                activeren.
              </div>
            )}

            {marketEventsFires.length > 0 ? (
              <div
                data-testid="instellingen-market-events-fires-list"
                style={{ marginTop: 12 }}
              >
                <strong style={{ fontSize: 13 }}>
                  Geplande fires (weekdagen):
                </strong>
                <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
                  {marketEventsFires.map((fire) => (
                    <li
                      key={`${fire.market_code}-${fire.event_kind}`}
                      style={{ fontSize: 13, color: "#374151" }}
                    >
                      {fire.market_label_nl} —{" "}
                      {fire.event_kind === "close" ? "sluiting" : "opening"}{" "}
                      om{" "}
                      <strong>
                        {String(fire.fire_hour).padStart(2, "0")}:
                        {String(fire.fire_minute).padStart(2, "0")}
                      </strong>{" "}
                      <code style={{ fontSize: 11, color: "#6b7280" }}>
                        ({fire.timezone})
                      </code>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div
              style={{
                marginTop: 12,
                display: "flex",
                gap: 12,
                alignItems: "center",
              }}
            >
              <button
                type="button"
                onClick={() => void handleSaveMarketEvents()}
                disabled={marketEventsSaving}
                data-testid="instellingen-market-events-save"
                style={{
                  background: "#1f2937",
                  color: "#ffffff",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: 4,
                  cursor: marketEventsSaving ? "not-allowed" : "pointer",
                  fontSize: 14,
                }}
              >
                {marketEventsSaving ? "Opslaan…" : "Markt-events opslaan"}
              </button>
              {marketEventsSaved ? (
                <span style={{ color: "#15803d", fontSize: 13 }}>
                  {marketEventsSaved}
                </span>
              ) : null}
              {marketEventsError ? (
                <span
                  data-testid="instellingen-market-events-error"
                  style={{ color: "#b91c1c", fontSize: 13 }}
                >
                  {marketEventsError}
                </span>
              ) : null}
            </div>
          </section>

          {/* Section 4k — Notificaties (PR K). Email transport + prefs. */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-notifications-section"
          >
            <h2 style={{ margin: 0 }}>Notificaties</h2>
            <p style={{ marginTop: 4, color: "#374151", fontSize: 13 }}>
              {notificationsHelp
                || "Stel SMTP in zodat je e-mail ontvangt wanneer iets belangrijks gebeurt. Test eerst met de knop hieronder voordat je voor productie aanzet."}
            </p>
            {!notificationsRealClientEnabled ? (
              <div
                data-testid="instellingen-notifications-stub-banner"
                style={{
                  marginTop: 10,
                  padding: 10,
                  background: "#fef3c7",
                  borderRadius: 4,
                  fontSize: 13,
                  color: "#92400e",
                }}
              >
                Stub-modus actief: e-mails worden voorbereid maar niet
                verzonden. Zet de env-var
                <code> NOTIFICATIONS_EMAIL_REAL_CLIENT_ENABLED=true </code>
                aan om SMTP daadwerkelijk te gebruiken.
              </div>
            ) : null}

            <div className="grid one-column" style={{ marginTop: 10 }}>
              <label>
                SMTP-host
                <input
                  type="text"
                  data-testid="instellingen-notifications-smtp-host"
                  value={notificationsForm.smtp_host ?? ""}
                  placeholder="smtp.gmail.com"
                  onChange={(e) =>
                    setNotificationsForm((p) => ({
                      ...p,
                      smtp_host: e.target.value || null,
                    }))
                  }
                />
                <span className="help-text">
                  Het adres van je SMTP-server. Voor Gmail:
                  <code> smtp.gmail.com</code>. Voor andere providers:
                  zie hun documentatie.
                </span>
              </label>
              <label>
                SMTP-poort
                <input
                  type="number"
                  min="1"
                  max="65535"
                  data-testid="instellingen-notifications-smtp-port"
                  value={notificationsForm.smtp_port}
                  onChange={(e) =>
                    setNotificationsForm((p) => ({
                      ...p,
                      smtp_port: Number(e.target.value),
                    }))
                  }
                />
                <span className="help-text">
                  Standaard 587 (STARTTLS). Gebruik 465 voor implicit
                  SSL of 25 voor onbeveiligde lokale relays.
                </span>
              </label>
              <label>
                SMTP-gebruikersnaam
                <input
                  type="text"
                  data-testid="instellingen-notifications-smtp-username"
                  value={notificationsForm.smtp_username ?? ""}
                  onChange={(e) =>
                    setNotificationsForm((p) => ({
                      ...p,
                      smtp_username: e.target.value || null,
                    }))
                  }
                />
                <span className="help-text">
                  Meestal je e-mailadres. Leeg laten voor relays die geen
                  authenticatie vereisen.
                </span>
              </label>
              <label>
                SMTP-password
                <input
                  type="password"
                  data-testid="instellingen-notifications-smtp-password"
                  value={notificationsForm.smtp_password ?? ""}
                  placeholder={
                    notificationsPasswordSet
                      ? "(opgeslagen — leeglaten om bestaande te behouden)"
                      : ""
                  }
                  onChange={(e) =>
                    setNotificationsForm((p) => ({
                      ...p,
                      smtp_password: e.target.value,
                    }))
                  }
                />
                <span className="help-text">
                  Bij Gmail: gebruik een app-specifiek password, niet je
                  account-password. Wordt versleuteld opgeslagen en nooit
                  teruggegeven via de API.
                </span>
              </label>
              <label>
                Afzender-adres (From)
                <input
                  type="email"
                  data-testid="instellingen-notifications-smtp-from"
                  value={notificationsForm.smtp_from ?? ""}
                  placeholder="trading-bot@example.com"
                  onChange={(e) =>
                    setNotificationsForm((p) => ({
                      ...p,
                      smtp_from: e.target.value || null,
                    }))
                  }
                />
                <span className="help-text">
                  Het e-mailadres dat als afzender getoond wordt. Bij
                  Gmail moet dit hetzelfde zijn als je gebruikersnaam.
                </span>
              </label>
              <label>
                Ontvanger-adres (To)
                <input
                  type="email"
                  data-testid="instellingen-notifications-smtp-to"
                  value={notificationsForm.smtp_to ?? ""}
                  placeholder="jij@example.com"
                  onChange={(e) =>
                    setNotificationsForm((p) => ({
                      ...p,
                      smtp_to: e.target.value || null,
                    }))
                  }
                />
                <span className="help-text">
                  Het e-mailadres waar de notificaties heen gestuurd
                  worden. Meestal je eigen adres.
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-notifications-smtp-use-tls"
                  checked={notificationsForm.smtp_use_tls}
                  onChange={(e) =>
                    setNotificationsForm((p) => ({
                      ...p,
                      smtp_use_tls: e.target.checked,
                    }))
                  }
                />{" "}
                TLS gebruiken (aanbevolen)
                <span className="help-text">
                  Aan (standaard) = de verbinding wordt versleuteld via
                  STARTTLS (port 587) of SSL (port 465). Alleen
                  uitschakelen voor lokale relays die geen TLS
                  ondersteunen.
                </span>
              </label>

              <h3 style={{ marginTop: 12, marginBottom: 4 }}>
                Welke notificaties wil je ontvangen?
              </h3>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-notifications-master-enabled"
                  checked={notificationsForm.notifications_email_enabled}
                  onChange={(e) =>
                    setNotificationsForm((p) => ({
                      ...p,
                      notifications_email_enabled: e.target.checked,
                    }))
                  }
                />{" "}
                E-mail notificaties inschakelen (master switch)
                <span className="help-text">
                  Master switch. Uit (standaard) = nooit een e-mail, ook
                  niet bij ingestelde triggers. Aan = de drie toggles
                  hieronder bepalen wat verstuurd wordt.
                </span>
              </label>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-notifications-trigger-nav-drop"
                  checked={notificationsForm.notification_send_on_nav_drop}
                  onChange={(e) =>
                    setNotificationsForm((p) => ({
                      ...p,
                      notification_send_on_nav_drop: e.target.checked,
                    }))
                  }
                />{" "}
                E-mail bij portfolio-NAV daling ≥ 2%
              </label>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-notifications-trigger-position-drop"
                  checked={
                    notificationsForm.notification_send_on_position_drop
                  }
                  onChange={(e) =>
                    setNotificationsForm((p) => ({
                      ...p,
                      notification_send_on_position_drop: e.target.checked,
                    }))
                  }
                />{" "}
                E-mail bij positie daling ≥ 5%
              </label>
              <label>
                <input
                  type="checkbox"
                  data-testid="instellingen-notifications-trigger-high-conf-sell"
                  checked={
                    notificationsForm.notification_send_on_high_confidence_sell
                  }
                  onChange={(e) =>
                    setNotificationsForm((p) => ({
                      ...p,
                      notification_send_on_high_confidence_sell:
                        e.target.checked,
                    }))
                  }
                />{" "}
                E-mail bij hoge-zekerheid verkoop-suggestie
              </label>
            </div>

            <div
              style={{
                marginTop: 12,
                display: "flex",
                gap: 12,
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <button
                type="button"
                onClick={() => void handleSaveNotifications()}
                disabled={notificationsSaving}
                data-testid="instellingen-notifications-save"
                style={{
                  background: "#1f2937",
                  color: "#ffffff",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: 4,
                  cursor: notificationsSaving ? "not-allowed" : "pointer",
                  fontSize: 14,
                }}
              >
                {notificationsSaving ? "Opslaan…" : "Notificaties opslaan"}
              </button>
              <button
                type="button"
                onClick={() => void handleSendTestEmail()}
                disabled={notificationsTestSending}
                data-testid="instellingen-notifications-test-email"
                style={{
                  background: "#ffffff",
                  color: "#1f2937",
                  border: "1px solid #1f2937",
                  padding: "6px 14px",
                  borderRadius: 4,
                  cursor: notificationsTestSending ? "not-allowed" : "pointer",
                  fontSize: 14,
                }}
              >
                {notificationsTestSending ? "Versturen…" : "Test e-mail"}
              </button>
              {notificationsSaved ? (
                <span style={{ color: "#15803d", fontSize: 13 }}>
                  {notificationsSaved}
                </span>
              ) : null}
              {notificationsError ? (
                <span
                  data-testid="instellingen-notifications-error"
                  style={{ color: "#b91c1c", fontSize: 13 }}
                >
                  {notificationsError}
                </span>
              ) : null}
            </div>

            {notificationsTestResult ? (
              <div
                data-testid="instellingen-notifications-test-result"
                style={{
                  marginTop: 10,
                  padding: 10,
                  borderRadius: 4,
                  fontSize: 13,
                  background: notificationsTestResult.sent
                    ? "#dcfce7"
                    : notificationsTestResult.status === "stubbed"
                      ? "#fef3c7"
                      : "#fee2e2",
                  color: notificationsTestResult.sent
                    ? "#15803d"
                    : notificationsTestResult.status === "stubbed"
                      ? "#92400e"
                      : "#991b1b",
                }}
              >
                <strong>
                  {notificationsTestResult.sent
                    ? "✓ Verstuurd"
                    : notificationsTestResult.status === "stubbed"
                      ? "Stub-modus"
                      : "Niet verstuurd"}
                  :
                </strong>{" "}
                {notificationsTestResult.detail_nl}
              </div>
            ) : null}
          </section>

          {/* Section 4g — Geavanceerde instellingen (PR E). Collapsed by
              default; meant for power-users only. */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-advanced-section"
          >
            <button
              type="button"
              onClick={() => setAdvancedOpen((v) => !v)}
              data-testid="instellingen-advanced-toggle"
              aria-expanded={advancedOpen}
              style={{
                background: "transparent",
                border: "none",
                padding: 0,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 18,
                fontWeight: 600,
                color: "#111827",
              }}
            >
              <span aria-hidden="true">{advancedOpen ? "▼" : "▶"}</span>
              Geavanceerde instellingen
            </button>
            <p style={{ marginTop: 4, color: "#374151", fontSize: 13 }}>
              {advancedHelp
                || "Power-user knoppen achter een accordion. Pas alleen aan als je weet wat je doet — verkeerde waarden kunnen voorspellingen of order-uitleg uit balans brengen."}
            </p>
            {advancedOpen ? (
              <>
                <div className="grid one-column" style={{ marginTop: 10 }}>
                  <label>
                    Ensemble-strategie
                    <select
                      data-testid="instellingen-advanced-ensemble"
                      value={advancedForm.ensemble_weight_strategy}
                      onChange={(e) =>
                        setAdvancedForm((p) => ({
                          ...p,
                          ensemble_weight_strategy: e.target.value,
                        }))
                      }
                    >
                      <option value="equal_weight">
                        Equal weight (standaard)
                      </option>
                      <option value="auto">
                        Auto (per-predictor calibratie)
                      </option>
                    </select>
                    <span className="help-text">
                      Hoe het systeem voorspellingen van verschillende
                      modellen combineert. Equal weight = elke predictor
                      telt even zwaar. Auto = gewicht op basis van recente
                      calibratie.
                    </span>
                  </label>
                  <label>
                    GBM drift-venster (dagen)
                    <input
                      type="number"
                      step="1"
                      min="1"
                      data-testid="instellingen-advanced-gbm-window"
                      value={
                        advancedForm.gbm_drift_window_days == null
                          ? ""
                          : advancedForm.gbm_drift_window_days
                      }
                      onChange={(e) =>
                        setAdvancedForm((p) => ({
                          ...p,
                          gbm_drift_window_days:
                            e.target.value === ""
                              ? null
                              : Number(e.target.value),
                        }))
                      }
                    />
                    <span className="help-text">
                      Hoeveel dagen historie het GBM-model gebruikt om
                      drift (verwacht rendement) te schatten. Leeg laten
                      = volledige lookback. Hoger = stabieler, lager =
                      reactiever.
                    </span>
                  </label>
                  <label>
                    Goedkeuringsvenster Action Draft (minuten)
                    <input
                      type="number"
                      step="1"
                      min="1"
                      data-testid="instellingen-advanced-approval-minutes"
                      value={advancedForm.action_draft_approval_valid_minutes}
                      onChange={(e) =>
                        setAdvancedForm((p) => ({
                          ...p,
                          action_draft_approval_valid_minutes: Number(
                            e.target.value,
                          ),
                        }))
                      }
                    />
                    <span className="help-text">
                      Hoe lang een goedgekeurde Action Draft geldig blijft
                      voor IBKR-submit. Standaard 5 minuten. Hoger = meer
                      tijd om te reviewen, lager = strakker tegen slippage.
                    </span>
                  </label>
                  <label>
                    AI-uitleg provider
                    <select
                      data-testid="instellingen-advanced-ai-provider"
                      value={advancedForm.ai_explanation_provider_code}
                      onChange={(e) =>
                        setAdvancedForm((p) => ({
                          ...p,
                          ai_explanation_provider_code: e.target.value,
                        }))
                      }
                    >
                      <option value="stub">Stub (gratis, deterministisch)</option>
                      <option value="claude">
                        Claude (betaald, natuurlijke taal)
                      </option>
                    </select>
                    <span className="help-text">
                      Welke provider de Nederlandse uitleg-tekst onder
                      elke suggestie genereert. Stub kost niets, Claude
                      gebruikt je maandbudget.
                    </span>
                  </label>
                  <label>
                    Sharpe-drempel &ldquo;sterke beweging&rdquo;
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      data-testid="instellingen-advanced-sharpe-strong"
                      value={advancedForm.sharpe_strong_threshold}
                      onChange={(e) =>
                        setAdvancedForm((p) => ({
                          ...p,
                          sharpe_strong_threshold: e.target.value,
                        }))
                      }
                    />
                    <span className="help-text">
                      Boven welke risico-gecorrigeerde score (Sharpe) een
                      voorspelling als &ldquo;sterke stijging/daling&rdquo; wordt
                      gelabeld. Standaard 1.0 ≈ ~84% kans op de
                      voorspelde richting. Hoger = strikter, lager =
                      sneller &ldquo;sterk&rdquo; stempel.
                    </span>
                  </label>
                  <label>
                    Sharpe-drempel &ldquo;lichte beweging&rdquo;
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      data-testid="instellingen-advanced-sharpe-slight"
                      value={advancedForm.sharpe_slight_threshold}
                      onChange={(e) =>
                        setAdvancedForm((p) => ({
                          ...p,
                          sharpe_slight_threshold: e.target.value,
                        }))
                      }
                    />
                    <span className="help-text">
                      Onderste drempel voor &ldquo;lichte stijging/daling&rdquo;.
                      Standaard 0.3 ≈ ~62% kans. Tussen deze waarde en
                      0 valt het label terug op &ldquo;Geen duidelijke
                      richting&rdquo;. Moet lager zijn dan de sterke drempel.
                    </span>
                  </label>
                </div>
                <div
                  style={{
                    marginTop: 12,
                    display: "flex",
                    gap: 12,
                    alignItems: "center",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => void handleSaveAdvanced()}
                    disabled={advancedSaving}
                    data-testid="instellingen-advanced-save"
                    style={{
                      background: "#1f2937",
                      color: "#ffffff",
                      border: "none",
                      padding: "6px 14px",
                      borderRadius: 4,
                      cursor: advancedSaving ? "not-allowed" : "pointer",
                      fontSize: 14,
                    }}
                  >
                    {advancedSaving ? "Opslaan…" : "Geavanceerd opslaan"}
                  </button>
                  {advancedSaved ? (
                    <span style={{ color: "#15803d", fontSize: 13 }}>
                      {advancedSaved}
                    </span>
                  ) : null}
                  {advancedError ? (
                    <span
                      data-testid="instellingen-advanced-error"
                      style={{ color: "#b91c1c", fontSize: 13 }}
                    >
                      {advancedError}
                    </span>
                  ) : null}
                </div>
              </>
            ) : null}
          </section>

          {/* Section 4j — Voorspeller-tuning (PR I). Collapsed accordion
              for power-user predictor tuning. */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-predictor-tuning-section"
          >
            <button
              type="button"
              onClick={() => setPredictorTuningOpen((v) => !v)}
              data-testid="instellingen-predictor-tuning-toggle"
              aria-expanded={predictorTuningOpen}
              style={{
                background: "transparent",
                border: "none",
                padding: 0,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 18,
                fontWeight: 600,
                color: "#111827",
              }}
            >
              <span aria-hidden="true">{predictorTuningOpen ? "▼" : "▶"}</span>
              Voorspeller-tuning
            </button>
            <p style={{ marginTop: 4, color: "#374151", fontSize: 13 }}>
              {predictorTuningHelp
                || "Power-user voorspeller-tuning. Beheert TTLs, dagboek-tolerantie en GBM regime-shift drift-blending."}
            </p>
            {predictorTuningOpen ? (
              <>
                <div className="grid one-column" style={{ marginTop: 10 }}>
                  <label>
                    Voorspelling-TTL (minuten)
                    <input
                      type="number"
                      step="1"
                      min="1"
                      data-testid="instellingen-predictor-forecast-ttl"
                      value={predictorTuningForm.forecast_valid_minutes}
                      onChange={(e) =>
                        setPredictorTuningForm((p) => ({
                          ...p,
                          forecast_valid_minutes: Number(e.target.value),
                        }))
                      }
                    />
                    <span className="help-text">
                      Hoe lang een opgeslagen voorspelling geldig blijft
                      voordat de morgen-chain hem opnieuw moet
                      berekenen. Standaard 1440 (24u). Korter = vaker
                      recompute, hoger = minder EODHD-calls.
                    </span>
                  </label>
                  <label>
                    Beslissings-pakket-TTL (minuten)
                    <input
                      type="number"
                      step="1"
                      min="1"
                      data-testid="instellingen-predictor-dp-ttl"
                      value={
                        predictorTuningForm.decision_packages_valid_minutes
                      }
                      onChange={(e) =>
                        setPredictorTuningForm((p) => ({
                          ...p,
                          decision_packages_valid_minutes: Number(
                            e.target.value,
                          ),
                        }))
                      }
                    />
                    <span className="help-text">
                      Hoe lang een Decision Package geldig blijft. Komt
                      typisch overeen met de voorspelling-TTL hierboven.
                    </span>
                  </label>
                  <label>
                    Dagboek &ldquo;onbeslist&rdquo;-tolerantie (%)
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      data-testid="instellingen-predictor-diary-tolerance"
                      value={
                        predictorTuningForm.prediction_diary_inconclusive_tolerance_pct
                      }
                      onChange={(e) =>
                        setPredictorTuningForm((p) => ({
                          ...p,
                          prediction_diary_inconclusive_tolerance_pct:
                            e.target.value,
                        }))
                      }
                    />
                    <span className="help-text">
                      Tussen ±deze waarde wordt een voorspellings-
                      uitkomst als &ldquo;onbeslist&rdquo; geclassificeerd in
                      het prediction-diary. Standaard 0.25%. Strakker =
                      meer harde verdicts, ruimer = meer onbeslist.
                    </span>
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      data-testid="instellingen-predictor-regime-enabled"
                      checked={
                        predictorTuningForm.gbm_regime_shift_enabled
                      }
                      onChange={(e) =>
                        setPredictorTuningForm((p) => ({
                          ...p,
                          gbm_regime_shift_enabled: e.target.checked,
                        }))
                      }
                    />{" "}
                    GBM regime-shift drift-blending inschakelen
                    <span className="help-text">
                      Uit (standaard) = drift = volle-historie gemiddelde.
                      Aan = de drift blendt korte- en lange-window
                      gemiddeldes als ze meer dan de drempel hieronder
                      afwijken, zodat een regime-verschuiving sneller
                      doorwerkt.
                    </span>
                  </label>
                  <label>
                    Regime-shift drempel (%)
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      data-testid="instellingen-predictor-regime-threshold"
                      value={
                        predictorTuningForm.gbm_regime_shift_threshold_pct
                      }
                      onChange={(e) =>
                        setPredictorTuningForm((p) => ({
                          ...p,
                          gbm_regime_shift_threshold_pct: e.target.value,
                        }))
                      }
                    />
                    <span className="help-text">
                      Onder welke procentuele afwijking tussen korte- en
                      lange-window drift de blend niet ingrijpt.
                      Standaard 5.0. Alleen actief als de toggle
                      hierboven aan staat.
                    </span>
                  </label>
                </div>
                <div
                  style={{
                    marginTop: 12,
                    display: "flex",
                    gap: 12,
                    alignItems: "center",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => void handleSavePredictorTuning()}
                    disabled={predictorTuningSaving}
                    data-testid="instellingen-predictor-tuning-save"
                    style={{
                      background: "#1f2937",
                      color: "#ffffff",
                      border: "none",
                      padding: "6px 14px",
                      borderRadius: 4,
                      cursor: predictorTuningSaving
                        ? "not-allowed"
                        : "pointer",
                      fontSize: 14,
                    }}
                  >
                    {predictorTuningSaving
                      ? "Opslaan…"
                      : "Voorspeller-tuning opslaan"}
                  </button>
                  {predictorTuningSaved ? (
                    <span style={{ color: "#15803d", fontSize: 13 }}>
                      {predictorTuningSaved}
                    </span>
                  ) : null}
                  {predictorTuningError ? (
                    <span
                      data-testid="instellingen-predictor-tuning-error"
                      style={{ color: "#b91c1c", fontSize: 13 }}
                    >
                      {predictorTuningError}
                    </span>
                  ) : null}
                </div>
              </>
            ) : null}
          </section>

          {/* Section 4 — Connection + AI (editable). */}
          <section
            style={SECTION_STYLE}
            data-testid="instellingen-connection-section"
          >
            <h3 style={{ marginTop: 0 }}>Verbinding &amp; AI</h3>
            <p style={HELP_STYLE}>
              De IBKR-verbinding en de Claude AI-uitleginstellingen. Wijzigingen
              worden bewaard in de database en bij het opstarten van de API
              toegepast.
            </p>

            <label
              style={{ ...LABEL_STYLE, display: "flex", alignItems: "center", gap: 8 }}
              htmlFor="connection-ibkr_enabled"
            >
              <input
                id="connection-ibkr_enabled"
                data-testid="instellingen-connection-ibkr_enabled"
                type="checkbox"
                checked={connection.ibkr_enabled}
                onChange={(event) =>
                  setConnectionField("ibkr_enabled", event.target.checked)
                }
              />
              <FieldLabel
                label_nl="IBKR-verbinding ingeschakeld"
                help_nl="Zet de verbinding met Interactive Brokers aan of uit."
              />
            </label>

            <label style={LABEL_STYLE} htmlFor="connection-ibkr_account_id">
              <FieldLabel
                label_nl="IBKR-rekening"
                help_nl="De account-id (bv. DU1234567 voor paper, U1234567 voor live)."
              />
              <input
                id="connection-ibkr_account_id"
                data-testid="instellingen-connection-ibkr_account_id"
                type="text"
                value={connection.ibkr_account_id}
                onChange={(event) =>
                  setConnectionField("ibkr_account_id", event.target.value)
                }
              />
              {connection.ibkr_account_id.trim() ? (
                <AccountIdModePreview
                  accountId={connection.ibkr_account_id}
                />
              ) : null}
            </label>

            <label style={LABEL_STYLE} htmlFor="connection-ibkr_host">
              <FieldLabel
                label_nl="IBKR-host"
                help_nl="Het adres van de TWS/Gateway (standaard 127.0.0.1)."
              />
              <input
                id="connection-ibkr_host"
                data-testid="instellingen-connection-ibkr_host"
                type="text"
                value={connection.ibkr_host}
                onChange={(event) =>
                  setConnectionField("ibkr_host", event.target.value)
                }
              />
            </label>

            <label style={LABEL_STYLE} htmlFor="connection-ibkr_port">
              <FieldLabel
                label_nl="IBKR-poort"
                help_nl="De poort van de TWS/Gateway (paper 7497, live 7496)."
              />
              <input
                id="connection-ibkr_port"
                data-testid="instellingen-connection-ibkr_port"
                type="number"
                step="1"
                value={connection.ibkr_port}
                onChange={(event) =>
                  setConnectionField("ibkr_port", event.target.value)
                }
              />
            </label>

            <label style={LABEL_STYLE} htmlFor="connection-ibkr_client_id">
              <FieldLabel
                label_nl="IBKR-client-id"
                help_nl="Het client-id van de API-sessie (standaard 1)."
              />
              <input
                id="connection-ibkr_client_id"
                data-testid="instellingen-connection-ibkr_client_id"
                type="number"
                step="1"
                value={connection.ibkr_client_id}
                onChange={(event) =>
                  setConnectionField("ibkr_client_id", event.target.value)
                }
              />
            </label>

            <label
              style={{ ...LABEL_STYLE, display: "flex", alignItems: "center", gap: 8 }}
              htmlFor="connection-ai_explanation_enabled"
            >
              <input
                id="connection-ai_explanation_enabled"
                data-testid="instellingen-connection-ai_explanation_enabled"
                type="checkbox"
                checked={connection.ai_explanation_enabled}
                onChange={(event) =>
                  setConnectionField(
                    "ai_explanation_enabled",
                    event.target.checked,
                  )
                }
              />
              <FieldLabel
                label_nl="AI-uitleg ingeschakeld"
                help_nl="Laat Claude een Nederlandstalige uitleg bij beslissingen genereren."
              />
            </label>

            <label
              style={{ ...LABEL_STYLE, display: "flex", alignItems: "center", gap: 8 }}
              htmlFor="connection-ai_explanation_morning_batch_enabled"
            >
              <input
                id="connection-ai_explanation_morning_batch_enabled"
                data-testid="instellingen-connection-ai_explanation_morning_batch_enabled"
                type="checkbox"
                checked={connection.ai_explanation_morning_batch_enabled}
                onChange={(event) =>
                  setConnectionField(
                    "ai_explanation_morning_batch_enabled",
                    event.target.checked,
                  )
                }
              />
              <FieldLabel
                label_nl="Voor-bereken Claude-uitleg per ochtend"
                help_nl="Genereert vroeg ochtends voor elke aangehouden positie alvast de Claude-paraphrase, zodat de dashboard om 07:00 al de uitleg toont."
              />
            </label>

            <label
              style={{ ...LABEL_STYLE, display: "flex", alignItems: "center", gap: 8 }}
              htmlFor="connection-ai_email_summary_enabled"
            >
              <input
                id="connection-ai_email_summary_enabled"
                data-testid="instellingen-connection-ai_email_summary_enabled"
                type="checkbox"
                checked={connection.ai_email_summary_enabled}
                onChange={(event) =>
                  setConnectionField(
                    "ai_email_summary_enabled",
                    event.target.checked,
                  )
                }
              />
              <FieldLabel
                label_nl="AI-samenvatting bovenaan e-mails"
                help_nl="Voegt een korte Nederlandstalige Claude-samenvatting toe boven de digest- en ochtend-alert-mails. De deterministische template blijft altijd zichtbaar; bij mislukken valt de mail terug zonder header."
              />
            </label>

            <label
              style={{ ...LABEL_STYLE, display: "flex", alignItems: "center", gap: 8 }}
              htmlFor="connection-research_ai_extraction_enabled"
            >
              <input
                id="connection-research_ai_extraction_enabled"
                data-testid="instellingen-connection-research_ai_extraction_enabled"
                type="checkbox"
                checked={connection.research_ai_extraction_enabled}
                onChange={(event) =>
                  setConnectionField(
                    "research_ai_extraction_enabled",
                    event.target.checked,
                  )
                }
              />
              <FieldLabel
                label_nl="AI-extractie van onderzoeksbronnen"
                help_nl="Laat Claude korte feiten / citaten uit geüploade onderzoeksbronnen halen. Substring-bewaking blokkeert gehallucineerde feiten. Resultaten zijn alleen leeshulp — nooit veilig voor suggesties of orders."
              />
            </label>

            <label
              style={LABEL_STYLE}
              htmlFor="connection-claude_ai_explanation_model"
            >
              <FieldLabel
                label_nl="Claude AI-model"
                help_nl="Het model dat voor de AI-uitleg wordt gebruikt."
              />
              <input
                id="connection-claude_ai_explanation_model"
                data-testid="instellingen-connection-claude_ai_explanation_model"
                type="text"
                value={connection.claude_ai_explanation_model}
                onChange={(event) =>
                  setConnectionField(
                    "claude_ai_explanation_model",
                    event.target.value,
                  )
                }
              />
            </label>

            <label
              style={LABEL_STYLE}
              htmlFor="connection-claude_ai_budget_monthly_eur"
            >
              <FieldLabel
                label_nl="Maandelijks AI-budget (EUR)"
                help_nl="De maximale maandelijkse uitgave aan Claude AI-oproepen."
              />
              <input
                id="connection-claude_ai_budget_monthly_eur"
                data-testid="instellingen-connection-claude_ai_budget_monthly_eur"
                type="number"
                step="0.01"
                min="0"
                value={connection.claude_ai_budget_monthly_eur}
                onChange={(event) =>
                  setConnectionField(
                    "claude_ai_budget_monthly_eur",
                    event.target.value,
                  )
                }
              />
            </label>

            <label style={LABEL_STYLE} htmlFor="connection-claude_ai_api_key">
              <FieldLabel
                label_nl="Claude API-sleutel"
                help_nl="Laat leeg om de bestaande sleutel te behouden. Wordt nooit getoond."
              />
              <input
                id="connection-claude_ai_api_key"
                data-testid="instellingen-connection-claude_ai_api_key"
                type="password"
                autoComplete="off"
                placeholder="••••••••"
                value={connectionKeyInput}
                onChange={(event) => setConnectionKeyInput(event.target.value)}
              />
              <span
                data-testid="instellingen-connection-key-state"
                style={HELP_STYLE}
              >
                {connectionKeySet ? "Sleutel is ingesteld" : "Nog geen sleutel"}
              </span>
            </label>

            <p style={{ ...HELP_STYLE, marginTop: 12 }}>
              Wijzigingen aan de IBKR-verbinding worden actief na herstart van
              de worker.
            </p>

            <SaveBar
              testId="instellingen-connection"
              saving={connectionSaving}
              savedMessage={connectionSaved}
              error={connectionError}
              onSave={() => void handleSaveConnection()}
            />
          </section>
        </>
      )}
    </main>
  );
}
