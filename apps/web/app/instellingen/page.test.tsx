import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  render as rtlRender,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ConnectionSettingsResponse,
  RiskLimitsResponse,
  TradingSettingsResponse,
} from "@/lib/apiClient";

// Page-under-test uses useQuery; wrap render in a fresh QueryClientProvider
// so the test runs in isolation and the cache doesn't carry across cases.
function render(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return rtlRender(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

const getRiskLimits = vi.fn();
const updateRiskLimits = vi.fn();
const getTradingSettings = vi.fn();
const updateTradingSettings = vi.fn();
const getConnectionSettings = vi.fn();
const updateConnectionSettings = vi.fn();
const getUniverseScanSettings = vi.fn();
const updateUniverseScanSettings = vi.fn();
const getOrderPolicySettings = vi.fn();
const updateOrderPolicySettings = vi.fn();
const getSchedulerSettings = vi.fn();
const updateSchedulerSettings = vi.fn();
const getDataWindowSettings = vi.fn();
const updateDataWindowSettings = vi.fn();
const getWorkerSweepSettings = vi.fn();
const updateWorkerSweepSettings = vi.fn();
const getAdvancedSettings = vi.fn();
const updateAdvancedSettings = vi.fn();
const getForecastMarketSettings = vi.fn();
const updateForecastMarketSettings = vi.fn();
const getExecutionGateSettings = vi.fn();
const updateExecutionGateSettings = vi.fn();
const getPredictorTuningSettings = vi.fn();
const updatePredictorTuningSettings = vi.fn();
const getMarketEventsSettings = vi.fn();
const updateMarketEventsSettings = vi.fn();
const getNotificationSettings = vi.fn();
const updateNotificationSettings = vi.fn();
const sendTestEmail = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getRiskLimits: (...a: unknown[]) => getRiskLimits(...a),
    updateRiskLimits: (...a: unknown[]) => updateRiskLimits(...a),
    getTradingSettings: (...a: unknown[]) => getTradingSettings(...a),
    updateTradingSettings: (...a: unknown[]) => updateTradingSettings(...a),
    getConnectionSettings: (...a: unknown[]) => getConnectionSettings(...a),
    updateConnectionSettings: (...a: unknown[]) =>
      updateConnectionSettings(...a),
    getUniverseScanSettings: (...a: unknown[]) =>
      getUniverseScanSettings(...a),
    updateUniverseScanSettings: (...a: unknown[]) =>
      updateUniverseScanSettings(...a),
    getOrderPolicySettings: (...a: unknown[]) =>
      getOrderPolicySettings(...a),
    updateOrderPolicySettings: (...a: unknown[]) =>
      updateOrderPolicySettings(...a),
    getSchedulerSettings: (...a: unknown[]) => getSchedulerSettings(...a),
    updateSchedulerSettings: (...a: unknown[]) =>
      updateSchedulerSettings(...a),
    getDataWindowSettings: (...a: unknown[]) => getDataWindowSettings(...a),
    updateDataWindowSettings: (...a: unknown[]) =>
      updateDataWindowSettings(...a),
    getWorkerSweepSettings: (...a: unknown[]) =>
      getWorkerSweepSettings(...a),
    updateWorkerSweepSettings: (...a: unknown[]) =>
      updateWorkerSweepSettings(...a),
    getAdvancedSettings: (...a: unknown[]) => getAdvancedSettings(...a),
    updateAdvancedSettings: (...a: unknown[]) =>
      updateAdvancedSettings(...a),
    getForecastMarketSettings: (...a: unknown[]) =>
      getForecastMarketSettings(...a),
    updateForecastMarketSettings: (...a: unknown[]) =>
      updateForecastMarketSettings(...a),
    getExecutionGateSettings: (...a: unknown[]) =>
      getExecutionGateSettings(...a),
    updateExecutionGateSettings: (...a: unknown[]) =>
      updateExecutionGateSettings(...a),
    getPredictorTuningSettings: (...a: unknown[]) =>
      getPredictorTuningSettings(...a),
    updatePredictorTuningSettings: (...a: unknown[]) =>
      updatePredictorTuningSettings(...a),
    getMarketEventsSettings: (...a: unknown[]) =>
      getMarketEventsSettings(...a),
    updateMarketEventsSettings: (...a: unknown[]) =>
      updateMarketEventsSettings(...a),
    getNotificationSettings: (...a: unknown[]) =>
      getNotificationSettings(...a),
    updateNotificationSettings: (...a: unknown[]) =>
      updateNotificationSettings(...a),
    sendTestEmail: (...a: unknown[]) => sendTestEmail(...a),
  },
}));

import Page from "./page";

const RISK_LIMITS: RiskLimitsResponse = {
  ibkr_account_id: "U1234567",
  daily_max_approvals: 5,
  cooldown_seconds: 60,
  anti_revenge_window_hours: 72,
  anti_revenge_loss_threshold_pct: "1.0",
  soft_drawdown_pct: "5.0",
  soft_drawdown_window_days: 5,
  hard_drawdown_pct: "10.0",
  hard_drawdown_window_days: 20,
  fomo_drift_pct: "1.5",
  last_updated_at: "2026-05-28T10:00:00+00:00",
};

