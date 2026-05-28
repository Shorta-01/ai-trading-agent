import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  RiskLimitsResponse,
  TradingSettingsResponse,
} from "@/lib/apiClient";

const getRiskLimits = vi.fn();
const updateRiskLimits = vi.fn();
const getTradingSettings = vi.fn();
const updateTradingSettings = vi.fn();

vi.mock("@/lib/apiClient", () => ({
  apiClient: {
    getRiskLimits: (...a: unknown[]) => getRiskLimits(...a),
    updateRiskLimits: (...a: unknown[]) => updateRiskLimits(...a),
    getTradingSettings: (...a: unknown[]) => getTradingSettings(...a),
    updateTradingSettings: (...a: unknown[]) => updateTradingSettings(...a),
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

function ok<T>(data: T) {
  return Promise.resolve({ ok: true as const, data });
}

beforeEach(() => {
  getRiskLimits.mockReset();
  updateRiskLimits.mockReset();
  getTradingSettings.mockReset();
  updateTradingSettings.mockReset();
  getRiskLimits.mockReturnValue(ok(RISK_LIMITS));
  getTradingSettings.mockReturnValue(ok(TRADING));
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
      screen.getByTestId("instellingen-config-note"),
    ).toBeInTheDocument();

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
});
