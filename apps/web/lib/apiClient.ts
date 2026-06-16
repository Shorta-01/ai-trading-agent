import type { components } from "./api-types";

/**
 * Reference a backend response shape generated from the FastAPI OpenAPI
 * schema (`lib/api-types.ts`, regenerated with `npm run gen:api-types`).
 * Prefer this over hand-written response types — it is the single source
 * of truth and surfaces backend/frontend drift at compile time.
 */
export type ApiSchema<K extends keyof components["schemas"]> =
  components["schemas"][K];

export type FetchState<T> =
  | { ok: true; data: T }
  | { ok: false; reason: "not_reachable" };

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; message: string }
  | { ok: false; status: 0; message: string };

export type ServiceStatusCard = {
  key: string;
  label_nl: string;
  status_key: string;
  status_nl: string;
  help_nl: string;
  blocks_suggestions: boolean;
  last_checked_at: string | null;
  action_nl?: string | null;
};

export type SystemStatusSummary = {
  project_name: string;
  mode: string;
  title_nl: string;
  summary_nl: string;
  help_nl: string;
  paper_only: boolean;
  can_create_new_suggestions: boolean;
  suggestion_status_nl: string;
  suggestion_help_nl: string;
  services: ServiceStatusCard[];
};

export type SettingsSummary = {
  title_nl: string;
  help_nl: string;
  ibkr: {
    label_nl: string;
    status_nl: string;
    help_nl: string;
    paper_account_required: boolean;
    live_order_transmission_allowed: boolean;
  };
  openai: {
    label_nl: string;
    status_nl: string;
    help_nl: string;
    api_key_configured: boolean;
  };
  secret_safety: {
    label_nl: string;
    help_nl: string;
  };
};

export type AiUsageSummary = { title_nl: string; help_nl: string; usage_available: boolean; estimated_cost_usd: number | null; estimated_cost_eur: number | null; budget_status_nl: string; budget_help_nl: string; warning_nl: string; };
export type StorageStatusSummary = { title_nl: string; summary_nl: string; help_nl: string; selected_database_nl: string; migration_tool_nl: string; implementation_status_nl: string; first_persistence_target_nl: string; storage_ready: boolean; can_persist_paper_setup: boolean; };
// PR M — monitoring widget reads the live storage online state.
export type OnlineStorageStatusResponse = {
  configured: boolean;
  connected: boolean;
  safe_to_write: boolean;
  migration_readiness_status: string;
  writes_status_nl: string;
};
// PR O — Claude AI budget pill on the dashboard triage strip.
export type ClaudeBudgetStatusResponse = {
  status: string; // "ok" | "not_configured" | "storage_unavailable"
  status_nl: string;
  help_nl: string;
  monthly_cap_eur: string;
  budget_month: string | null;
  monthly_total_eur: string | null;
  remaining_eur: string | null;
  exceeded: boolean;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};
// PR P — NAV history sparkline feed.
export type NavHistoryPoint = {
  recorded_at_utc: string;
  nav_value: string; // serialised Decimal
};
export type NavHistoryResponse = {
  status: string;
  status_nl: string;
  help_nl: string;
  ibkr_account_id: string | null;
  base_currency: string | null;
  days_requested: number;
  points: NavHistoryPoint[];
};
// PR N — dashboard market-hours widget feed.
export type MarketHoursEntry = {
  market_code: string;
  market_label_nl: string;
  timezone: string;
  open_at_utc: string;
  close_at_utc: string;
  open_local_hhmm: string;
  close_local_hhmm: string;
  state: "pre_open" | "open" | "post_close" | "weekend";
  state_nl: string;
  next_event_kind: "open" | "close" | null;
  next_event_at_utc: string | null;
};
export type MarketHoursNowResponse = {
  now_utc: string;
  universe_codes_selected: string[];
  markets: MarketHoursEntry[];
  help_nl: string;
};
// PR Q — predictor performance leaderboard for the dashboard.
export type PredictorPerformanceEntry = {
  model_code: string;
  model_version: string;
  sample_count: number;
  realised_sample_count: number;
  mean_brier_score: string | null;
  mean_return_spread_pct: string | null;
  mean_realised_return_pct: string | null;
};
export type PredictorPerformanceResponse = {
  status: string;
  status_nl: string;
  help_nl: string;
  lookback_days: number;
  total_contributions_considered: number;
  predictors: PredictorPerformanceEntry[];
  best_model_code: string | null;
  safe_for_orders: boolean;
  safe_for_action_drafts: boolean;
};
export type IntegrationCard = { key: string; label_nl: string; status_nl: string; help_nl: string; configured: boolean; connected: boolean; blocks_related_jobs: boolean; };
export type IntegrationsSummary = { title_nl: string; help_nl: string; cards: IntegrationCard[]; };

export type TradingSettingsResponse = {
  title_nl: string;
  status_nl: string;
  settings_source: string;
  settings_source_nl: string;
  message_nl: string;
  allowed_universe: Record<string, boolean>;
  user_strategy: Record<string, unknown>;
  always_blocked_asset_types: string[];
  help_texts: { key: string; label_nl: string; help_nl: string }[];
  safety_summary_nl: string;
  updated?: boolean;
};

export type TradingSettingsUpdateInput = {
  allowed_universe: Record<string, boolean>;
  user_strategy: Record<string, unknown>;
  reason_nl?: string;
};

// Risk-limits (behavioural guardrail) settings — Task 138. Hand-defined to
// mirror ``RiskLimitsResponse``/``UpdateRiskLimitsRequest`` in
// ``apps/api/src/portfolio_outlook_api/risk_limits_routes.py``. Decimal
// fields are strings on the wire (no float rounding).
export type RiskLimitsResponse = {
  ibkr_account_id: string;
  daily_max_approvals: number;
  cooldown_seconds: number;
  anti_revenge_window_hours: number;
  anti_revenge_loss_threshold_pct: string;
  soft_drawdown_pct: string;
  soft_drawdown_window_days: number;
  hard_drawdown_pct: string;
  hard_drawdown_window_days: number;
  fomo_drift_pct: string;
  last_updated_at: string;
};

export type RiskLimitsUpdateInput = {
  daily_max_approvals: number;
  cooldown_seconds: number;
  anti_revenge_window_hours: number;
  anti_revenge_loss_threshold_pct: string;
  soft_drawdown_pct: string;
  soft_drawdown_window_days: number;
  hard_drawdown_pct: string;
  hard_drawdown_window_days: number;
  fomo_drift_pct: string;
};

// Hand-defined types that mirror ``ConnectionSettingsResponse`` /
// ``UpdateConnectionSettingsRequest`` in
// ``apps/api/src/portfolio_outlook_api/runtime_config_routes.py``. The Claude
// API key is write-only: the response only carries ``claude_ai_api_key_set``
// and never the key value. The monthly budget is a string on the wire (no
// float rounding).
export type UniverseScanIndexOption = {
  code: string;
  label_nl: string;
};

export type UniverseScanSettingsResponse = {
  selected_codes: string[];
  available_codes: UniverseScanIndexOption[];
  help_nl: string;
};

export type OrderPolicySettingsResponse = {
  default_buy_value_eur: string;
  default_top_up_pct: string;
  default_reduce_pct: string;
  max_sector_pct: string;
  cost_dominates_ratio: string;
  suggestion_valid_minutes: number;
  help_nl: string;
};

export type OrderPolicySettingsUpdateInput = {
  default_buy_value_eur: string;
  default_top_up_pct: string;
  default_reduce_pct: string;
  max_sector_pct: string;
  cost_dominates_ratio: string;
  suggestion_valid_minutes: number;
};

export type SchedulerSettingsResponse = {
  scheduler_daily_briefing_cron: string;
  ibkr_sync_interval_minutes: number;
  help_nl: string;
};

export type SchedulerSettingsUpdateInput = {
  scheduler_daily_briefing_cron: string;
  ibkr_sync_interval_minutes: number;
};

export type DataWindowSettingsResponse = {
  forecast_history_lookback_days: number;
  forecast_minimum_bars_required: number;
  daily_briefing_lookback_hours: number;
  universe_scan_cache_ttl_hours: number;
  help_nl: string;
};

export type DataWindowSettingsUpdateInput = {
  forecast_history_lookback_days: number;
  forecast_minimum_bars_required: number;
  daily_briefing_lookback_hours: number;
  universe_scan_cache_ttl_hours: number;
};

export type WorkerSweepSettingsResponse = {
  sweep_interval_seconds: number;
  sweep_retry_max_attempts: number;
  sweep_retry_backoff_seconds: string;
  sweep_alert_after_consecutive_errors: number;
  eodhd_rate_limit_per_second: number;
  help_nl: string;
};

export type WorkerSweepSettingsUpdateInput = {
  sweep_interval_seconds: number;
  sweep_retry_max_attempts: number;
  sweep_retry_backoff_seconds: string;
  sweep_alert_after_consecutive_errors: number;
  eodhd_rate_limit_per_second: number;
};

export type AdvancedSettingsResponse = {
  ensemble_weight_strategy: string;
  gbm_drift_window_days: number | null;
  action_draft_approval_valid_minutes: number;
  ai_explanation_provider_code: string;
  sharpe_strong_threshold: string;
  sharpe_slight_threshold: string;
  help_nl: string;
};

export type AdvancedSettingsUpdateInput = {
  ensemble_weight_strategy: string;
  gbm_drift_window_days: number | null;
  action_draft_approval_valid_minutes: number;
  ai_explanation_provider_code: string;
  sharpe_strong_threshold: string;
  sharpe_slight_threshold: string;
};

export type ForecastMarketSettingsResponse = {
  forecast_horizon_trading_days: number;
  forecast_ensemble_enabled: boolean;
  suggestions_risk_profile: string;
  universe_set: string;
  market_data_provider: string;
  market_data_sync_enabled: boolean;
  ibkr_market_data_enabled: boolean;
  ibkr_market_data_type: string;
  help_nl: string;
};

export type ForecastMarketSettingsUpdateInput = {
  forecast_horizon_trading_days: number;
  forecast_ensemble_enabled: boolean;
  suggestions_risk_profile: string;
  universe_set: string;
  market_data_provider: string;
  market_data_sync_enabled: boolean;
  ibkr_market_data_enabled: boolean;
  ibkr_market_data_type: string;
};

export type ExecutionGateSettingsResponse = {
  ibkr_paper_order_submission_enabled: boolean;
  submission_sweep_enabled: boolean;
  cancel_sweep_enabled: boolean;
  morning_chain_after_pre_briefing: boolean;
  help_nl: string;
};

export type ExecutionGateSettingsUpdateInput = {
  ibkr_paper_order_submission_enabled: boolean;
  submission_sweep_enabled: boolean;
  cancel_sweep_enabled: boolean;
  morning_chain_after_pre_briefing: boolean;
};

export type PredictorTuningSettingsResponse = {
  forecast_valid_minutes: number;
  decision_packages_valid_minutes: number;
  prediction_diary_inconclusive_tolerance_pct: string;
  gbm_regime_shift_enabled: boolean;
  gbm_regime_shift_threshold_pct: string;
  help_nl: string;
};

export type PredictorTuningSettingsUpdateInput = {
  forecast_valid_minutes: number;
  decision_packages_valid_minutes: number;
  prediction_diary_inconclusive_tolerance_pct: string;
  gbm_regime_shift_enabled: boolean;
  gbm_regime_shift_threshold_pct: string;
};

export type MarketEventFire = {
  market_code: string;
  market_label_nl: string;
  timezone: string;
  event_kind: "open" | "close";
  fire_hour: number;
  fire_minute: number;
};

export type MarketEventsSettingsResponse = {
  per_market_close_digest_enabled: boolean;
  per_market_open_alerts_enabled: boolean;
  universe_codes_selected: string[];
  active_sessions: string[];
  fires: MarketEventFire[];
  help_nl: string;
};

export type MarketEventsSettingsUpdateInput = {
  per_market_close_digest_enabled: boolean;
  per_market_open_alerts_enabled: boolean;
};

export type NotificationSettingsResponse = {
  smtp_host: string | null;
  smtp_port: number;
  smtp_username: string | null;
  smtp_from: string | null;
  smtp_to: string | null;
  smtp_use_tls: boolean;
  smtp_password_set: boolean;
  notifications_email_enabled: boolean;
  notifications_email_real_client_enabled: boolean;
  notification_send_on_nav_drop: boolean;
  notification_send_on_position_drop: boolean;
  notification_send_on_high_confidence_sell: boolean;
  help_nl: string;
};