const TRADING: TradingSettingsResponse = {
  title_nl: "Handelsinstellingen",
  status_nl: "ok",
  settings_source: "default",
  settings_source_nl: "standaard",
  message_nl: "ok",
  allowed_universe: {
    allow_etfs: true,
    allow_stocks: true,
    allow_bond_etfs: false,
    allow_commodity_etfs: false,
    allow_currencies_watch_only: false,
  },
  user_strategy: {
    portfolio_goal: "balanced_growth_risk",
    risk_level: "medium",
    asset_mix_preference: "etf_and_stock_mix",
    preferred_regions: ["global"],
    preferred_sectors: [],
    avoided_sectors: [],
    max_position_pct: "10",
    min_cash_reserve_pct: "5",
    currency_preference: "eur_preferred_usd_allowed",
    prefer_simple_belgian_tax_admin: true,
    user_buffer_eur: "0",
    // Unrendered field — must survive the merge on save.
    explanation_nl: "Voorkeurlaag voor ranking en fit.",
  },
  always_blocked_asset_types: ["options", "futures", "crypto"],
  help_texts: [],
  safety_summary_nl: "ok",
};

const CONNECTION: ConnectionSettingsResponse = {
  ibkr_enabled: true,
  ibkr_account_id: "DU1234567",
  ibkr_host: "127.0.0.1",
  ibkr_port: 7497,
  ibkr_client_id: 1,
  ai_explanation_enabled: false,
  claude_ai_explanation_model: "claude-haiku-4-5",
  claude_ai_budget_monthly_eur: "50.0",
  claude_ai_api_key_set: true,
  ai_explanation_morning_batch_enabled: false,
  ai_email_summary_enabled: false,
  research_ai_extraction_enabled: false,
};

function ok<T>(data: T) {
  return Promise.resolve({ ok: true as const, data });
}

const UNIVERSE_SCAN = {
  selected_codes: ["BEL20", "AEX"],
  available_codes: [
    { code: "BEL20", label_nl: "België — Bel20" },
    { code: "AEX", label_nl: "Nederland — AEX" },
    { code: "CAC40", label_nl: "Frankrijk — CAC 40" },
  ],
  help_nl: "Kies welke beurzen het systeem dagelijks moet scannen.",
};

const ORDER_POLICY = {
  default_buy_value_eur: "1000",
  default_top_up_pct: "0.25",
  default_reduce_pct: "0.25",
  max_sector_pct: "30",
  cost_dominates_ratio: "3",
  suggestion_valid_minutes: 1440,
  help_nl: "Standaard order-grootte en suggestie-filters.",
};

const SCHEDULER = {
  scheduler_daily_briefing_cron: "30 6 * * *",
  ibkr_sync_interval_minutes: 15,
  help_nl: "Wanneer de briefing klaarstaat en hoe vaak IBKR wordt gesynchroniseerd.",
};

const DATA_WINDOWS = {
  forecast_history_lookback_days: 400,
  forecast_minimum_bars_required: 60,
  daily_briefing_lookback_hours: 24,
  universe_scan_cache_ttl_hours: 24,
  help_nl: "Lookbacks en cache-vensters.",
};

const WORKER_SWEEPS = {
  sweep_interval_seconds: 60,
  sweep_retry_max_attempts: 3,
  sweep_retry_backoff_seconds: "2.0",
  sweep_alert_after_consecutive_errors: 3,
  eodhd_rate_limit_per_second: 10,
  help_nl: "Worker-zijde cadens en EODHD-rate-limit.",
};

const ADVANCED = {
  ensemble_weight_strategy: "equal_weight",
  gbm_drift_window_days: null as number | null,
  action_draft_approval_valid_minutes: 5,
  ai_explanation_provider_code: "stub",
  sharpe_strong_threshold: "1.0",
  sharpe_slight_threshold: "0.3",
  help_nl: "Geavanceerde instellingen voor power-users.",
};

const FORECAST_MARKET = {
  forecast_horizon_trading_days: 21,
  forecast_ensemble_enabled: false,
  suggestions_risk_profile: "Gebalanceerd",
  universe_set: "SP500",
  market_data_provider: "none",
  market_data_sync_enabled: false,
  ibkr_market_data_enabled: false,
  ibkr_market_data_type: "delayed",
  help_nl: "Voorspellings- en marktdata-instellingen.",
};

const EXECUTION_GATES = {
  ibkr_paper_order_submission_enabled: false,
  submission_sweep_enabled: false,
  cancel_sweep_enabled: false,
  morning_chain_after_pre_briefing: false,
  help_nl: "Veiligheids-kritische uitvoerings-poorten.",
};

const PREDICTOR_TUNING = {
  forecast_valid_minutes: 1440,
  decision_packages_valid_minutes: 1440,
  prediction_diary_inconclusive_tolerance_pct: "0.25",
  gbm_regime_shift_enabled: false,
  gbm_regime_shift_threshold_pct: "5.0",
  help_nl: "Power-user voorspeller-tuning.",
};

