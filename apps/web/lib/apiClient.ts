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
  getIbkrPositions: () => getJson<{ items: IbkrPositionSnapshot[] }>("/ibkr/portfolio/positions"),
  getIbkrCash: () => getJson<{ items: IbkrCashSnapshot[] }>("/ibkr/account/cash"),
  getIbkrOpenOrders: () => getJson<{ items: IbkrOpenOrderSnapshot[] }>("/ibkr/orders/open"),
  getIbkrExecutions: () => getJson<{ items: IbkrExecutionSnapshot[] }>("/ibkr/executions"),
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