export type NotificationSettingsUpdateInput = {
  smtp_host: string | null;
  smtp_port: number;
  smtp_username: string | null;
  // Blank/omitted preserves the stored password.
  smtp_password: string | null;
  smtp_from: string | null;
  smtp_to: string | null;
  smtp_use_tls: boolean;
  notifications_email_enabled: boolean;
  notification_send_on_nav_drop: boolean;
  notification_send_on_position_drop: boolean;
  notification_send_on_high_confidence_sell: boolean;
};

export type TestEmailResponse = {
  sent: boolean;
  status: string;
  detail_nl: string;
  used_host: string | null;
};

export type DigestAlert = {
  kind: string;
  severity_nl: string;
  title_nl: string;
  body_nl: string;
  reference_kind: string | null;
  reference_id: string | null;
};

export type DigestTodayResponse = {
  status: string;
  status_nl: string;
  help_nl: string;
  generated_at: string | null;
  briefing_date: string | null;
  market_code: string | null;
  nav_summary: Record<string, unknown>;
  positions_summary: Record<string, unknown>;
  suggestions_summary: Record<string, unknown>;
  action_drafts_summary: Record<string, unknown>;
  alerts: DigestAlert[];
  safe_for_orders: boolean;
};

export type OrchestratorVerdictsSummaryResponse = {
  title_nl: string;
  help_nl: string;
  total: number;
  by_decision: Record<string, number>;
  latest_generated_at: string | null;
};

export type OrchestratorVerdictRow = {
  verdict_id: string;
  symbol: string;
  ibkr_conid: number | null;
  forecast_id: string | null;
  generated_at: string;
  decision: string;
  blocking_reason: string | null;
  summary_nl: string;
  details_json: Record<string, unknown>;
};

export type OrchestratorVerdictsListResponse = {
  title_nl: string;
  help_nl: string;
  items: OrchestratorVerdictRow[];
};

// V1.2 §AU / CLAUDE.md §5 — operator favorites + exclusions.

export type WatchlistFavoriteRow = {
  watchlist_preference_id: string;
  symbol: string;
  note: string | null;
  created_at: string;
  latest_decision: string | null;
  latest_blocking_reason: string | null;
  latest_summary_nl: string | null;
  latest_generated_at: string | null;
  latest_confidence: number | null;
};

export type WatchlistFavoritesResponse = {
  title_nl: string;
  help_nl: string;
  account_id: string;
  items: WatchlistFavoriteRow[];
};

export type WatchlistExclusionRow = {
  watchlist_preference_id: string;
  symbol: string;
  note: string | null;
  created_at: string;
};

export type WatchlistExclusionsResponse = {
  title_nl: string;
  help_nl: string;
  account_id: string;
  items: WatchlistExclusionRow[];
};

export type SaveWatchlistPreferenceInput = {
  account_id?: string;
  symbol: string;
  kind: "favorite" | "excluded";
  note?: string | null;
};

export type WatchlistPreferenceMutationResponse = {
  accepted: boolean;
  record_id: string | null;
  explanation_nl: string;
};

// V1.2 §AV — macro info-strip + sector spread.

export type MacroSnapshotResponse = {
  title_nl: string;
  help_nl: string;
  state: "rustig" | "verhoogd" | "stress" | "onbekend";
  severity: "info" | "warning" | "critical";
  headline_nl: string;
  vix_level: number | null;
  ma_short_day: number | null;
  ma_long_day: number | null;
  last_evaluated_at: string | null;
  sample_size: number;
};

export type SectorRow = {
  sector: string;
  weight_pct: number;
  notional_local_approx: string;
  position_count: number;
};

export type SectorSpreadResponse = {
  title_nl: string;
  help_nl: string;
  items: SectorRow[];
  total_positions: number;
  has_unclassified: boolean;
};

// V1.2 §AW — belastingjaaroverzicht.

export type TaxRealisedTrade = {
  symbol: string;
  account_id: string;
  currency_local: string;
  quantity: string;
  buy_date: string;
  buy_price_local: string;
  buy_exec_id: string;
  sell_date: string;
  sell_price_local: string;
  sell_exec_id: string;
  gross_local: string;
  tob_buy_local: string;
  tob_sell_local: string;
  net_local: string;
  hold_days: number;
  net_pct_on_cost: string;
  buy_action_draft_id: string | null;
  sell_action_draft_id: string | null;
  // V1.2 §BB — EUR fields, optional.
  buy_fx_rate_eur?: string | null;
  sell_fx_rate_eur?: string | null;
  gross_eur?: string | null;
  tob_buy_eur?: string | null;
  tob_sell_eur?: string | null;
  net_eur?: string | null;
};

export type TaxYearTotals = {
  trade_count: number;
  gross_local_by_currency: Record<string, string>;
  tob_local_by_currency: Record<string, string>;
  net_local_by_currency: Record<string, string>;
  average_hold_days: number;
  hit_rate_pct: number;
  earliest_close: string | null;
  latest_close: string | null;
  // V1.2 §BB — EUR-totalen.
  gross_eur_total?: string | null;
  tob_eur_total?: string | null;
  net_eur_total?: string | null;
  eur_conversion_coverage_pct?: number;
};

export type TaxMonthlyPoint = {
  month: string;
  net_local_by_currency: Record<string, string>;
  cumulative_net_local_by_currency: Record<string, string>;
};

export type TaxGoodHouseholder = {
  trades_per_year: number;
  average_hold_days: number;
  trading_capital_share_pct: number | null;
  uses_leverage: boolean;
  uses_shorts: boolean;
  summary_nl: string;
};

// V1.2 §BZ vervolg — IBKR-config audit-trail entry zoals in de
// belasting jaaroverzicht response.
export type TaxIbkrConfigAuditEntry = {
  created_at: string;
  event_code: string;
  severity: string;
  status: string;
  source: string;
  title_nl: string;
  message_nl: string;
};

export type TaxYearReportResponse = {
  title_nl: string;
  help_nl: string;
  year: number;
  realised_trades: TaxRealisedTrade[];
  year_totals: TaxYearTotals;
  monthly_points: TaxMonthlyPoint[];
  good_householder: TaxGoodHouseholder;
  dividends: unknown[];
  fx_conversion_available: boolean;
  notes_nl: string[];
  ibkr_config_audit?: TaxIbkrConfigAuditEntry[];
};

// V1.2 §AX — maandrapport.

export type MonthlyReportRealisedTrade = {
  symbol: string;
  currency_local: string;
  quantity: string;
  buy_date: string;
  sell_date: string;
  gross_local: string;
  net_local: string;
  hold_days: number;
  net_pct_on_cost: string;
};

export type MonthlyReportResponse = {
  title_nl: string;
  help_nl: string;
  year: number;
  month: number;
  executive_summary: {
    headline_nl: string;
    net_local_by_currency: Record<string, string>;
    vs_baseline_eur: string | null;
    trade_count: number;
    hit_rate_pct: number;
  };
  open_positions_count: number;
  action_draft_activity: {
    proposed: number;
    user_approved: number;
    submitted: number;
    filled: number;
    dismissed: number;
  };
  verdict_activity: {
    total: number;
    by_decision: Record<string, number>;
  };
  income: {
    capital_gains_local_by_currency: Record<string, string>;
    tob_local_by_currency: Record<string, string>;
    net_local_by_currency: Record<string, string>;
    ytd_net_local_by_currency: Record<string, string>;
  };
  software_performance: {
    hit_rate_pct: number;
    average_hold_days: number;
    confidence_distribution_pct: Record<string, number>;
    proposals_vs_approved: number[];
  };
  realised_trades: MonthlyReportRealisedTrade[];
  notes_nl: string[];
  // V1.2 §CD / GAPS.md P2-11 — operationele events tijdens de maand.
  events: MonthEventOut[];
};

export type MonthEventOut = {
  event_at: string;
  severity: string;
  category: string;
  title_nl: string;
  message_nl: string;
};

// V1.2 §AY — pauze-modus.

export type PauzeStatusResponse = {
  title_nl: string;
  help_nl: string;
  paused: boolean;
  paused_at: string | null;
  summary_nl: string;
};

// V1.2 §BF + §BJ — SELL-suggestie kaartjes voor het dashboard.
export type SellSignalCardResponse = {
  card_id: string;
  ibkr_account_ref: string;
  symbol: string;
  currency: string;
  signal_kind: string; // "take_profit" | "hold_review"
  action: string; // "hold" | "suggest_sell"
  entry_price: string;
  current_price: string;
  quantity: number;
  current_pct_return: string;
  target_pct: string | null;
  target_reached: boolean | null;
  days_held: number | null;
  forecast_id: string | null;
  forecaster_above_target: boolean | null;
  position_in_loss: boolean | null;
  short_term_p50: string | null;
  short_term_horizon_days: number | null;
  short_term_prob_above_pct: string | null;
  expected_net_proceeds_eur: string | null;
  headline_nl: string;
  detail_nl: string;
  first_generated_at: string;
  last_evaluated_at: string;
  dismissed_at: string | null;
  dismissed_reason: string | null;
};

export type SellSignalListResponse = {
  title_nl: string;
  help_nl: string;
  cards: SellSignalCardResponse[];
};

// V1.2 §BH + §BV — Go-live runbook checklist.
export type RunbookItemResponse = {
  code: string;
  group: string;
  label_nl: string;
  status: string; // "ok" | "info" | "warning" | "blocking"
  value_nl: string;
  what_it_means_nl: string;
};

export type RunbookResponse = {
  title_nl: string;
  help_nl: string;
  ready_for_paper_go_live: boolean;
  summary_nl: string;
  items: RunbookItemResponse[];
};

export type SellSignalSweepResponse = {
  started_at: string;
  completed_at: string;
  positions_evaluated: number;
  take_profit_cards_upserted: number;
  hold_review_cards_upserted: number;
  skipped_no_forecast: number;
  skipped_no_position: number;
  error_text: string | null;
};

// V1.2 §AZ — operator-aanpasbaar winstdoel.

export type ProfitTargetResponse = {
  title_nl: string;
  help_nl: string;
  profit_target_pct: string;
  is_doctrine_default: boolean;
  summary_nl: string;
};

// V1.2 §BA — operator-getrackt dividenden register.

export type DividendRow = {
  dividend_event_id: string;
  symbol: string;
  isin: string | null;
  pay_date: string;
  currency_local: string;
  gross_local: string;
  withholding_pct: string;
  withholding_local: string;
  net_local: string;
  country_code: string | null;
  note: string | null;
  rv_shortfall_pct: string;
  rv_shortfall_local: string;
};

export type DividendKpis = {
  gross_by_currency: Record<string, string>;
  withholding_by_currency: Record<string, string>;
  net_by_currency: Record<string, string>;
  count: number;
};

export type DividendListResponse = {
  title_nl: string;
  help_nl: string;
  year: number;
  items: DividendRow[];
  totals: DividendKpis;
  treaty_defaults_pct_by_country: Record<string, string>;
};

export type CreateDividendInput = {
  symbol: string;
  pay_date: string;
  currency_local: string;
  gross_local: string;
  withholding_pct?: string | null;
  country_code?: string | null;
  isin?: string | null;
  note?: string | null;
};

export type DividendMutationResponse = {
  accepted: boolean;
  record_id: string | null;
  explanation_nl: string;
};

export type TobYearToDateResponse = {
  title_nl: string;
  help_nl: string;
  year: number;
  executions_count: number;
  by_currency: Record<string, string>;
  by_security_class: Record<string, Record<string, string>>;
  note_nl: string;
  safe_for_orders: boolean;
};

export type EarningsEventRow = {
  earnings_event_id: string;
  symbol: string;
  ibkr_conid: string | null;
  event_date: string;
  status: string;
  source: string;
  fetched_at: string;
};

export type EarningsUpcomingResponse = {
  title_nl: string;
  help_nl: string;
  window_days: number;
  items: EarningsEventRow[];
};

export type EarningsRefreshResponse = {
  status: string;
  fetched_count: number;
  upserted_count: number;
  symbols_requested: number;
  window_days: number;
  error_text: string | null;
  safe_for_orders: boolean;
};

export type SuggestionsGridItem = {
  suggestion_id: string;
  ibkr_conid: string;
  symbol: string;
  currency: string;
  forecast_id: string | null;
  generated_at: string;
  valid_until: string;
  valid_until_age_minutes: number;
  risk_profile: string;
  has_position: boolean;
  action_label: string;
  action_label_nl: string;
  confidence_label: string;
  confidence_label_nl: string;
  confidence_score: string;
  rationale_nl: string;
  drivers: string[];
  blockers: string[];
  status: string;
  blocking_reason: string | null;
  branch_reason_nl: string | null;
  downgrade_reason_nl: string | null;
  top_driver_nl: string | null;
  blocking_reason_nl: string | null;
  expected_return_pct: string | null;
  prob_gain_pct: string | null;
  diff_status: "nieuw" | "gewijzigd" | "ongewijzigd";
  previous_action_label_nl: string | null;
};