const NOTIFICATIONS = {
  smtp_host: null,
  smtp_port: 587,
  smtp_username: null,
  smtp_from: null,
  smtp_to: null,
  smtp_use_tls: true,
  smtp_password_set: false,
  notifications_email_enabled: false,
  notifications_email_real_client_enabled: false,
  notification_send_on_nav_drop: true,
  notification_send_on_position_drop: true,
  notification_send_on_high_confidence_sell: true,
  help_nl: "SMTP help text",
};

const MARKET_EVENTS = {
  per_market_close_digest_enabled: true,
  per_market_open_alerts_enabled: false,
  universe_codes_selected: ["BEL20", "AEX"],
  active_sessions: ["Euronext — Brussel, Amsterdam, Parijs"],
  fires: [
    {
      market_code: "EURONEXT",
      market_label_nl: "Euronext — Brussel, Amsterdam, Parijs",
      timezone: "Europe/Brussels",
      event_kind: "close" as const,
      fire_hour: 17,
      fire_minute: 45,
    },
  ],
  help_nl: "Markt-bewuste scheduler.",
};

beforeEach(() => {
  getRiskLimits.mockReset();
  updateRiskLimits.mockReset();
  getTradingSettings.mockReset();
  updateTradingSettings.mockReset();
  getConnectionSettings.mockReset();
  updateConnectionSettings.mockReset();
  getUniverseScanSettings.mockReset();
  updateUniverseScanSettings.mockReset();
  getOrderPolicySettings.mockReset();
  updateOrderPolicySettings.mockReset();
  getSchedulerSettings.mockReset();
  updateSchedulerSettings.mockReset();
  getDataWindowSettings.mockReset();
  updateDataWindowSettings.mockReset();
  getWorkerSweepSettings.mockReset();
  updateWorkerSweepSettings.mockReset();
  getAdvancedSettings.mockReset();
  updateAdvancedSettings.mockReset();
  getForecastMarketSettings.mockReset();
  updateForecastMarketSettings.mockReset();
  getExecutionGateSettings.mockReset();
  updateExecutionGateSettings.mockReset();
  getPredictorTuningSettings.mockReset();
  updatePredictorTuningSettings.mockReset();
  getMarketEventsSettings.mockReset();
  updateMarketEventsSettings.mockReset();
  getNotificationSettings.mockReset();
  updateNotificationSettings.mockReset();
  sendTestEmail.mockReset();
  getRiskLimits.mockReturnValue(ok(RISK_LIMITS));
  getTradingSettings.mockReturnValue(ok(TRADING));
  getConnectionSettings.mockReturnValue(ok(CONNECTION));
  getUniverseScanSettings.mockReturnValue(ok(UNIVERSE_SCAN));
  getOrderPolicySettings.mockReturnValue(ok(ORDER_POLICY));
  getSchedulerSettings.mockReturnValue(ok(SCHEDULER));
  getDataWindowSettings.mockReturnValue(ok(DATA_WINDOWS));
  getWorkerSweepSettings.mockReturnValue(ok(WORKER_SWEEPS));
  getAdvancedSettings.mockReturnValue(ok(ADVANCED));
  getForecastMarketSettings.mockReturnValue(ok(FORECAST_MARKET));
  getExecutionGateSettings.mockReturnValue(ok(EXECUTION_GATES));
  getPredictorTuningSettings.mockReturnValue(ok(PREDICTOR_TUNING));
  getMarketEventsSettings.mockReturnValue(ok(MARKET_EVENTS));
  getNotificationSettings.mockReturnValue(ok(NOTIFICATIONS));
});

afterEach(() => cleanup());

