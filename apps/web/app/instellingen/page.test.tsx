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
  getRiskLimits.mockReturnValue(ok(RISK_LIMITS));
  getTradingSettings.mockReturnValue(ok(TRADING));
  getConnectionSettings.mockReturnValue(ok(CONNECTION));
  getUniverseScanSettings.mockReturnValue(ok(UNIVERSE_SCAN));
  getOrderPolicySettings.mockReturnValue(ok(ORDER_POLICY));
  getSchedulerSettings.mockReturnValue(ok(SCHEDULER));
  getDataWindowSettings.mockReturnValue(ok(DATA_WINDOWS));
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
});