export type SuggestionsGridSection = {
  action_label_nl: string;
  section_title_nl: string;
  item_count: number;
  items: SuggestionsGridItem[];
};

export type SuggestionsGridResponse = {
  status: string;
  status_nl: string;
  help_nl: string;
  risk_profile: string;
  actions_allowed: boolean;
  safe_for_orders: boolean;
  generated_at: string | null;
  section_count: number;
  total_item_count: number;
  new_count: number;
  changed_count: number;
  sections: SuggestionsGridSection[];
};

export type ConnectionSettingsResponse = {
  ibkr_enabled: boolean;
  ibkr_account_id: string | null;
  ibkr_host: string | null;
  ibkr_port: number | null;
  ibkr_client_id: number | null;
  ai_explanation_enabled: boolean;
  claude_ai_explanation_model: string | null;
  claude_ai_budget_monthly_eur: string | null;
  claude_ai_api_key_set: boolean;
  // Settings UI PR L — AI feature toggles.
  ai_explanation_morning_batch_enabled: boolean;
  ai_email_summary_enabled: boolean;
  research_ai_extraction_enabled: boolean;
};

export type ConnectionSettingsUpdateInput = {
  ibkr_enabled: boolean;
  ibkr_account_id: string | null;
  ibkr_host: string | null;
  ibkr_port: number | null;
  ibkr_client_id: number | null;
  ai_explanation_enabled: boolean;
  claude_ai_explanation_model: string | null;
  claude_ai_budget_monthly_eur: string | null;
  // Optional: only sent when the operator types a new key. Omit (do not send)
  // to preserve the previously-stored key.
  claude_ai_api_key?: string;
  // Settings UI PR L — AI feature toggles.
  ai_explanation_morning_batch_enabled: boolean;
  ai_email_summary_enabled: boolean;
  research_ai_extraction_enabled: boolean;
};


export type IbkrSyncStatusResponse = {
  configured: boolean;
  status_nl: string;
  help_nl: string;
  positions_count: number;
  cash_available: boolean;
  open_orders_count: number;
  executions_count: number;
  last_sync_at?: string;
  payload_validation_status?: string;
  payload_validation_status_nl?: string;
  payload_validation_error_count?: number;
  payload_validation_errors?: Array<Record<string, unknown>>;
  payload_validation_help_nl?: string;
  actions_allowed?: boolean;
  order_submission_allowed?: boolean;
  order_modification_allowed?: boolean;
  order_cancellation_allowed?: boolean;
  suggestions_allowed?: boolean;
  can_submit_orders?: boolean;
  safe_for_orders?: boolean;
  blocks_orders?: boolean;
};


export type IbkrPositionSnapshot = {
  sync_run_id: string;
  account_ref: string;
  symbol: string;
  security_type: string;
  currency: string;
  quantity: string;
  average_cost: string | null;
  exchange: string | null;
  timestamp: string;
};

export type IbkrCashSnapshot = {
  sync_run_id: string;
  account_ref: string;
  base_currency: string;
  cash: string;
  available_funds: string | null;
  buying_power: string | null;
  timestamp: string;
};

export type IbkrOpenOrderSnapshot = {
  sync_run_id: string;
  ibkr_order_id: number;
  symbol: string;
  action_side: string | null;
  order_type: string | null;
  quantity: string;
  status: string;
  filled_quantity: string;
  remaining_quantity: string;
  last_status_at: string;
};

export type IbkrExecutionSnapshot = {
  sync_run_id: string;
  execution_id: string;
  symbol: string;
  side: string;
  quantity: string;
  price: string;
  execution_time: string;
  currency: string;
};

export type IbkrStatusResponse = {
  provider: "ibkr";
  enabled: boolean;
  configured: boolean;
  connection_status: string;
  account_mode_status: string;
  expected_environment: string;
  account_id_hint_present: boolean;
  gateway_url_configured: boolean;
  status_check_enabled: boolean;
  can_submit_orders: boolean;
  blocks_orders: boolean;
  status_nl: string;
  message_nl: string;
  help_nl: string;
};

export type SystemEventSummary = {
  system_event_id: string;
  severity: string;
  category: string;
  source_service: string;
  source_component: string;
  event_code: string;
  title_nl: string;
  message_nl: string;
  help_nl: string;
  created_at: string;
  blocks_suggestions: boolean;
  blocks_writes: boolean;
  blocks_ai_explanation: boolean;
  status: string;
  // V1.2 §BZ vervolg — alleen gevuld wanneer de operator het event
  // weggeklikt of gearchiveerd heeft (zie audit-trail timeline).
  resolved_at?: string | null;
  archived_at?: string | null;
};

export type ActiveSystemEventsResponse = {
  events: SystemEventSummary[];
  storage_available?: boolean;
  summary_nl?: string;
  // V1.2 §BZ vervolg — velden uit ``/system/events/active`` +
  // ``/admin/audit/ibkr-config`` voor de audit-trail UI.
  available?: boolean;
  storage_configured?: boolean;
  events_loaded?: boolean;
  active_count?: number;
  status_nl?: string;
  message_nl?: string;
};

export type ErrorLogItem = {
  system_event_id: string;
  created_at: string;
  severity: string;
  category: string;
  source_service: string;
  source_component: string;
  event_code: string;
  title_nl: string;
  message_nl: string;
  technical_summary: string | null;
  stack_trace_redacted: string | null;
  redacted_details_json: Record<string, string> | null;
  status: string;
};

export type ErrorLogResponse = {
  open_count: number;
  errors: ErrorLogItem[];
};

export type ReportErrorInput = {
  message: string;
  component?: string | null;
  stack?: string | null;
  context?: Record<string, string> | null;
};

export type ResearchSourceRecord = {
  library_source_id: string;
  title: string;
  source_kind: string;
  document_type: string;
  source_type: string;
  status: string;
  analysis_status: string;
  classification_status: string;
  extraction_status: string;
  asset_symbol: string | null;
  asset_name: string | null;
  source_credibility_level: string | null;
  prompt_injection_risk_level: string | null;
  explanation_nl: string;
  created_at: string;
  updated_at: string;
  ibkr_conid: string | null;
};


export type ResearchUploadedFileMetadataRecord = {
  library_source_id: string;
  original_file_name: string;
  stored_file_name: string;
  file_size_bytes: number;
  content_type: string | null;
  file_hash_sha256: string;
  uploaded_at: string;
};

export type ResearchExtractTextResponse = {
  status_nl: string;
  message_nl: string;
  help_nl: string;
  library_source_id: string;
  extracted_text_id: string;
  extraction_status: string;
  character_count: number;
  line_count: number;
  text_hash_sha256: string;
  extracted_text_storage_uri: string;
  preview_text_nl: string;
  blocks_suggestions: boolean;
  can_be_used_in_suggestions: boolean;
  record: Record<string, unknown>;
};
export type RequestLogResponse = {
  request_log_id: string;
  correlation_id: string;
  request_family: string;
  request_purpose: string;
  created_at: string;
  completed_at: string | null;
  provider_code: string;
  provider_account_mode: string;
  provider_environment: string;
  source_type: string;
  data_domain: string;
  request_kind: string;
  request_target: string;
  request_status: string;
  safe_for_analysis: boolean;
  safe_for_suggestions: boolean;
  safe_for_action_drafts: boolean;
  status_nl: string;
  help_nl: string;
  audit_help_nl: string;
  chain_completeness_status: string;
  chain_completeness_nl: string;
  missing_chain_links: string[];
};
export type ProviderSourceResponse = {
  provider_source_id: string;
  provider_code: string;
  provider_kind: string;
  data_domain: string;
  source_type: string;
  provider_environment: string;
  provider_account_mode: string;
  created_at: string;
  updated_at: string;
  disabled_at?: string | null;
  disabled_reason?: string | null;
  status_nl: string;
  help_nl: string;
  audit_help_nl: string;
  metadata_quality_status: string;
  metadata_quality_nl: string;
  missing_metadata_fields: string[];
};


export type ValuationInputTrace = Record<string, unknown>;

export type PortfolioValuationReadinessRow = {
  conid: string | null;
  symbol: string | null;
  asset_class: string | null;
  currency: string | null;
  quantity: string;
  average_cost: string | null;
  market_data_status: string;
  valuation_status: string;
  reason_code: string;
  status_nl: string;
  help_nl: string;
  last_market_snapshot_id: string | null;
  market_price: string | null;
  market_price_timestamp: string | null;
  market_value: string | null;
  unrealized_pnl: string | null;
  cost_basis_status: string;
  cost_basis_status_nl: string;
  cost_basis_help_nl: string;
  cost_basis_available: boolean;
  cost_basis: string | null;
  cost_basis_currency: string | null;
  unrealized_pl_status: string;
  unrealized_pl_status_nl: string;
  unrealized_pl_help_nl: string;
  unrealized_pl_available: boolean;
  unrealized_pl: string | null;
  unrealized_pl_currency: string | null;
  unrealized_pl_percent_available: boolean;
  unrealized_pl_percent: string | null;
  converted_unrealized_pl_available: boolean;
  converted_unrealized_pl: string | null;
  missing_cost_basis_inputs: string[];
  missing_pl_inputs: string[];
  cost_basis_input_trace: Record<string, unknown> | null;
  unrealized_pl_input_trace: Record<string, unknown> | null;
};

export type PortfolioValuationReadinessResponse = {
  conversion_total_status: string;
  conversion_total_status_nl: string;
  conversion_total_help_nl: string;
  base_currency: string | null;
  total_market_value_available: boolean;
  total_market_value: string | null;
  total_cash_value_available: boolean;
  total_cash_value: string | null;
  total_portfolio_value_available: boolean;
  total_portfolio_value: string | null;
  converted_totals_available: boolean;
  converted_position_values_available: boolean;
  converted_cash_values_available: boolean;
  missing_total_value_inputs: string[];
  missing_market_data_conids: string[];
  missing_cash_inputs: string[];
  missing_fx_pairs: string[];
  stale_fx_pairs: string[];
  invalid_fx_pairs: string[];
  valuation_input_trace: ValuationInputTrace | null;
  rows: PortfolioValuationReadinessRow[];
  suggestions_allowed?: boolean;
  action_drafts_allowed?: boolean;
  orders_allowed?: boolean;
};

export type AssetForecastResponse = {
  forecast_id: string;
  ibkr_conid: string;
  symbol: string;
  currency: string;
  model_code: string;
  model_version: string;
  horizon_days: number;
  generated_at: string;
  valid_until: string;
  data_points_used: number;
  history_first_bar_date: string | null;
  history_last_bar_date: string | null;
  current_price: string;
  expected_return_pct: string;
  p10_price: string;
  p50_price: string;
  p90_price: string;
  prob_gain: string;
  prob_loss: string;
  prob_loss_gt_5pct: string;
  prob_loss_gt_10pct: string;
  prob_gain_gt_5pct: string;
  prob_gain_gt_10pct: string;
  expected_volatility_annual: string;
  downside_risk_score: string;
  confidence_score: string;
  direction_label: string;
  direction_label_nl: string;
  explanation_nl: string;
  status: string;
  blocking_reason: string | null;
  safe_for_analysis: boolean;
  safe_for_suggestions: boolean;
  safe_for_action_drafts: boolean;
};

export type LatestForecastsResponse = {
  status: string;
  status_nl: string;
  help_nl: string;
  items: AssetForecastResponse[];
  suggestions_allowed?: boolean;
  safe_for_orders?: boolean;
  blocks_orders?: boolean;
};

export type AssetSuggestionResponse = {
  suggestion_id: string;
  ibkr_conid: string;
  symbol: string;
  currency: string;
  forecast_id: string | null;
  model_code: string;
  model_version: string;
  generated_at: string;
  valid_until: string;
  risk_profile: string;
  has_position: boolean;
  action_label: string;
  action_label_nl: string;
  confidence_label: string;
  confidence_label_nl: string;
  confidence_score: string;
  rationale_nl: string;
  drivers: string[];
  blockers: string[];
  status: string;
  blocking_reason: string | null;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
  safe_for_broker_submission: boolean;
};

export type LatestSuggestionsResponse = {
  status: string;
  status_nl: string;
  help_nl: string;
  risk_profile: string;
  items: AssetSuggestionResponse[];
  actions_allowed?: boolean;
  safe_for_action_drafts?: boolean;
  safe_for_orders?: boolean;
  blocks_orders?: boolean;
};

