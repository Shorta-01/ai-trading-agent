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

import { useCallback, useEffect, useState } from "react";

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

export default function Page() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

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

  const loadRiskLimits = useCallback(async () => {
    const result = await apiClient.getRiskLimits();
    if (!result.ok) return false;
    applyRiskLimits(result.data);
    return true;
  }, []);

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

  const loadTrading = useCallback(async () => {
    const result = await apiClient.getTradingSettings();
    if (!result.ok) return false;
    applyTrading(result.data);
    return true;
  }, []);

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

  const loadConnection = useCallback(async () => {
    const result = await apiClient.getConnectionSettings();
    if (!result.ok) return false;
    applyConnection(result.data);
    return true;
  }, []);

  function applyConnection(data: ConnectionSettingsResponse) {
    setConnection(connectionStateFromResponse(data));
    setConnectionKeySet(data.claude_ai_api_key_set);
    // Never reflect the (masked) key back into the input — keep it blank so a
    // save without typing omits the field and preserves the stored key.
    setConnectionKeyInput("");
  }

  const refresh = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    const [riskOk, tradingOk, connectionOk] = await Promise.all([
      loadRiskLimits(),
      loadTrading(),
      loadConnection(),
    ]);
    setLoading(false);
    if (!riskOk && !tradingOk && !connectionOk) {
      setLoadError("Instellingen konden niet worden geladen.");
    }
  }, [loadRiskLimits, loadTrading, loadConnection]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

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