describe("InstellingenPage", () => {
  it("renders the three sections with loaded values", async () => {
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-risk-section"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("instellingen-strategy-section"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("instellingen-universe-section"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("instellingen-connection-section"),
    ).toBeInTheDocument();
    // Connection key-set state reflected; the key value is never rendered.
    expect(
      screen.getByTestId("instellingen-connection-key-state"),
    ).toHaveTextContent("Sleutel is ingesteld");
    expect(
      screen.getByTestId("instellingen-connection-ibkr_account_id"),
    ).toHaveValue("DU1234567");

    // Risk-limit field pre-filled from the loaded value.
    expect(
      screen.getByTestId("instellingen-risk-daily_max_approvals"),
    ).toHaveValue(5);
    // Strategy dropdown pre-filled.
    expect(
      screen.getByTestId("instellingen-strategy-risk_level"),
    ).toHaveValue("medium");
    // Universe checkbox pre-filled.
    expect(
      screen.getByTestId("instellingen-universe-allow_etfs"),
    ).toBeChecked();
    // Read-only blocked asset types displayed.
    expect(
      screen.getByTestId("instellingen-universe-blocked"),
    ).toHaveTextContent("options, futures, crypto");
  });

  it("saves an edited risk-limit field via updateRiskLimits", async () => {
    updateRiskLimits.mockReturnValue(
      ok({ ...RISK_LIMITS, daily_max_approvals: 3 }),
    );
    render(<Page />);
    const input = await screen.findByTestId(
      "instellingen-risk-daily_max_approvals",
    );
    await userEvent.clear(input);
    await userEvent.type(input, "3");
    await userEvent.click(
      screen.getByTestId("instellingen-risk-save-button"),
    );
    await waitFor(() => expect(updateRiskLimits).toHaveBeenCalledTimes(1));
    expect(updateRiskLimits).toHaveBeenCalledWith(
      expect.objectContaining({ daily_max_approvals: 3 }),
    );
    expect(
      await screen.findByTestId("instellingen-risk-saved-message"),
    ).toBeInTheDocument();
  });

  it("saves an edited strategy field with the merged user_strategy", async () => {
    updateTradingSettings.mockReturnValue(ok(TRADING));
    render(<Page />);
    const select = await screen.findByTestId(
      "instellingen-strategy-risk_level",
    );
    await userEvent.selectOptions(select, "high");
    await userEvent.click(
      screen.getByTestId("instellingen-strategy-save-button"),
    );
    await waitFor(() =>
      expect(updateTradingSettings).toHaveBeenCalledTimes(1),
    );
    const payload = updateTradingSettings.mock.calls[0][0];
    expect(payload.user_strategy.risk_level).toBe("high");
    // Edited values present.
    expect(payload.user_strategy.portfolio_goal).toBe("balanced_growth_risk");
    // Unrendered field preserved via the spread-merge.
    expect(payload.user_strategy.explanation_nl).toBe(
      "Voorkeurlaag voor ranking en fit.",
    );
    // The full allowed_universe is sent unchanged.
    expect(payload.allowed_universe).toEqual(TRADING.allowed_universe);
  });

  it("renders the V1.2 profit-harvest cycle parameters with defaults", async () => {
    render(<Page />);
    // Heading and the 10 trading_* inputs are present.
    expect(
      await screen.findByTestId("instellingen-profit-harvest-heading"),
    ).toBeInTheDocument();
    expect(
      (
        screen.getByTestId(
          "instellingen-strategy-trading_target_net_pct",
        ) as HTMLInputElement
      ).value,
    ).toBe("4");
    expect(
      (
        screen.getByTestId(
          "instellingen-strategy-trading_horizon_min_months",
        ) as HTMLInputElement
      ).value,
    ).toBe("3");
    expect(
      (
        screen.getByTestId(
          "instellingen-strategy-trading_horizon_max_months",
        ) as HTMLInputElement
      ).value,
    ).toBe("6");
    expect(
      (
        screen.getByTestId(
          "instellingen-strategy-trading_confidence_threshold_pct",
        ) as HTMLInputElement
      ).value,
    ).toBe("70");
    expect(
      (
        screen.getByTestId(
          "instellingen-strategy-trading_total_budget_eur",
        ) as HTMLInputElement
      ).value,
    ).toBe("1000000");
  });

  it("saves edited profit-harvest cycle parameters via updateTradingSettings", async () => {
    updateTradingSettings.mockReturnValue(ok(TRADING));
    render(<Page />);
    const targetInput = await screen.findByTestId(
      "instellingen-strategy-trading_target_net_pct",
    );
    await userEvent.clear(targetInput);
    await userEvent.type(targetInput, "5");
    const confInput = screen.getByTestId(
      "instellingen-strategy-trading_confidence_threshold_pct",
    );
    await userEvent.clear(confInput);
    await userEvent.type(confInput, "75");
    await userEvent.click(
      screen.getByTestId("instellingen-strategy-save-button"),
    );
    await waitFor(() =>
      expect(updateTradingSettings).toHaveBeenCalledTimes(1),
    );
    const payload = updateTradingSettings.mock.calls[0][0];
    expect(payload.user_strategy.trading_target_net_pct).toBe("5");
    expect(payload.user_strategy.trading_confidence_threshold_pct).toBe("75");
    // Defaults flow through for the untouched fields.
    expect(payload.user_strategy.trading_horizon_min_months).toBe("3");
    expect(payload.user_strategy.trading_horizon_max_months).toBe("6");
    expect(payload.user_strategy.trading_min_position_eur).toBe("25000");
    expect(payload.user_strategy.trading_max_position_eur).toBe("100000");
  });

  it("saves a universe toggle with the merged allowed_universe", async () => {
    updateTradingSettings.mockReturnValue(ok(TRADING));
    render(<Page />);
    const checkbox = await screen.findByTestId(
      "instellingen-universe-allow_bond_etfs",
    );
    await userEvent.click(checkbox);
    await userEvent.click(
      screen.getByTestId("instellingen-universe-save-button"),
    );
    await waitFor(() =>
      expect(updateTradingSettings).toHaveBeenCalledTimes(1),
    );
    const payload = updateTradingSettings.mock.calls[0][0];
    expect(payload.allowed_universe.allow_bond_etfs).toBe(true);
    expect(payload.allowed_universe.allow_etfs).toBe(true);
    // The full user_strategy is sent unchanged.
    expect(payload.user_strategy).toEqual(TRADING.user_strategy);
  });

  it("saves an edited connection field via updateConnectionSettings", async () => {
    updateConnectionSettings.mockReturnValue(
      ok({ ...CONNECTION, ibkr_account_id: "DU9999999" }),
    );
    render(<Page />);
    const input = await screen.findByTestId(
      "instellingen-connection-ibkr_account_id",
    );
    await userEvent.clear(input);
    await userEvent.type(input, "DU9999999");
    await userEvent.click(
      screen.getByTestId("instellingen-connection-save-button"),
    );
    await waitFor(() =>
      expect(updateConnectionSettings).toHaveBeenCalledTimes(1),
    );
    expect(updateConnectionSettings).toHaveBeenCalledWith(
      expect.objectContaining({ ibkr_account_id: "DU9999999" }),
    );
    expect(
      await screen.findByTestId("instellingen-connection-saved-message"),
    ).toBeInTheDocument();
  });

  it("omits claude_ai_api_key when the key input is left blank", async () => {
    updateConnectionSettings.mockReturnValue(ok(CONNECTION));
    render(<Page />);
    await screen.findByTestId("instellingen-connection-section");
    await userEvent.click(
      screen.getByTestId("instellingen-connection-save-button"),
    );
    await waitFor(() =>
      expect(updateConnectionSettings).toHaveBeenCalledTimes(1),
    );
    const payload = updateConnectionSettings.mock.calls[0][0];
    // Blank key input -> the field is omitted so the stored key is preserved.
    expect("claude_ai_api_key" in payload).toBe(false);
  });

  it("sends claude_ai_api_key only when the operator types one", async () => {
    updateConnectionSettings.mockReturnValue(
      ok({ ...CONNECTION, claude_ai_api_key_set: true }),
    );
    render(<Page />);
    const keyInput = await screen.findByTestId(
      "instellingen-connection-claude_ai_api_key",
    );
    await userEvent.type(keyInput, "sk-ant-new-key");
    await userEvent.click(
      screen.getByTestId("instellingen-connection-save-button"),
    );
    await waitFor(() =>
      expect(updateConnectionSettings).toHaveBeenCalledTimes(1),
    );
    const payload = updateConnectionSettings.mock.calls[0][0];
    expect(payload.claude_ai_api_key).toBe("sk-ant-new-key");
  });

  it("renders the three AI feature checkboxes (PR L)", async () => {
    render(<Page />);
    expect(
      await screen.findByTestId(
        "instellingen-connection-ai_explanation_morning_batch_enabled",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("instellingen-connection-ai_email_summary_enabled"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId(
        "instellingen-connection-research_ai_extraction_enabled",
      ),
    ).toBeInTheDocument();
  });

  it("sends the AI feature toggles in the save payload", async () => {
    updateConnectionSettings.mockReturnValue(
      ok({
        ...CONNECTION,
        ai_explanation_morning_batch_enabled: true,
        ai_email_summary_enabled: true,
        research_ai_extraction_enabled: true,
      }),
    );
    render(<Page />);
    await userEvent.click(
      await screen.findByTestId(
        "instellingen-connection-ai_explanation_morning_batch_enabled",
      ),
    );
    await userEvent.click(
      screen.getByTestId("instellingen-connection-ai_email_summary_enabled"),
    );
    await userEvent.click(
      screen.getByTestId(
        "instellingen-connection-research_ai_extraction_enabled",
      ),
    );
    await userEvent.click(
      screen.getByTestId("instellingen-connection-save-button"),
    );
    await waitFor(() =>
      expect(updateConnectionSettings).toHaveBeenCalledTimes(1),
    );
    expect(updateConnectionSettings).toHaveBeenCalledWith(
      expect.objectContaining({
        ai_explanation_morning_batch_enabled: true,
        ai_email_summary_enabled: true,
        research_ai_extraction_enabled: true,
      }),
    );
  });

  it("renders the scan-universe multi-select with stored selection", async () => {
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-universe-scan-section"),
    ).toBeInTheDocument();
    const bel20 = screen.getByTestId("instellingen-universe-scan-option-BEL20");
    const aex = screen.getByTestId("instellingen-universe-scan-option-AEX");
    const cac40 = screen.getByTestId("instellingen-universe-scan-option-CAC40");
    expect(bel20.querySelector("input")).toBeChecked();
    expect(aex.querySelector("input")).toBeChecked();
    expect(cac40.querySelector("input")).not.toBeChecked();
  });

  it("saves the multi-select via updateUniverseScanSettings", async () => {
    updateUniverseScanSettings.mockReturnValue(
      ok({ ...UNIVERSE_SCAN, selected_codes: ["BEL20", "AEX", "CAC40"] }),
    );
    render(<Page />);
    await screen.findByTestId("instellingen-universe-scan-section");
    // Toggle CAC40 on.
    const cac40 = screen.getByTestId("instellingen-universe-scan-option-CAC40");
    const checkbox = cac40.querySelector("input");
    expect(checkbox).not.toBeNull();
    await userEvent.click(checkbox as HTMLInputElement);
    await userEvent.click(screen.getByTestId("instellingen-universe-scan-save"));
    await waitFor(() =>
      expect(updateUniverseScanSettings).toHaveBeenCalledTimes(1),
    );
    expect(updateUniverseScanSettings.mock.calls[0][0]).toEqual({
      selected_codes: ["BEL20", "AEX", "CAC40"],
    });
  });

  it("renders the order-policy section with persisted values", async () => {
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-order-policy-section"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("instellingen-order-policy-default_buy_value_eur"),
    ).toHaveValue(1000);
    expect(
      screen.getByTestId("instellingen-order-policy-max_sector_pct"),
    ).toHaveValue(30);
    expect(
      screen.getByTestId("instellingen-order-policy-suggestion_valid_minutes"),
    ).toHaveValue(1440);
  });

  it("saves the order policy with the edited values", async () => {
    updateOrderPolicySettings.mockReturnValue(
      ok({
        ...ORDER_POLICY,
        default_buy_value_eur: "2500",
        max_sector_pct: "25",
      }),
    );
    render(<Page />);
    const input = await screen.findByTestId(
      "instellingen-order-policy-default_buy_value_eur",
    );
    await userEvent.clear(input);
    await userEvent.type(input, "2500");
    const cap = screen.getByTestId("instellingen-order-policy-max_sector_pct");
    await userEvent.clear(cap);
    await userEvent.type(cap, "25");
    await userEvent.click(screen.getByTestId("instellingen-order-policy-save"));
    await waitFor(() =>
      expect(updateOrderPolicySettings).toHaveBeenCalledTimes(1),
    );
    const payload = updateOrderPolicySettings.mock.calls[0][0];
    expect(payload.default_buy_value_eur).toBe("2500");
    expect(payload.max_sector_pct).toBe("25");
    expect(payload.suggestion_valid_minutes).toBe(1440);
  });

  it("renders the scheduler section + saves an edited cron", async () => {
    updateSchedulerSettings.mockReturnValue(
      ok({ ...SCHEDULER, scheduler_daily_briefing_cron: "45 7 * * *" }),
    );
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-scheduler-section"),
    ).toBeInTheDocument();
    const cron = screen.getByTestId("instellingen-scheduler-cron");
    expect(cron).toHaveValue("30 6 * * *");
    await userEvent.clear(cron);
    await userEvent.type(cron, "45 7 * * *");
    await userEvent.click(screen.getByTestId("instellingen-scheduler-save"));
    await waitFor(() =>
      expect(updateSchedulerSettings).toHaveBeenCalledTimes(1),
    );
    expect(updateSchedulerSettings.mock.calls[0][0]).toEqual({
      scheduler_daily_briefing_cron: "45 7 * * *",
      ibkr_sync_interval_minutes: 15,
    });
  });

  it("renders the data-windows section + saves edited lookbacks", async () => {
    updateDataWindowSettings.mockReturnValue(
      ok({ ...DATA_WINDOWS, forecast_history_lookback_days: 600 }),
    );
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-data-windows-section"),
    ).toBeInTheDocument();
    const lookback = screen.getByTestId("instellingen-data-history_lookback");
    expect(lookback).toHaveValue(400);
    await userEvent.clear(lookback);
    await userEvent.type(lookback, "600");
    await userEvent.click(
      screen.getByTestId("instellingen-data-windows-save"),
    );
    await waitFor(() =>
      expect(updateDataWindowSettings).toHaveBeenCalledTimes(1),
    );
    expect(updateDataWindowSettings.mock.calls[0][0]).toEqual({
      forecast_history_lookback_days: 600,
      forecast_minimum_bars_required: 60,
      daily_briefing_lookback_hours: 24,
      universe_scan_cache_ttl_hours: 24,
    });
  });

  it("renders the worker-sweeps section + saves edited values", async () => {
    updateWorkerSweepSettings.mockReturnValue(
      ok({
        ...WORKER_SWEEPS,
        sweep_interval_seconds: 120,
        eodhd_rate_limit_per_second: 5,
      }),
    );
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-worker-sweeps-section"),
    ).toBeInTheDocument();
    const interval = screen.getByTestId("instellingen-worker-sweep_interval");
    expect(interval).toHaveValue(60);
    await userEvent.clear(interval);
    await userEvent.type(interval, "120");
    const rate = screen.getByTestId("instellingen-worker-eodhd_rate");
    await userEvent.clear(rate);
    await userEvent.type(rate, "5");
    await userEvent.click(
      screen.getByTestId("instellingen-worker-sweeps-save"),
    );
    await waitFor(() =>
      expect(updateWorkerSweepSettings).toHaveBeenCalledTimes(1),
    );
    const payload = updateWorkerSweepSettings.mock.calls[0][0];
    expect(payload.sweep_interval_seconds).toBe(120);
    expect(payload.eodhd_rate_limit_per_second).toBe(5);
    expect(payload.sweep_retry_max_attempts).toBe(3);
  });

  it("renders the advanced section collapsed by default + saves when expanded", async () => {
    updateAdvancedSettings.mockReturnValue(
      ok({
        ...ADVANCED,
        ensemble_weight_strategy: "auto",
        action_draft_approval_valid_minutes: 10,
      }),
    );
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-advanced-section"),
    ).toBeInTheDocument();
    const toggle = screen.getByTestId("instellingen-advanced-toggle");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    // Inputs are hidden while collapsed.
    expect(
      screen.queryByTestId("instellingen-advanced-ensemble"),
    ).not.toBeInTheDocument();
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const ensemble = screen.getByTestId("instellingen-advanced-ensemble");
    expect(ensemble).toHaveValue("equal_weight");
    await userEvent.selectOptions(ensemble, "auto");
    const minutes = screen.getByTestId(
      "instellingen-advanced-approval-minutes",
    );
    await userEvent.clear(minutes);
    await userEvent.type(minutes, "10");
    await userEvent.click(
      screen.getByTestId("instellingen-advanced-save"),
    );
    await waitFor(() =>
      expect(updateAdvancedSettings).toHaveBeenCalledTimes(1),
    );
    expect(updateAdvancedSettings.mock.calls[0][0]).toEqual({
      ensemble_weight_strategy: "auto",
      gbm_drift_window_days: null,
      action_draft_approval_valid_minutes: 10,
      ai_explanation_provider_code: "stub",
      sharpe_strong_threshold: "1.0",
      sharpe_slight_threshold: "0.3",
    });
  });

  it("renders the sharpe thresholds in the advanced section and saves them", async () => {
    updateAdvancedSettings.mockReturnValue(
      ok({
        ...ADVANCED,
        sharpe_strong_threshold: "1.5",
        sharpe_slight_threshold: "0.5",
      }),
    );
    render(<Page />);
    await userEvent.click(
      await screen.findByTestId("instellingen-advanced-toggle"),
    );
    const strong = screen.getByTestId("instellingen-advanced-sharpe-strong");
    const slight = screen.getByTestId("instellingen-advanced-sharpe-slight");
    expect(strong).toHaveValue(1.0);
    expect(slight).toHaveValue(0.3);
    await userEvent.clear(strong);
    await userEvent.type(strong, "1.5");
    await userEvent.clear(slight);
    await userEvent.type(slight, "0.5");
    await userEvent.click(
      screen.getByTestId("instellingen-advanced-save"),
    );
    await waitFor(() =>
      expect(updateAdvancedSettings).toHaveBeenCalledTimes(1),
    );
    const payload = updateAdvancedSettings.mock.calls[0][0];
    expect(payload.sharpe_strong_threshold).toBe("1.5");
    expect(payload.sharpe_slight_threshold).toBe("0.5");
  });

  it("renders the forecast & market section + saves edited values", async () => {
    updateForecastMarketSettings.mockReturnValue(
      ok({
        ...FORECAST_MARKET,
        forecast_horizon_trading_days: 60,
        forecast_ensemble_enabled: true,
        universe_set: "EU600",
      }),
    );
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-forecast-market-section"),
    ).toBeInTheDocument();
    const horizon = screen.getByTestId("instellingen-forecast-horizon");
    expect(horizon).toHaveValue(21);
    await userEvent.clear(horizon);
    await userEvent.type(horizon, "60");
    await userEvent.click(
      screen.getByTestId("instellingen-forecast-ensemble"),
    );
    await userEvent.selectOptions(
      screen.getByTestId("instellingen-forecast-universe-set"),
      "EU600",
    );
    await userEvent.click(
      screen.getByTestId("instellingen-forecast-market-save"),
    );
    await waitFor(() =>
      expect(updateForecastMarketSettings).toHaveBeenCalledTimes(1),
    );
    const payload = updateForecastMarketSettings.mock.calls[0][0];
    expect(payload.forecast_horizon_trading_days).toBe(60);
    expect(payload.forecast_ensemble_enabled).toBe(true);
    expect(payload.universe_set).toBe("EU600");
    expect(payload.suggestions_risk_profile).toBe("Gebalanceerd");
  });

  it("renders the execution-gates section + flips toggles + saves", async () => {
    updateExecutionGateSettings.mockReturnValue(
      ok({
        ...EXECUTION_GATES,
        ibkr_paper_order_submission_enabled: true,
        submission_sweep_enabled: true,
      }),
    );
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-execution-gates-section"),
    ).toBeInTheDocument();
    const paperSubmit = screen.getByTestId(
      "instellingen-execution-paper-submit",
    );
    const submissionSweep = screen.getByTestId(
      "instellingen-execution-submission-sweep",
    );
    expect(paperSubmit).not.toBeChecked();
    expect(submissionSweep).not.toBeChecked();
    await userEvent.click(paperSubmit);
    await userEvent.click(submissionSweep);
    await userEvent.click(
      screen.getByTestId("instellingen-execution-gates-save"),
    );
    await waitFor(() =>
      expect(updateExecutionGateSettings).toHaveBeenCalledTimes(1),
    );
    const payload = updateExecutionGateSettings.mock.calls[0][0];
    expect(payload.ibkr_paper_order_submission_enabled).toBe(true);
    expect(payload.submission_sweep_enabled).toBe(true);
    expect(payload.cancel_sweep_enabled).toBe(false);
    expect(payload.morning_chain_after_pre_briefing).toBe(false);
  });

  it("renders the predictor-tuning accordion + saves when expanded", async () => {
    updatePredictorTuningSettings.mockReturnValue(
      ok({
        ...PREDICTOR_TUNING,
        forecast_valid_minutes: 720,
        gbm_regime_shift_enabled: true,
      }),
    );
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-predictor-tuning-section"),
    ).toBeInTheDocument();
    const toggle = screen.getByTestId(
      "instellingen-predictor-tuning-toggle",
    );
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(
      screen.queryByTestId("instellingen-predictor-forecast-ttl"),
    ).not.toBeInTheDocument();
    await userEvent.click(toggle);
    const ttl = screen.getByTestId("instellingen-predictor-forecast-ttl");
    expect(ttl).toHaveValue(1440);
    await userEvent.clear(ttl);
    await userEvent.type(ttl, "720");
    await userEvent.click(
      screen.getByTestId("instellingen-predictor-regime-enabled"),
    );
    await userEvent.click(
      screen.getByTestId("instellingen-predictor-tuning-save"),
    );
    await waitFor(() =>
      expect(updatePredictorTuningSettings).toHaveBeenCalledTimes(1),
    );
    const payload = updatePredictorTuningSettings.mock.calls[0][0];
    expect(payload.forecast_valid_minutes).toBe(720);
    expect(payload.gbm_regime_shift_enabled).toBe(true);
    expect(payload.decision_packages_valid_minutes).toBe(1440);
  });

  it("renders the market-events section with active sessions + planned fires", async () => {
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-market-events-section"),
    ).toBeInTheDocument();
    // The resolved active-sessions list and the planned-fires list
    // both render — the operator's universe choice has produced a
    // scheduled close fire.
    expect(
      screen.getByTestId("instellingen-market-events-active-sessions"),
    ).toHaveTextContent("Euronext");
    expect(
      screen.getByTestId("instellingen-market-events-fires-list"),
    ).toHaveTextContent("17:45");
    // The default-off open-check toggle is unchecked; the close
    // digest toggle is checked.
    expect(
      screen.getByTestId("instellingen-market-events-close-enabled"),
    ).toBeChecked();
    expect(
      screen.getByTestId("instellingen-market-events-open-enabled"),
    ).not.toBeChecked();
  });

  it("shows a warning when no markets are selected and saves the toggles", async () => {
    getMarketEventsSettings.mockReturnValue(
      ok({
        ...MARKET_EVENTS,
        universe_codes_selected: [],
        active_sessions: [],
        fires: [],
      }),
    );
    updateMarketEventsSettings.mockReturnValue(
      ok({
        ...MARKET_EVENTS,
        per_market_open_alerts_enabled: true,
      }),
    );
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-market-events-no-sessions"),
    ).toHaveTextContent("Geen markten geselecteerd");

    // Flip the open-alerts toggle and save.
    await userEvent.click(
      screen.getByTestId("instellingen-market-events-open-enabled"),
    );
    await userEvent.click(
      screen.getByTestId("instellingen-market-events-save"),
    );
    await waitFor(() =>
      expect(updateMarketEventsSettings).toHaveBeenCalledTimes(1),
    );
    const payload = updateMarketEventsSettings.mock.calls[0][0];
    expect(payload.per_market_close_digest_enabled).toBe(true);
    expect(payload.per_market_open_alerts_enabled).toBe(true);
  });

  it("renders the notifications section + stub-mode banner when real client off", async () => {
    render(<Page />);
    expect(
      await screen.findByTestId("instellingen-notifications-section"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("instellingen-notifications-stub-banner"),
    ).toHaveTextContent("Stub-modus actief");
    expect(
      screen.getByTestId("instellingen-notifications-smtp-host"),
    ).toBeInTheDocument();
  });

  it("does NOT echo the smtp password back from the GET response", async () => {
    getNotificationSettings.mockReturnValue(
      ok({ ...NOTIFICATIONS, smtp_password_set: true }),
    );
    render(<Page />);
    const passwordInput = await screen.findByTestId(
      "instellingen-notifications-smtp-password",
    );
    // Input is rendered with the empty placeholder pattern, never the
    // value — the API never returns the password.
    expect(passwordInput).toHaveValue("");
    expect(passwordInput).toHaveAttribute("placeholder", expect.stringContaining("opgeslagen"));
  });

  it("saves notification settings + clears password input after success", async () => {
    updateNotificationSettings.mockReturnValue(
      ok({
        ...NOTIFICATIONS,
        smtp_host: "smtp.example.com",
        smtp_password_set: true,
      }),
    );
    render(<Page />);
    const hostInput = await screen.findByTestId(
      "instellingen-notifications-smtp-host",
    );
    await userEvent.type(hostInput, "smtp.example.com");
    const passwordInput = screen.getByTestId(
      "instellingen-notifications-smtp-password",
    );
    await userEvent.type(passwordInput, "secret-value");
    await userEvent.click(
      screen.getByTestId("instellingen-notifications-save"),
    );
    await waitFor(() =>
      expect(updateNotificationSettings).toHaveBeenCalledTimes(1),
    );
    // After save, the password input is cleared so a refresh doesn't
    // re-submit the secret.
    expect(passwordInput).toHaveValue("");
  });

  it("shows test-email result when 'Test e-mail' is clicked", async () => {
    sendTestEmail.mockReturnValue(
      ok({
        sent: false,
        status: "stubbed",
        detail_nl: "Stub-modus: niet verzonden.",
        used_host: "smtp.example.com",
      }),
    );
    render(<Page />);
    await userEvent.click(
      await screen.findByTestId("instellingen-notifications-test-email"),
    );
    await waitFor(() => {
      expect(sendTestEmail).toHaveBeenCalledTimes(1);
    });
    expect(
      screen.getByTestId("instellingen-notifications-test-result"),
    ).toHaveTextContent("Stub-modus");
  });
});