export type AssetDecisionPackageResponse = {
  decision_package_id: string;
  content_hash: string;
  ibkr_conid: string;
  symbol: string;
  currency: string;
  risk_profile: string;
  generated_at: string;
  valid_until: string;
  position_snapshot_id: string | null;
  position_quantity: string | null;
  position_average_cost: string | null;
  cash_snapshot_id: string | null;
  cash_base_currency: string | null;
  cash_amount: string | null;
  market_snapshot_id: string | null;
  market_last_price: string | null;
  market_freshness_status: string | null;
  market_provider_code: string | null;
  market_provider_as_of: string | null;
  fx_pair: string | null;
  fx_rate: string | null;
  fx_freshness_status: string | null;
  forecast_id: string | null;
  forecast_model_code: string | null;
  forecast_model_version: string | null;
  forecast_horizon_days: number | null;
  forecast_p10_price: string | null;
  forecast_p50_price: string | null;
  forecast_p90_price: string | null;
  forecast_prob_gain: string | null;
  forecast_prob_loss: string | null;
  forecast_expected_return_pct: string | null;
  forecast_expected_volatility_annual: string | null;
  forecast_downside_risk_score: string | null;
  forecast_confidence_score: string | null;
  suggestion_id: string | null;
  suggestion_model_code: string | null;
  suggestion_action_label: string;
  suggestion_action_label_nl: string;
  suggestion_confidence_label: string;
  suggestion_confidence_label_nl: string;
  suggestion_status: string;
  has_position: boolean;
  gate_outcomes: string[];
  evidence_links: string[];
  audit_links: string[];
  rationale_nl: string;
  explanation_nl: string;
  status: string;
  blocking_reason: string | null;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
  safe_for_broker_submission: boolean;
  research_evidence_count: number;
  research_credibility_summary: string | null;
  research_freshness_status: string | null;
  research_blocking_reason: string | null;
  research_snippet_nl: string | null;
};

export type LatestDecisionPackagesResponse = {
  status: string;
  status_nl?: string;
  help_nl: string;
  items: AssetDecisionPackageResponse[];
  safe_for_action_drafts?: boolean;
  safe_for_orders?: boolean;
  safe_for_broker_submission?: boolean;
  blocks_orders?: boolean;
};

