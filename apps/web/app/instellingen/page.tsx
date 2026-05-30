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
import {
  apiClient,
  type ConnectionSettingsResponse,
  type RiskLimitsResponse,
  type RiskLimitsUpdateInput,
  type TradingSettingsResponse,
} from "@/lib/apiClient";
import {
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
    || advancedQuery.isPending;
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
                    Sharpe-drempel "sterke beweging"
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
                      voorspelling als "sterke stijging/daling" wordt
                      gelabeld. Standaard 1.0 ≈ ~84% kans op de
                      voorspelde richting. Hoger = strikter, lager =
                      sneller "sterk" stempel.
                    </span>
                  </label>
                  <label>
                    Sharpe-drempel "lichte beweging"
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
                      Onderste drempel voor "lichte stijging/daling".
                      Standaard 0.3 ≈ ~62% kans. Tussen deze waarde en
                      0 valt het label terug op "Geen duidelijke
                      richting". Moet lager zijn dan de sterke drempel.
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
