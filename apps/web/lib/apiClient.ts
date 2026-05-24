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
};

export type ActiveSystemEventsResponse = {
  events: SystemEventSummary[];
  storage_available?: boolean;
  summary_nl?: string;
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

async function requestJson<T>(path: string, method: "GET" | "POST", body?: object): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: method === "POST" ? JSON.stringify(body ?? {}) : undefined,
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
  getActiveSystemEvents: () => getJson<ActiveSystemEventsResponse>("/system/events/active"),
  resolveSystemEvent: (systemEventId: string, payload?: SystemEventActionInput) =>
    postJson<{ success: boolean }>(`/system/events/${systemEventId}/resolve`, payload),
  archiveSystemEvent: (systemEventId: string, payload?: SystemEventActionInput) =>
    postJson<{ success: boolean }>(`/system/events/${systemEventId}/archive`, payload),
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