export type DecisionPackageExplanationResponse = {
  explanation_id: string;
  decision_package_id: string;
  decision_package_content_hash: string;
  ibkr_conid: string;
  symbol: string;
  model_provider_code: string;
  model_name: string;
  model_version: string;
  input_evidence_hash: string;
  output_text_hash: string;
  explanation_nl: string;
  risk_disclaimer_nl: string;
  status: string;
  blocking_reason: string | null;
  hallucinated_numbers: string[];
  generated_at: string;
  safe_for_self_learning: boolean;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type DecisionPackageExplanationRunResponse = {
  status: string;
  status_nl?: string;
  help_nl?: string;
  reason?: string;
  requested_at?: string;
  completed_at?: string;
  explanation_id: string | null;
  blocking_reason: string | null;
  hallucinated_numbers: string[];
  explanation: DecisionPackageExplanationResponse | null;
  safe_for_self_learning?: boolean;
  safe_for_action_drafts?: boolean;
  safe_for_orders?: boolean;
};

export type DecisionPackageExplanationReadResponse = {
  status: string;
  status_nl?: string;
  help_nl: string;
  item: DecisionPackageExplanationResponse | null;
  safe_for_self_learning?: boolean;
  safe_for_action_drafts?: boolean;
  safe_for_orders?: boolean;
};

export type BriefingAlertResponse = {
  alert_id: string;
  alert_kind: string;
  severity: string;
  reference_kind: string | null;
  reference_id: string | null;
  title_nl: string;
  body_nl: string;
  acknowledged_at: string | null;
  linked_at: string;
};

export type DailyBriefingResponse = {
  briefing_id: string;
  briefing_date: string;
  generated_at: string;
  lookback_started_at: string;
  position_count: number;
  base_currency: string | null;
  total_position_value: string | null;
  cash_total: string | null;
  fx_freshness_status: string | null;
  new_suggestion_count: number;
  new_decision_package_count: number;
  new_action_draft_count: number;
  diary_outcomes_closed_count: number;
  critical_event_count: number;
  alert_count: number;
  summary_nl: string;
  help_nl: string;
  status: string;
  blocking_reason: string | null;
  alerts: BriefingAlertResponse[];
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type SchedulerJobResponse = {
  job_id: string;
  job_name: string;
  cron_expression: string;
  next_run_at: string | null;
};

export type SchedulerJobsResponse = {
  status: string;
  status_nl: string;
  help_nl: string;
  scheduler_enabled: boolean;
  scheduler_timezone: string;
  scheduler_daily_briefing_cron: string;
  items: SchedulerJobResponse[];
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type SchedulerRunResponse = {
  run_id: string;
  job_name: string;
  scheduled_at: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  error_text: string | null;
  triggered_by: string;
};

export type LatestSchedulerRunResponse = {
  status: string;
  status_nl?: string;
  help_nl: string;
  item: SchedulerRunResponse | null;
  safe_for_action_drafts?: boolean;
  safe_for_orders?: boolean;
};

export type RecentSchedulerRunsResponse = {
  status: string;
  status_nl?: string;
  help_nl: string;
  limit: number;
  items: SchedulerRunResponse[];
  safe_for_action_drafts?: boolean;
  safe_for_orders?: boolean;
};

export type IbkrAccountModeResponse = {
  status: string;
  mode: string;
  display_label: string;
  expected_environment: string;
  detected_source?: string;
  hint_account_id_masked?: string | null;
  actual_account_id_masked?: string | null;
  hint_mismatch?: boolean;
  hint_mismatch_nl?: string | null;
  help_nl: string;
  safe_for_orders: boolean;
  blocks_orders: boolean;
};

export type IbkrConnectionStatusResponse = {
  connected: boolean;
  account_id: string | null;
  account_mode: "paper" | "live" | "unknown";
  verified_at: string | null;
  error: string | null;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type IbkrConnectionAuditEntry = {
  id: string;
  event_at: string;
  ibkr_account_id: string | null;
  event_type: string;
  account_mode_detected: string | null;
  details_json: string | null;
  connection_id: string | null;
};

export type IbkrConnectionAuditResponse = {
  items: IbkrConnectionAuditEntry[];
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type IbkrPositionLatestRow = {
  ibkr_account_id: string | null;
  conid: string | null;
  symbol: string;
  exchange: string | null;
  primary_exchange: string | null;
  currency: string;
  security_type: string;
  quantity: string | null;
  avg_cost: string | null;
  market_price: string | null;
  market_value: string | null;
  unrealized_pnl: string | null;
  as_of: string | null;
};

export type IbkrPositionsLatestResponse = {
  items: IbkrPositionLatestRow[];
  sync_run_id: string | null;
  as_of: string | null;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type IbkrCashLatestRow = {
  ibkr_account_id: string | null;
  currency: string;
  cash: string | null;
  available_funds: string | null;
  buying_power: string | null;
  net_liquidation_value: string | null;
  total_cash_value: string | null;
  as_of: string | null;
};

export type IbkrCashLatestResponse = {
  items: IbkrCashLatestRow[];
  sync_run_id: string | null;
  as_of: string | null;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type WatchlistConfirmationStateResponse = {
  account_id: string | null;
  state: "unconfirmed" | "confirmed" | "no_account_configured";
  banner_text: string | null;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type WatchlistConfirmResponse = {
  state: "confirmed";
  confirmed_at: string;
  row_count: number;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type ColdStartWatchlistItem = {
  watchlist_item_id: string;
  symbol: string;
  name: string | null;
  exchange: string | null;
  currency: string | null;
  security_type: string | null;
};

export type ColdStartWatchlistResponse = {
  items: ColdStartWatchlistItem[];
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type MarketDataLatestSnapshotResponse = {
  ibkr_conid: string;
  symbol: string;
  exchange: string | null;
  as_of_date: string;
  close_local: string;
  currency_local: string;
  close_eur: string | null;
  fx_rate_used: string | null;
  fx_rate_as_of: string | null;
  freshness: "fresh" | "stale" | "unavailable";
  provider: string;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type MarketDataByAccountRow = {
  ibkr_conid: string;
  symbol: string;
  exchange: string | null;
  as_of_date: string;
  close_local: string;
  currency_local: string;
  close_eur: string | null;
  freshness: "fresh" | "stale" | "unavailable";
};

export type MarketDataByAccountResponse = {
  account_id: string | null;
  items: MarketDataByAccountRow[];
  fetched_via: string | null;
  as_of_date: string | null;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type ForecastLabel =
  | "Kopen"
  | "Verminderen"
  | "Verkopen"
  | "Houden"
  | "Bekijken"
  | "Geblokkeerd";

export type ForecastConfidenceLevel = "Laag" | "Gemiddeld" | "Hoog";

export type PerAssetCoverage = {
  forecasts_evaluated: number;
  hit_rate_within_band: string | null;
  sufficient_history: boolean;
};

export type ForecastLatestResponse = {
  conid: string;
  generated_at: string;
  forecast_valid_until: string;
  horizon_trading_days: number;
  method: string;
  current_price_local: string;
  currency_local: string;
  p10_log_return: string;
  p50_log_return: string;
  p90_log_return: string;
  p10_price_local: string;
  p50_price_local: string;
  p90_price_local: string;
  p10_price_eur: string | null;
  p50_price_eur: string | null;
  p90_price_eur: string | null;
  prob_positive: string;
  prob_loss_gt_5pct: string;
  expected_volatility_annualized: string;
  confidence_level: ForecastConfidenceLevel;
  label: ForecastLabel;
  block_reason: string | null;
  per_asset_coverage: PerAssetCoverage;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type ForecastDaySummaryResponse = {
  account_id: string | null;
  as_of_date: string;
  total_forecasts: number;
  total_blocked: number;
  label_counts: Partial<Record<ForecastLabel, number>>;
  block_reasons: Record<string, number>;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type DecisionPackageGateOutcome = {
  gate_name: string;
  passed: boolean;
  reason_nl: string;
};

export type DecisionPackageEvidenceReference = {
  source_id: string;
  source_type: string;
  claim_summary: string;
};

export type DecisionPackageResponse = {
  decision_package_id: string;
  forecast_run_id: string;
  composed_at: string;
  valid_until: string;
  ibkr_account_id: string;
  conid: string;
  symbol: string;
  exchange: string | null;
  currency_local: string;
  asset_class: string | null;
  user_holds_position: boolean;
  held_quantity: string | null;
  held_avg_cost_local: string | null;
  current_price_local: string;
  current_price_eur: string;
  as_of_market_data_ts: string;
  freshness_state: "fresh" | "stale" | "unavailable";
  data_age_trading_days: number;
  forecast_method: string;
  p10_log_return: string;
  p50_log_return: string;
  p90_log_return: string;
  p10_price_eur: string;
  p50_price_eur: string;
  p90_price_eur: string;
  prob_positive: string;
  prob_loss_gt_5pct: string;
  expected_volatility_annualized: string;
  forecast_confidence_level: ForecastConfidenceLevel;
  suggested_action_label:
    | "Kopen"
    | "Verminderen"
    | "Verkopen"
    | "Houden"
    | "Bekijken";
  block_reason: string | null;
  gate_outcomes: DecisionPackageGateOutcome[];
  evidence_references: DecisionPackageEvidenceReference[];
  deterministic_dutch_explanation: string;
  audit_trail_hash: string;
  previous_package_hash: string | null;
  // V1.2 §BK / §BL — CLAUDE.md §9 enrichment velden. Allemaal nullable
  // (null wanneer storage geen rij heeft).
  sector: string | null;
  market_cap_eur: string | null;
  pe_ratio: string | null;
  momentum_6m_pct: string | null;
  momentum_12m_pct: string | null;
  dividend_yield_pct: string | null;
  next_earnings_date: string | null;
  next_earnings_status: string | null;
  expected_dividend_gross_local: string | null;
  expected_dividend_currency: string | null;
  safe_for_action_drafts: false;
  safe_for_orders: false;
};

export type DecisionPackageChainResponse = {
  ibkr_account_id: string;
  conid: string;
  packages: DecisionPackageResponse[];
  safe_for_action_drafts: false;
  safe_for_orders: false;
};

// ---------------------------------------------------------------------
// Task 133 — Action Draft (user-facing To-Do tier).
// ---------------------------------------------------------------------

export type ActionDraftStatus =
  // Task 133 user-facing statuses.
  | "proposed"
  | "edited"
  | "user_approved"
  | "dismissed"
  | "deleted"
  | "superseded"
  // Task 134 IBKR lifecycle statuses.
  | "submitted"
  | "accepted"
  | "working"
  | "filled"
  | "partially_filled"
  | "cancelled"
  | "rejected"
  | "pending_cancellation"
  | "awaiting_reply_timeout";

export type ActionDraftPaperSubmissionResponse = {
  status: string;
  status_nl: string;
  help_nl: string;
  submission_id: string | null;
  state: string | null;
  ibkr_order_id: number | null;
  ibkr_perm_id: number | null;
  ibkr_status_text: string | null;
  blocking_reason: string | null;
  actions_allowed: boolean;
  order_submission_allowed: boolean;
  order_modification_allowed: boolean;
  order_cancellation_allowed: boolean;
  safe_for_submission: boolean;
  safe_for_orders: boolean;
  safe_for_broker_submission: boolean;
  blocks_orders: boolean;
};

export type ActionDraftResponse = {
  action_draft_id: string;
  decision_package_id: string | null;
  forecast_run_id: string | null;
  created_at: string;
  created_by: "user" | "system";
  ibkr_account_id: string;
  conid: string;
  symbol: string;
  exchange: string;
  currency_local: string;
  side: "BUY" | "SELL";
  quantity: string;
  order_type: "LMT";
  limit_price_local: string;
  time_in_force: "DAY";
  notional_local: string;
  notional_eur: string;
  fx_rate_at_creation: string;
  usable_cash_eur_at_creation: string;
  held_quantity_at_creation: string | null;
  status: ActionDraftStatus;
  last_edited_at: string | null;
  user_approved_at: string | null;
  dismissed_at: string | null;
  deleted_at: string | null;
  dismissed_reason: string | null;
  user_note: string | null;
  superseded_by_decision_package_id: string | null;
  audit_trail_hash: string;
  previous_draft_hash: string | null;
  safe_for_submission: false;
  // Task 134 lifecycle fields.
  submission_block_reason: string | null;
  submission_started_at: string | null;
  terminal_state_at: string | null;
};

// ---------------------------------------------------------------------
// Task 134c — IBKR submission lifecycle responses.
// ---------------------------------------------------------------------

export type IbkrSubmissionAuditRow = {
  id: number | null;
  action_draft_id: string;
  submitted_at: string;
  sent_to_account_id: string;
  sent_account_mode: "paper" | "live";
  ibkr_perm_id: number | null;
  ibkr_order_id: number | null;
  contract_json: Record<string, unknown>;
  order_json: Record<string, unknown>;
  gateway_session_id: string;
  result: "placed" | "rejected_at_send" | "connection_lost";
  error_class: string | null;
  error_message_dutch: string | null;
};

export type IbkrSubmissionAuditListResponse = {
  ibkr_account_id: string;
  rows: IbkrSubmissionAuditRow[];
};

export type IbkrSubmissionLifecycleEvent = {
  id: number | null;
  action_draft_id: string;
  event_at: string;
  ibkr_perm_id: number;
  event_type:
    | "status_change"
    | "fill"
    | "commission_report"
    | "cancellation_request";
  from_status: string | null;
  to_status: string | null;
  ibkr_raw_status: string | null;
  fill_price_local: string | null;
  fill_quantity: string | null;
  commission: string | null;
  commission_currency: string | null;
  raw_callback_json: Record<string, unknown>;
};

export type IbkrSubmissionLifecycleListResponse = {
  action_draft_id: string;
  events: IbkrSubmissionLifecycleEvent[];
};

export type IbkrExecutionRow = {
  id: number | null;
  ibkr_exec_id: string;
  ibkr_perm_id: number;
  action_draft_id: string;
  account_id: string;
  conid: string;
  side: "BUY" | "SELL";
  fill_price_local: string;
  fill_quantity: string;
  fill_time: string;
  commission: string;
  commission_currency: string;
  exchange: string;
};

export type IbkrExecutionListResponse = {
  account_id: string;
  conid: string;
  executions: IbkrExecutionRow[];
};

// Task 135b — IBKR reconciliation API types.

export type ReconciliationPassName =
  | "orphaned_execution"
  | "stale_in_flight"
  | "timeout_recovery";

export type ReconciliationMode =
  | "completed"
  | "skipped_locked"
  | "skipped_disconnected"
  | "error";

export type ManualReviewReason =
  | "timeout_24h_no_data"
  | "terminal_state_divergence"
  | "unmatched_execution_no_draft";

export type ManualReviewResolutionStatus =
  | "pending"
  | "resolved"
  | "acknowledged";

export type UnmatchedExecutionResolutionStatus =
  | "unresolved"
  | "manually_matched"
  | "ignored";

export type ReconciliationRunResponse = {
  id: number | null;
  reconciliation_run_id: string;
  started_at: string;
  completed_at: string | null;
  account_id: string;
  pass_a_orphaned_count: number;
  pass_b_stale_count: number;
  pass_c_timeout_count: number;
  divergences_found: number;
  mode_detected: ReconciliationMode;
  error_details_json: Record<string, unknown> | null;
};

export type ReconciliationRunListResponse = {
  ibkr_account_id: string;
  runs: ReconciliationRunResponse[];
};

export type ReconciliationStatusResponse = {
  ibkr_account_id: string;
  latest_run: ReconciliationRunResponse | null;
  drafts_healed_last_24h: number;
  pending_manual_review_count: number;
  unresolved_unmatched_count: number;
};

export type ReconciliationAuditRow = {
  id: number | null;
  reconciliation_run_id: string;
  action_draft_id: string | null;
  event_at: string;
  pass_name: ReconciliationPassName;
  divergence_type: string;
  before_status: string | null;
  after_status: string | null;
  ibkr_evidence_json: Record<string, unknown>;
  notes_dutch: string | null;
};

export type ReconciliationAuditListResponse = {
  ibkr_account_id: string;
  rows: ReconciliationAuditRow[];
};

export type ManualReviewResponse = {
  id: number | null;
  flagged_at: string;
  action_draft_id: string;
  reason: ManualReviewReason;
  details_dutch: string;
  resolution_status: ManualReviewResolutionStatus;
  resolved_at: string | null;
  resolution_note: string | null;
};

export type ManualReviewListResponse = {
  ibkr_account_id: string;
  rows: ManualReviewResponse[];
};

export type UnmatchedExecutionRow = {
  id: number | null;
  event_at: string;
  ibkr_perm_id: number;
  ibkr_exec_id: string;
  account_id: string;
  conid: string;
  side: "BUY" | "SELL";
  fill_price_local: string;
  fill_quantity: string;
  fill_time: string;
  raw_execution_json: Record<string, unknown>;
  resolution_status: UnmatchedExecutionResolutionStatus;
};

export type UnmatchedExecutionListResponse = {
  ibkr_account_id: string;
  rows: UnmatchedExecutionRow[];
};

export type ActiveDraftListResponse = {
  ibkr_account_id: string;
  drafts: ActionDraftResponse[];
};

export type HistoriekDraftListResponse = {
  ibkr_account_id: string;
  drafts: ActionDraftResponse[];
};

export type ActionDraftListResponse = {
  ibkr_account_id: string;
  drafts: ActionDraftResponse[];
  safe_for_submission: false;
};

export type CreateActionDraftInput = {
  decision_package_id?: string;
  user_note?: string;
  ibkr_account_id?: string;
  conid?: string;
  symbol?: string;
  exchange?: string;
  currency_local?: string;
  side?: "BUY" | "SELL";
  quantity?: string;
  limit_price_local?: string;
};

export type PatchActionDraftInput = {
  quantity?: string;
  limit_price_local?: string;
  user_note?: string;
};

export type ForecastByAccountRow = {
  conid: string;
  label: ForecastLabel;
  confidence_level: ForecastConfidenceLevel;
  generated_at: string;
  p50_log_return: string;
  prob_positive: string;
  user_holds_position: boolean;
  // #1 + #6 — forecast horizon + prediction interval, surfaced so the UI
  // can show "we expect X to Y with Z probability" instead of just a
  // Hoog/Middel/Laag confidence label.
  horizon_trading_days: number;
  p10_log_return: string;
  p90_log_return: string;
};

export type ForecastByAccountResponse = {
  account_id: string | null;
  items: ForecastByAccountRow[];
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type CalibrationCoverageResponse = {
  window_days: number;
  forecasts_evaluated: number;
  hit_rate_within_band: string | null;
  p10_p90_coverage_percent: string | null;
  mean_realized_minus_p50: string | null;
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type ProviderCallRow = {
  audit_id: string;
  called_at: string;
  provider: string;
  endpoint: string;
  response_status: number | null;
  duration_ms: number | null;
  error_class: string | null;
  account_id: string | null;
  triggered_by_run_id: string | null;
};

export type ProviderCallsResponse = {
  items: ProviderCallRow[];
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

// Generated from the OpenAPI schema (single source of truth). The former
// hand-written shape is now derived via ApiSchema — drift is caught by tsc.
export type SchedulerV127StatusResponse =
  ApiSchema<"SchedulerV127StatusResponse">;

export type ScheduledRunAuditRow = {
  run_id: string;
  run_at: string;
  run_type: string;
  ibkr_account_id: string | null;
  mode_detected: string;
  duration_ms: number | null;
  outcome: string;
  error_details_json: string | null;
  next_scheduled_at: string | null;
};

export type SchedulerV127RunsResponse = {
  items: ScheduledRunAuditRow[];
  safe_for_action_drafts: boolean;
  safe_for_orders: boolean;
};

export type DailyBriefingRunResponse = {
  status: string;
  status_nl?: string;
  help_nl?: string;
  reason?: string;
  briefing_id: string | null;
  alert_count: number;
  safe_for_action_drafts?: boolean;
  safe_for_orders?: boolean;
};

export type DailyBriefingReadResponse = {
  status: string;
  status_nl?: string;
  help_nl: string;
  item: DailyBriefingResponse | null;
  safe_for_action_drafts?: boolean;
  safe_for_orders?: boolean;
};

export type AssetActionDraftResponse = {
  draft_id: string;
  decision_package_id: string;
  decision_package_content_hash: string;
  ibkr_conid: string;
  symbol: string;
  currency: string;
  exchange: string | null;
  primary_exchange: string | null;
  account_mode: string;
  expected_account_mode: string;
  action_side: string;
  order_type: string;
  tif: string;
  quantity: string;
  limit_price: string;
  estimated_order_value: string | null;
  estimated_cash_before: string | null;
  estimated_cash_after: string | null;
  estimated_position_quantity_before: string | null;
  estimated_position_quantity_after: string | null;
  estimated_position_value_after: string | null;
  estimated_portfolio_weight_after_pct: string | null;
  estimated_concentration_impact_pct: string | null;
  orderimpact_base_currency: string | null;
  estimated_belgian_tob: string | null;
  belgian_tob_security_class: string | null;
  source_action_label: string;
  source_action_label_nl: string;
  status: string;
  dry_run_status: string;
  dry_run_failures: string[];
  blocking_reason: string | null;
  rationale_nl: string;
  explanation_nl: string;
  created_at: string;
  updated_at: string;
  safe_for_submission: boolean;
  safe_for_orders: boolean;
  safe_for_broker_submission: boolean;
};

export type LatestActionDraftsResponse = {
  status: string;
  status_nl?: string;
  help_nl: string;
  items: AssetActionDraftResponse[];
  actions_allowed?: boolean;
  safe_for_submission?: boolean;
  safe_for_orders?: boolean;
  safe_for_broker_submission?: boolean;
  blocks_orders?: boolean;
};

export type FreshnessAuditResponse = {
  freshness_audit_id: string;
  request_log_id: string | null;
  provider_source_id: string | null;
  data_domain: string;
  audit_scope: string;
  freshness_status: string;
  reason_code: string | null;
  evaluated_at: string;
  expected_max_age_seconds: number | null;
  observed_age_seconds: number | null;
  source_timestamp: string | null;
  expires_at: string | null;
  safe_for_analysis: boolean;
  safe_for_suggestions: boolean;
  safe_for_action_drafts: boolean;
  status_nl: string;
  help_nl: string;
  audit_help_nl: string;
  chain_completeness_status: string;
  chain_completeness_nl: string;
  missing_chain_links: string[];
};
export type RequestLogListResponse = { items: RequestLogResponse[]; total_count:number; chain_complete_count:number; chain_partial_count:number; chain_missing_links_count:number; chain_metadata_only_count:number; safe_for_analysis_count:number; safe_for_suggestions_count:number; safe_for_action_drafts_count:number; blocked_for_analysis_count:number; blocked_for_suggestions_count:number; blocked_for_action_drafts_count:number; request_status_counts:Record<string,number>; provider_code_counts:Record<string,number>; data_domain_counts:Record<string,number>; audit_help_nl:string; status_nl: string; help_nl: string };
export type ProviderSourceListResponse = { items: ProviderSourceResponse[]; total_count:number; metadata_complete_count:number; metadata_partial_count:number; metadata_unknown_count:number; provider_kind_counts:Record<string,number>; provider_code_counts:Record<string,number>; data_domain_counts:Record<string,number>; disabled_count:number; active_metadata_count:number; audit_help_nl:string; status_nl: string; help_nl: string };
export type FreshnessAuditListResponse = { items: FreshnessAuditResponse[]; total_count:number; chain_complete_count:number; chain_partial_count:number; chain_missing_links_count:number; chain_metadata_only_count:number; safe_for_analysis_count:number; safe_for_suggestions_count:number; safe_for_action_drafts_count:number; blocked_for_analysis_count:number; blocked_for_suggestions_count:number; blocked_for_action_drafts_count:number; freshness_status_counts:Record<string,number>; reason_code_counts:Record<string,number>; provider_code_counts:Record<string,number>; data_domain_counts:Record<string,number>; audit_help_nl:string; status_nl: string; help_nl: string };
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Direct download URL for the suggestions Markdown export. The backend sets
// Content-Disposition: attachment, so a plain anchor navigation downloads the
// file (and is not subject to CORS, unlike a fetch + Blob read).
export function decisionPackagesExportUrl(): string {
  return `${API_BASE_URL}/decision-packages/export`;
}

async function getJson<T>(path: string): Promise<FetchState<T>> { /* unchanged */
  try { const response = await fetch(`${API_BASE_URL}${path}`, { method: "GET", headers: { "Content-Type": "application/json" }, cache: "no-store" });
    if (!response.ok) return { ok: false, reason: "not_reachable" };
    return { ok: true, data: (await response.json()) as T };
  } catch { return { ok: false, reason: "not_reachable" }; }
}

async function putJson<T>(path: string, body: object): Promise<FetchState<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!response.ok) return { ok: false, reason: "not_reachable" };
    return { ok: true, data: (await response.json()) as T };
  } catch { return { ok: false, reason: "not_reachable" }; }
}

async function postJson<T>(path: string, body?: object): Promise<FetchState<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body ?? {}),
    });
    if (!response.ok) return { ok: false, reason: "not_reachable" };
    return { ok: true, data: (await response.json()) as T };
  } catch {
    return { ok: false, reason: "not_reachable" };
  }
}



async function postFormData<T>(path: string, formData: FormData): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      body: formData,
    });
    const payload = (await response.json().catch(() => ({}))) as { detail?: string } & T;
    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        message: typeof payload.detail === "string" ? payload.detail : "Onbekende fout.",
      };
    }
    return { ok: true, data: payload as T };
  } catch {
    return { ok: false, status: 0, message: "API niet bereikbaar." };
  }
}

async function requestJson<T>(
  path: string,
  method: "GET" | "POST" | "DELETE" | "PUT" | "PATCH",
  body?: object,
): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body:
        method === "POST" || method === "PUT" || method === "PATCH"
          ? JSON.stringify(body ?? {})
          : undefined,
      cache: method === "GET" ? "no-store" : undefined,
    });
    const payload = (await response.json().catch(() => ({}))) as { detail?: string } & T;
    if (!response.ok) return { ok: false, status: response.status, message: typeof payload.detail === "string" ? payload.detail : "Onbekende fout." };
    return { ok: true, data: payload as T };
  } catch {
    return { ok: false, status: 0, message: "API niet bereikbaar." };
  }
}

export const apiClient = {
  getSystemStatus: () => getJson<SystemStatusSummary>("/system/status"),
  getSettingsSummary: () => getJson<SettingsSummary>("/settings/summary"),
  getAiUsageSummary: () => getJson<AiUsageSummary>("/usage/ai/summary"),
  getIntegrationsSummary: () => getJson<IntegrationsSummary>("/integrations/summary"),
  getStorageStatus: () => getJson<StorageStatusSummary>("/storage/status"),
  getStorageStatusOnline: () =>
    getJson<OnlineStorageStatusResponse>("/storage/status/online"),
  getApiHealth: () =>
    getJson<{ status: string; service: string }>("/health"),
  getMarketHoursNow: () =>
    getJson<MarketHoursNowResponse>("/markets/hours-now"),
  getClaudeBudgetStatus: () =>
    getJson<ClaudeBudgetStatusResponse>("/claude/budget/status"),
  getNavHistory: (days = 30) =>
    getJson<NavHistoryResponse>(`/portfolio/nav/history?days=${days}`),
  getPredictorPerformance: (lookbackDays = 30) =>
    getJson<PredictorPerformanceResponse>(
      `/predictors/performance?lookback_days=${lookbackDays}`,
    ),
  getTradingSettings: () => getJson<TradingSettingsResponse>("/settings/trading"),
  getIbkrStatus: () => getJson<IbkrStatusResponse>("/broker/ibkr/status"),
  getIbkrSyncStatus: () => getJson<IbkrSyncStatusResponse>("/ibkr/sync/status"),
  getPortfolioValuationReadiness: () => getJson<PortfolioValuationReadinessResponse>("/portfolio/valuation/readiness"),
  getIbkrPositions: () => getJson<{ items: IbkrPositionSnapshot[] }>("/ibkr/portfolio/positions"),
  getIbkrCash: () => getJson<{ items: IbkrCashSnapshot[] }>("/ibkr/account/cash"),
  getIbkrOpenOrders: () => getJson<{ items: IbkrOpenOrderSnapshot[] }>("/ibkr/orders/open"),
  getIbkrExecutions: () => getJson<{ items: IbkrExecutionSnapshot[] }>("/ibkr/executions"),
  getLatestForecasts: () => getJson<LatestForecastsResponse>("/forecasts/latest"),
  runForecastSync: () => postJson<{ status: string }>("/forecasts/compute"),
  getLatestSuggestions: () => getJson<LatestSuggestionsResponse>("/suggestions/latest"),
  runSuggestionsSync: () => postJson<{ status: string }>("/suggestions/compute"),
  getLatestDecisionPackages: () =>
    getJson<LatestDecisionPackagesResponse>("/decision-packages/latest"),
  runDecisionPackagesSync: () => postJson<{ status: string }>("/decision-packages/compute"),
  runDecisionPackageExplanation: (decisionPackageId: string) =>
    postJson<DecisionPackageExplanationRunResponse>(
      `/decision-packages/${decisionPackageId}/explanation`,
    ),
  getDecisionPackageExplanation: (decisionPackageId: string) =>
    getJson<DecisionPackageExplanationReadResponse>(
      `/decision-packages/${decisionPackageId}/explanation`,
    ),
  getLatestActionDrafts: () =>
    getJson<LatestActionDraftsResponse>("/action-drafts/latest"),
  runActionDraftsSync: () => postJson<{ status: string }>("/action-drafts/compute"),
  runDailyBriefing: () =>
    postJson<DailyBriefingRunResponse>("/briefings/daily/compute"),
  getLatestDailyBriefing: () =>
    getJson<DailyBriefingReadResponse>("/briefings/daily/latest"),
  getSchedulerJobs: () => getJson<SchedulerJobsResponse>("/scheduler/jobs"),
  getLatestSchedulerRun: () =>
    getJson<LatestSchedulerRunResponse>("/scheduler/runs/latest"),
  getRecentSchedulerRuns: (limit = 20) =>
    getJson<RecentSchedulerRunsResponse>(
      `/scheduler/runs?limit=${Math.max(1, Math.min(200, limit))}`,
    ),
  getIbkrAccountMode: () => getJson<IbkrAccountModeResponse>("/ibkr/account/mode"),
  getIbkrConnectionStatus: () =>
    getJson<IbkrConnectionStatusResponse>("/ibkr/connection/status"),
  getIbkrConnectionAudit: (limit = 20) =>
    getJson<IbkrConnectionAuditResponse>(
      `/ibkr/connection/audit?limit=${limit}`,
    ),
  getIbkrSyncPositionsLatest: () =>
    getJson<IbkrPositionsLatestResponse>("/ibkr/sync/positions/latest"),
  getIbkrSyncCashLatest: () =>
    getJson<IbkrCashLatestResponse>("/ibkr/sync/cash/latest"),
  getWatchlistConfirmationState: () =>
    getJson<WatchlistConfirmationStateResponse>(
      "/watchlist/confirmation-state",
    ),
  getColdStartWatchlistItems: () =>
    getJson<ColdStartWatchlistResponse>("/watchlist/cold-start-items"),
  confirmWatchlist: (phrase: string) =>
    requestJson<WatchlistConfirmResponse>(
      "/watchlist/confirm",
      "POST",
      { confirmation_phrase: phrase },
    ),
  deleteColdStartWatchlistItem: (watchlistItemId: string) =>
    requestJson<{ archived: boolean }>(
      `/watchlist/cold-start-items/${encodeURIComponent(watchlistItemId)}`,
      "DELETE",
    ),
  getMarketDataByAccount: (accountId?: string) =>
    getJson<MarketDataByAccountResponse>(
      accountId
        ? `/market-data/eod/snapshots/by-account?account_id=${encodeURIComponent(accountId)}`
        : "/market-data/eod/snapshots/by-account",
    ),
  getMarketDataProviderCalls: (limit = 20) =>
    getJson<ProviderCallsResponse>(
      `/market-data/provider-calls?limit=${limit}`,
    ),
  getForecastLatest: (conid: string) =>
    getJson<ForecastLatestResponse>(
      `/forecast/latest?conid=${encodeURIComponent(conid)}`,
    ),
  getForecastsByAccount: (accountId?: string) =>
    getJson<ForecastByAccountResponse>(
      accountId
        ? `/forecast/by-account?account_id=${encodeURIComponent(accountId)}`
        : "/forecast/by-account",
    ),
  getCalibrationCoverage: (windowDays = 90) =>
    getJson<CalibrationCoverageResponse>(
      `/calibration/coverage?window_days=${windowDays}`,
    ),
  getForecastDaySummary: (params?: { accountId?: string; asOfDate?: string }) => {
    const search = new URLSearchParams();
    if (params?.accountId) search.set("account_id", params.accountId);
    if (params?.asOfDate) search.set("as_of_date", params.asOfDate);
    const qs = search.toString();
    return getJson<ForecastDaySummaryResponse>(
      qs ? `/forecast/day-summary?${qs}` : "/forecast/day-summary",
    );
  },
  getDecisionPackage: (id: string) =>
    getJson<DecisionPackageResponse>(
      `/decision-package/${encodeURIComponent(id)}`,
    ),
  getLatestDecisionPackage: (params: { conid: string; accountId?: string }) => {
    const search = new URLSearchParams();
    search.set("conid", params.conid);
    if (params.accountId) {
      search.set("account_id", params.accountId);
    }
    return getJson<DecisionPackageResponse>(
      `/decision-package/latest?${search.toString()}`,
    );
  },
  getDecisionPackageChain: (params: {
    conid: string;
    accountId: string;
    limit?: number;
  }) => {
    const search = new URLSearchParams();
    search.set("conid", params.conid);
    search.set("account_id", params.accountId);
    if (params.limit !== undefined) search.set("limit", String(params.limit));
    return getJson<DecisionPackageChainResponse>(
      `/decision-package/chain?${search.toString()}`,
    );
  },
  // -------------------------------------------------------------------
  // Task 133 — Action Draft operations.
  // -------------------------------------------------------------------
  getActionDraftsTeKeuren: (accountId?: string) => {
    const qs = accountId
      ? `?account_id=${encodeURIComponent(accountId)}`
      : "";
    return getJson<ActionDraftListResponse>(`/action-draft/te-keuren${qs}`);
  },
  getActionDraft: (id: string) =>
    getJson<ActionDraftResponse>(`/action-draft/${encodeURIComponent(id)}`),
  createActionDraft: (payload: CreateActionDraftInput) =>
    requestJson<ActionDraftResponse>("/action-draft", "POST", payload),
  patchActionDraft: (id: string, payload: PatchActionDraftInput) =>
    requestJson<ActionDraftResponse>(
      `/action-draft/${encodeURIComponent(id)}`,
      "PATCH",
      payload,
    ),
  approveActionDraft: (id: string) =>
    requestJson<ActionDraftResponse>(
      `/action-draft/${encodeURIComponent(id)}/approve`,
      "POST",
    ),
  submitActionDraftToPaper: (id: string) =>
    requestJson<ActionDraftPaperSubmissionResponse>(
      `/action-drafts/${encodeURIComponent(id)}/submit-to-ibkr-paper`,
      "POST",
    ),
  dismissActionDraft: (id: string, reason?: string) =>
    requestJson<ActionDraftResponse>(
      `/action-draft/${encodeURIComponent(id)}/dismiss`,
      "POST",
      reason ? { reason } : {},
    ),
  deleteActionDraft: (id: string) =>
    requestJson<ActionDraftResponse>(
      `/action-draft/${encodeURIComponent(id)}/delete`,
      "POST",
    ),
  // -------------------------------------------------------------------
  // Task 134c — IBKR submission read API + cancel-submitted write.
  // -------------------------------------------------------------------
  cancelSubmittedActionDraft: (id: string) =>
    requestJson<ActionDraftResponse>(
      `/action-draft/${encodeURIComponent(id)}/cancel-submitted`,
      "POST",
    ),
  getIbkrSubmissionAudit: (accountId?: string, limit = 50) => {
    const search = new URLSearchParams();
    if (accountId) search.set("account_id", accountId);
    search.set("limit", String(limit));
    return getJson<IbkrSubmissionAuditListResponse>(
      `/ibkr-submission/audit?${search.toString()}`,
    );
  },
  getIbkrSubmissionLifecycle: (actionDraftId: string) =>
    getJson<IbkrSubmissionLifecycleListResponse>(
      `/ibkr-submission/lifecycle/${encodeURIComponent(actionDraftId)}`,
    ),
  getIbkrSubmissionActive: (accountId?: string) => {
    const qs = accountId
      ? `?account_id=${encodeURIComponent(accountId)}`
      : "";
    return getJson<ActiveDraftListResponse>(
      `/ibkr-submission/active${qs}`,
    );
  },
  getIbkrSubmissionHistoriek: (accountId?: string, limit = 50) => {
    const search = new URLSearchParams();
    if (accountId) search.set("account_id", accountId);
    search.set("limit", String(limit));
    return getJson<HistoriekDraftListResponse>(
      `/ibkr-submission/historiek?${search.toString()}`,
    );
  },
  // Task 134c — per-asset execution history (`GET /ibkr-executions`).
  // Renamed to avoid collision with the legacy ``getIbkrExecutions()``
  // (no-args, hits ``/ibkr/executions`` — Portefeuille's snapshot grid).
  getIbkrExecutionsForAsset: (params: {
    accountId?: string;
    conid: string;
  }) => {
    const search = new URLSearchParams();
    if (params.accountId) search.set("account_id", params.accountId);
    search.set("conid", params.conid);
    return getJson<IbkrExecutionListResponse>(
      `/ibkr-executions?${search.toString()}`,
    );
  },
  // -------------------------------------------------------------------
  // Task 135b — IBKR reconciliation read API + manual-review acknowledge.
  // -------------------------------------------------------------------
  getReconciliationStatus: (accountId?: string) => {
    const qs = accountId
      ? `?account_id=${encodeURIComponent(accountId)}`
      : "";
    return getJson<ReconciliationStatusResponse>(
      `/reconciliation/status${qs}`,
    );
  },
  getReconciliationRuns: (accountId?: string, limit = 50) => {
    const search = new URLSearchParams();
    if (accountId) search.set("account_id", accountId);
    search.set("limit", String(limit));
    return getJson<ReconciliationRunListResponse>(
      `/reconciliation/runs?${search.toString()}`,
    );
  },
  getReconciliationAudit: (accountId?: string, limit = 50) => {
    const search = new URLSearchParams();
    if (accountId) search.set("account_id", accountId);
    search.set("limit", String(limit));
    return getJson<ReconciliationAuditListResponse>(
      `/reconciliation/audit?${search.toString()}`,
    );
  },
  getReconciliationManualReview: (accountId?: string) => {
    const qs = accountId
      ? `?account_id=${encodeURIComponent(accountId)}`
      : "";
    return getJson<ManualReviewListResponse>(
      `/reconciliation/manual-review${qs}`,
    );
  },
  acknowledgeManualReview: (queueId: number, note?: string) => {
    const qs = note ? `?note=${encodeURIComponent(note)}` : "";
    return postJson<ManualReviewResponse>(
      `/reconciliation/manual-review/${queueId}/acknowledge${qs}`,
    );
  },
  getReconciliationUnmatchedExecutions: (accountId?: string) => {
    const qs = accountId
      ? `?account_id=${encodeURIComponent(accountId)}`
      : "";
    return getJson<UnmatchedExecutionListResponse>(
      `/reconciliation/unmatched-executions${qs}`,
    );
  },
  getSchedulerV127Status: () =>
    getJson<SchedulerV127StatusResponse>("/scheduler/v127/status"),
  getSchedulerV127Runs: (limit = 20) =>
    getJson<SchedulerV127RunsResponse>(
      `/scheduler/v127/runs?limit=${limit}`,
    ),
  getRequestAuditRequestLogs: () => getJson<RequestLogListResponse>("/audit/request-logs"),
  getRequestAuditRequestLog: (requestLogId: string) =>
    getJson<RequestLogResponse>(`/audit/request-logs/${encodeURIComponent(requestLogId)}`),
  getRequestAuditProviderSources: () =>
    getJson<ProviderSourceListResponse>("/audit/provider-sources"),
  getRequestAuditProviderSource: (providerSourceId: string) =>
    getJson<ProviderSourceResponse>(
      `/audit/provider-sources/${encodeURIComponent(providerSourceId)}`,
    ),
  getRequestAuditFreshnessAudits: () =>
    getJson<FreshnessAuditListResponse>("/audit/freshness-audits"),
  getRequestAuditFreshnessAudit: (freshnessAuditId: string) =>
    getJson<FreshnessAuditResponse>(
      `/audit/freshness-audits/${encodeURIComponent(freshnessAuditId)}`,
    ),
  runIbkrSync: () => postJson<{ status: string }>("/ibkr/sync/run"),
  updateTradingSettings: (payload: TradingSettingsUpdateInput) => putJson<TradingSettingsResponse>("/settings/trading", payload),
  getRiskLimits: () => getJson<RiskLimitsResponse>("/settings/risk-limits"),
  updateRiskLimits: (payload: RiskLimitsUpdateInput) =>
    putJson<RiskLimitsResponse>("/settings/risk-limits", payload),
  getConnectionSettings: () =>
    getJson<ConnectionSettingsResponse>("/settings/connection"),
  updateConnectionSettings: (payload: ConnectionSettingsUpdateInput) =>
    putJson<ConnectionSettingsResponse>("/settings/connection", payload),
  getUniverseScanSettings: () =>
    getJson<UniverseScanSettingsResponse>("/settings/universe-scan"),
  updateUniverseScanSettings: (payload: { selected_codes: string[] }) =>
    putJson<UniverseScanSettingsResponse>("/settings/universe-scan", payload),
  getOrderPolicySettings: () =>
    getJson<OrderPolicySettingsResponse>("/settings/order-policy"),
  updateOrderPolicySettings: (payload: OrderPolicySettingsUpdateInput) =>
    putJson<OrderPolicySettingsResponse>("/settings/order-policy", payload),
  getSchedulerSettings: () =>
    getJson<SchedulerSettingsResponse>("/settings/scheduler"),
  updateSchedulerSettings: (payload: SchedulerSettingsUpdateInput) =>
    putJson<SchedulerSettingsResponse>("/settings/scheduler", payload),
  getDataWindowSettings: () =>
    getJson<DataWindowSettingsResponse>("/settings/data-windows"),
  updateDataWindowSettings: (payload: DataWindowSettingsUpdateInput) =>
    putJson<DataWindowSettingsResponse>("/settings/data-windows", payload),
  getWorkerSweepSettings: () =>
    getJson<WorkerSweepSettingsResponse>("/settings/worker-sweeps"),
  updateWorkerSweepSettings: (payload: WorkerSweepSettingsUpdateInput) =>
    putJson<WorkerSweepSettingsResponse>("/settings/worker-sweeps", payload),
  getAdvancedSettings: () =>
    getJson<AdvancedSettingsResponse>("/settings/advanced"),
  updateAdvancedSettings: (payload: AdvancedSettingsUpdateInput) =>
    putJson<AdvancedSettingsResponse>("/settings/advanced", payload),
  getForecastMarketSettings: () =>
    getJson<ForecastMarketSettingsResponse>("/settings/forecast-market"),
  updateForecastMarketSettings: (
    payload: ForecastMarketSettingsUpdateInput,
  ) =>
    putJson<ForecastMarketSettingsResponse>(
      "/settings/forecast-market",
      payload,
    ),
  getExecutionGateSettings: () =>
    getJson<ExecutionGateSettingsResponse>("/settings/execution-gates"),
  updateExecutionGateSettings: (
    payload: ExecutionGateSettingsUpdateInput,
  ) =>
    putJson<ExecutionGateSettingsResponse>(
      "/settings/execution-gates",
      payload,
    ),
  getPredictorTuningSettings: () =>
    getJson<PredictorTuningSettingsResponse>("/settings/predictor-tuning"),
  updatePredictorTuningSettings: (
    payload: PredictorTuningSettingsUpdateInput,
  ) =>
    putJson<PredictorTuningSettingsResponse>(
      "/settings/predictor-tuning",
      payload,
    ),
  getSuggestionsGrid: () =>
    getJson<SuggestionsGridResponse>("/suggestions/grid"),
  getDigestToday: () => getJson<DigestTodayResponse>("/digests/today"),
  getOrchestratorVerdictsSummary: () =>
    getJson<OrchestratorVerdictsSummaryResponse>(
      "/orchestrator-verdicts/today",
    ),
  listOrchestratorVerdicts: (params?: { limit?: number }) =>
    getJson<OrchestratorVerdictsListResponse>(
      `/orchestrator-verdicts${
        params?.limit ? `?limit=${params.limit}` : ""
      }`,
    ),
  listFavorieten: (params?: { account_id?: string }) =>
    getJson<WatchlistFavoritesResponse>(
      `/watchlist-preferences/favorieten${
        params?.account_id
          ? `?account_id=${encodeURIComponent(params.account_id)}`
          : ""
      }`,
    ),
  listUitsluitingen: (params?: { account_id?: string }) =>
    getJson<WatchlistExclusionsResponse>(
      `/watchlist-preferences/uitsluitingen${
        params?.account_id
          ? `?account_id=${encodeURIComponent(params.account_id)}`
          : ""
      }`,
    ),
  saveWatchlistPreference: (payload: SaveWatchlistPreferenceInput) =>
    postJson<WatchlistPreferenceMutationResponse>(
      "/watchlist-preferences",
      payload,
    ),
  deleteWatchlistPreference: (params: {
    account_id?: string;
    symbol: string;
    kind: "favorite" | "excluded";
  }) =>
    requestJson<WatchlistPreferenceMutationResponse>(
      `/watchlist-preferences?account_id=${encodeURIComponent(
        params.account_id ?? "default",
      )}&symbol=${encodeURIComponent(params.symbol)}&kind=${
        params.kind
      }`,
      "DELETE",
    ),
  getMacroSnapshot: () =>
    getJson<MacroSnapshotResponse>("/markets/macro-snapshot"),
  getSectorSpread: () =>
    getJson<SectorSpreadResponse>("/portfolio/sector-spread"),
  getTaxYearReport: (params?: { year?: number }) =>
    getJson<TaxYearReportResponse>(
      `/belasting/jaaroverzicht${
        params?.year ? `?year=${params.year}` : ""
      }`,
    ),
  taxYearReportCsvUrl: (params?: { year?: number }) =>
    `${API_BASE_URL}/belasting/jaaroverzicht.csv${
      params?.year ? `?year=${params.year}` : ""
    }`,
  getMonthlyReport: (params?: { year?: number; month?: number }) => {
    const qs: string[] = [];
    if (params?.year) qs.push(`year=${params.year}`);
    if (params?.month) qs.push(`month=${params.month}`);
    const suffix = qs.length > 0 ? `?${qs.join("&")}` : "";
    return getJson<MonthlyReportResponse>(`/rapporten/maand${suffix}`);
  },
  getPauzeStatus: () => getJson<PauzeStatusResponse>("/pauze"),
  postPauze: () => postJson<PauzeStatusResponse>("/pauze"),
  postHervat: () => postJson<PauzeStatusResponse>("/pauze/hervat"),
  // V1.2 §BJ — SELL-suggestie kaartjes voor dashboard.
  getSellSignals: () =>
    getJson<SellSignalListResponse>("/sell-signals"),
  dismissSellSignal: (cardId: string, reason?: string) =>
    requestJson<SellSignalCardResponse>(
      `/sell-signals/${encodeURIComponent(cardId)}/dismiss`,
      "POST",
      { reason: reason ?? null },
    ),
  triggerSellSignalSweep: () =>
    postJson<SellSignalSweepResponse>("/sell-signals/sweep"),
  // V1.2 §BV — Go-live runbook checklist.
  getRunbook: () => getJson<RunbookResponse>("/runbook"),
  getProfitTarget: () =>
    getJson<ProfitTargetResponse>("/settings/profit-target"),
  putProfitTarget: (payload: { profit_target_pct: string | null }) =>
    putJson<ProfitTargetResponse>("/settings/profit-target", payload),
  listDividenden: (params?: { year?: number }) =>
    getJson<DividendListResponse>(
      `/dividenden${params?.year ? `?year=${params.year}` : ""}`,
    ),
  createDividend: (payload: CreateDividendInput) =>
    postJson<DividendMutationResponse>("/dividenden", payload),
  deleteDividend: (dividendEventId: string) =>
    requestJson<DividendMutationResponse>(
      `/dividenden/${encodeURIComponent(dividendEventId)}`,
      "DELETE",
    ),
  taxYearReportPdfUrl: (params?: { year?: number }) =>
    `${API_BASE_URL}/belasting/jaaroverzicht.pdf${
      params?.year ? `?year=${params.year}` : ""
    }`,
  monthlyReportPdfUrl: (params: { year: number; month: number }) =>
    `${API_BASE_URL}/rapporten/maand.pdf?year=${params.year}&month=${params.month}`,
  listArchive: () =>
    getJson<{
      title_nl: string;
      help_nl: string;
      items: {
        archive_id: string;
        year: number;
        month: number;
        pdf_size_bytes: number;
        generated_at: string;
        source: string;
      }[];
    }>("/rapporten/archief"),
  generateArchive: (payload: { year: number; month: number }) =>
    postJson<{
      accepted: boolean;
      archive_id: string;
      pdf_size_bytes: number;
    }>("/rapporten/archief/generate", payload),
  archivePdfUrl: (params: { year: number; month: number }) =>
    `${API_BASE_URL}/rapporten/archief/${params.year}/${params.month}`,
  getTobYearToDate: (params?: { year?: number }) =>
    getJson<TobYearToDateResponse>(
      `/tob/year-to-date${params?.year ? `?year=${params.year}` : ""}`,
    ),
  getUpcomingEarnings: (params?: { days?: number }) =>
    getJson<EarningsUpcomingResponse>(
      `/earnings/upcoming${params?.days ? `?days=${params.days}` : ""}`,
    ),
  refreshEarnings: (payload: {
    symbols: string[];
    window_days?: number;
  }) =>
    postJson<EarningsRefreshResponse>("/earnings/refresh", {
      symbols: payload.symbols,
      window_days: payload.window_days ?? 21,
    }),
  getNotificationSettings: () =>
    getJson<NotificationSettingsResponse>("/settings/notifications"),
  updateNotificationSettings: (
    payload: NotificationSettingsUpdateInput,
  ) =>
    putJson<NotificationSettingsResponse>(
      "/settings/notifications",
      payload,
    ),
  sendTestEmail: () =>
    postJson<TestEmailResponse>(
      "/settings/notifications/test-email",
      undefined,
    ),
  getMarketEventsSettings: () =>
    getJson<MarketEventsSettingsResponse>("/settings/market-events"),
  updateMarketEventsSettings: (
    payload: MarketEventsSettingsUpdateInput,
  ) =>
    putJson<MarketEventsSettingsResponse>(
      "/settings/market-events",
      payload,
    ),
  getActiveSystemEvents: () => getJson<ActiveSystemEventsResponse>("/system/events/active"),
  getIbkrConfigAudit: () => getJson<ActiveSystemEventsResponse>("/admin/audit/ibkr-config"),
  resolveSystemEvent: (systemEventId: string, payload?: SystemEventActionInput) =>
    postJson<{ success: boolean }>(`/system/events/${systemEventId}/resolve`, payload),
  archiveSystemEvent: (systemEventId: string, payload?: SystemEventActionInput) =>
    postJson<{ success: boolean }>(`/system/events/${systemEventId}/archive`, payload),
  getErrors: () => getJson<ErrorLogResponse>("/errors"),
  reportError: (payload: ReportErrorInput) =>
    postJson<{ system_event_id: string }>("/errors/report", payload),
  resolveError: (systemEventId: string) =>
    postJson<{ message_nl: string }>(
      `/errors/${encodeURIComponent(systemEventId)}/resolve`,
    ),
  deleteError: (systemEventId: string) =>
    requestJson<{ message_nl: string }>(
      `/errors/${encodeURIComponent(systemEventId)}`,
      "DELETE",
    ),
  listResearchSources: () => requestJson<{ records: ResearchSourceRecord[] }>("/research/sources", "GET"),
  getResearchSource: (librarySourceId: string) => requestJson<{ record: ResearchSourceRecord }>(`/research/sources/${librarySourceId}`, "GET"),
  createResearchSource: (payload: Record<string, unknown>) => requestJson<{ message_nl: string }>("/research/sources", "POST", payload),
  createUrlMetadata: (librarySourceId: string, payload: Record<string, unknown>) => requestJson<{ message_nl: string }>(`/research/sources/${librarySourceId}/url-metadata`, "POST", payload),
  getUrlMetadata: (librarySourceId: string) => requestJson<{ record: Record<string, unknown> }>(`/research/sources/${librarySourceId}/url-metadata`, "GET"),
  createUserNote: (librarySourceId: string, payload: Record<string, unknown>) => requestJson<{ message_nl: string }>(`/research/sources/${librarySourceId}/user-note`, "POST", payload),
  getUserNote: (librarySourceId: string) => requestJson<{ record: Record<string, unknown> }>(`/research/sources/${librarySourceId}/user-note`, "GET"),
  getLatestProcessingStatus: (librarySourceId: string) => requestJson<{ record: Record<string, unknown> }>(`/research/sources/${librarySourceId}/processing-status/latest`, "GET"),
  getUploadedFileMetadata: (librarySourceId: string) => requestJson<{ record: ResearchUploadedFileMetadataRecord }>(`/research/sources/${librarySourceId}/uploaded-file-metadata`, "GET"),
  extractResearchSourceText: (librarySourceId: string) => requestJson<ResearchExtractTextResponse>(`/research/sources/${librarySourceId}/extract-text`, "POST"),
  uploadResearchSourceFile: (
    librarySourceId: string,
    file: File,
    metadata?: {
      title?: string;
      assetSymbol?: string;
      assetName?: string;
      documentType?: string;
      sourceKind?: string;
      sourceType?: string;
      explanationNl?: string;
    },
  ) => {
    const formData = new FormData();
    formData.append("file", file);

    if (metadata?.title) formData.append("title", metadata.title);
    if (metadata?.assetSymbol) formData.append("asset_symbol", metadata.assetSymbol);
    if (metadata?.assetName) formData.append("asset_name", metadata.assetName);
    if (metadata?.documentType) formData.append("document_type", metadata.documentType);
    if (metadata?.sourceKind) formData.append("source_kind", metadata.sourceKind);
    if (metadata?.sourceType) formData.append("source_type", metadata.sourceType);
    if (metadata?.explanationNl) formData.append("explanation_nl", metadata.explanationNl);

    return postFormData<{
      library_source_id: string;
      status: string;
      original_filename: string;
      stored_filename: string;
      file_size_bytes: number;
      sha256_hash: string;
      explanation_nl: string;
      archive_storage_uri?: string | null;
    }>(`/research/sources/${librarySourceId}/upload-file`, formData);
  },
};

type SystemEventActionInput = {
  reason_nl?: string;
};


export type AssetMasterSearchRecord = {
  asset_id: string;
  canonical_symbol: string;
  asset_name: string;
  primary_exchange: string | null;
  primary_currency: string | null;
  asset_type: string;
  status: string;
  identifier_summary_nl: string;
};

export async function searchAssetMasterIdentities(query: string): Promise<FetchState<{records: AssetMasterSearchRecord[]}>> {
  const encoded = encodeURIComponent(query);
  return getJson(`/assets/master/search?q=${encoded}`);
}

export type WatchlistItem = {
  watchlist_item_id: string;
  asset_id: string | null;
  symbol: string;
  name: string | null;
  exchange: string | null;
  currency: string | null;
  security_type: string | null;
  note: string | null;
  status: "active" | "archived";
  source: "manual";
  created_at: string;
  updated_at: string;
  ibkr_conid: string | null;
};

export async function listWatchlistItems(): Promise<FetchState<{items: WatchlistItemResponse[]}>> { return getJson('/watchlist/items'); }
export type IbkrContractCandidate = { candidate_id: string; ibkr_conid: string; symbol: string; company_name: string | null; asset_class: string | null; exchange: string | null; primary_exchange: string | null; currency: string | null; validation_status: string; };
export async function searchIbkrContracts(query: string): Promise<FetchState<{items: IbkrContractCandidate[]}>> { return getJson(`/ibkr/contracts/search?query=${encodeURIComponent(query)}`); }
export async function createWatchlistItem(payload: {ibkr_conid: string; ibkr_symbol: string; ibkr_contract_name?: string | null; ibkr_security_type?: string | null; ibkr_exchange?: string | null; ibkr_primary_exchange?: string | null; ibkr_currency?: string | null; ibkr_validation_status: string; note?: string | null}): Promise<FetchState<{item: WatchlistItemResponse}>> { return postJson('/watchlist/items', payload); }
export async function updateWatchlistItem(id: string, payload: {note?: string | null; name?: string | null; exchange?: string | null; currency?: string | null; security_type?: string | null; asset_id?: string | null}): Promise<FetchState<{item: WatchlistItemResponse}>> { try { const response = await fetch(`${API_BASE_URL}/watchlist/items/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); if (!response.ok) return { ok: false, reason: 'not_reachable' }; return { ok: true, data: (await response.json()) as {item: WatchlistItemResponse} }; } catch { return { ok: false, reason: 'not_reachable' }; } }
export async function archiveWatchlistItem(id: string): Promise<FetchState<{archived: boolean}>> { try { const response = await fetch(`${API_BASE_URL}/watchlist/items/${id}`, { method: 'DELETE' }); if (!response.ok) return { ok: false, reason: 'not_reachable' }; return { ok: true, data: (await response.json()) as {archived: boolean} }; } catch { return { ok: false, reason: 'not_reachable' }; } }


export type WatchlistItemResponse = {
  item: WatchlistItem;
  link_status: "gelinkt" | "niet_gelinkt";
  linked_asset: {
    asset_id: string;
    canonical_symbol: string | null;
    asset_name: string | null;
    primary_exchange: string | null;
    primary_currency: string | null;
  } | null;
  ibkr_status_label_nl: string;
  analysis_readiness_label_nl: string;
  asset_listing_readiness: WatchlistAssetListingReadiness;
};

export type WatchlistAssetListingReadiness = {
  link_status: string;
  listing_id: string | null;
  asset_id: string | null;
  ibkr_conid: string | null;
  symbol: string | null;
  security_type: string | null;
  exchange: string | null;
  primary_exchange: string | null;
  currency: string | null;
  validation_status: string | null;
  validated_at: string | null;
  market_data_ready: boolean;
  analysis_ready: boolean;
  suggestions_allowed: boolean;
  action_drafts_allowed: boolean;
  blocker_code: string | null;
  status_nl: string;
  freshness_status?: string | null;
  valuation_readiness_status?: string | null;
  price_basis?: string | null;
  price_basis_nl?: string | null;
  usable_price?: string | null;
  snapshot_age_seconds?: number | null;
  next_step_nl: string;
  audit_help_nl: string;
};

export type MarketDataLatestSnapshotStatusResponse = {
  ibkr_conid: string;
  status: string;
  status_nl: string;
  freshness_status?: string | null;
  valuation_readiness_status?: string | null;
  price_basis?: string | null;
  price_basis_nl?: string | null;
  usable_price?: string | null;
  snapshot_age_seconds?: number | null;
  next_step_nl: string;
  help_nl: string;
  analysis_ready: boolean;
  suggestions_allowed: boolean;
  action_drafts_allowed: boolean;
};


export type IbkrWatchlistSummary = { ibkr_watchlist_id: string; name: string; read_only: boolean | null; watchlist_scope: string | null; };
export type IbkrWatchlistInstrument = { ibkr_watchlist_id: string; ibkr_conid: string | null; symbol: string | null; name: string | null; asset_class: string | null; exchange: string | null; currency: string | null; validation_status: string; import_status: string; };
export async function listIbkrWatchlists(): Promise<FetchState<{status: string; configured: boolean; items: IbkrWatchlistSummary[]; message_nl: string}>> { return getJson("/ibkr/watchlists"); }
export async function listIbkrWatchlistInstruments(id: string): Promise<FetchState<{status: string; configured: boolean; items: IbkrWatchlistInstrument[]; message_nl: string}>> { return getJson(`/ibkr/watchlists/${encodeURIComponent(id)}/instruments`); }
export async function importIbkrWatchlist(id: string): Promise<FetchState<{status: string; run: {import_run_id: string}; candidates: IbkrWatchlistInstrument[]; message_nl: string}>> { return postJson(`/ibkr/watchlists/${encodeURIComponent(id)}/import`, {}); }
export async function getMarketDataLatestSnapshotStatus(ibkrConid: string): Promise<FetchState<MarketDataLatestSnapshotStatusResponse>> {
  return getJson(`/market-data/snapshots/latest/${encodeURIComponent(ibkrConid)}`);
}
