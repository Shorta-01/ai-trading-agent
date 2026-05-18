export type FetchState<T> =
  | { ok: true; data: T }
  | { ok: false; reason: "not_reachable" };

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

export type AiUsageSummary = {
  title_nl: string;
  help_nl: string;
  usage_available: boolean;
  estimated_cost_usd: number | null;
  estimated_cost_eur: number | null;
  budget_status_nl: string;
  budget_help_nl: string;
  warning_nl: string;
};

export type StorageStatusSummary = {
  title_nl: string;
  summary_nl: string;
  help_nl: string;
  selected_database_nl: string;
  migration_tool_nl: string;
  implementation_status_nl: string;
  first_persistence_target_nl: string;
  storage_ready: boolean;
  can_persist_paper_setup: boolean;
};

export type IntegrationCard = {
  key: string;
  label_nl: string;
  status_nl: string;
  help_nl: string;
  configured: boolean;
  connected: boolean;
  blocks_related_jobs: boolean;
};

export type IntegrationsSummary = {
  title_nl: string;
  help_nl: string;
  cards: IntegrationCard[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<FetchState<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });

    if (!response.ok) {
      return { ok: false, reason: "not_reachable" };
    }

    const data = (await response.json()) as T;
    return { ok: true, data };
  } catch {
    return { ok: false, reason: "not_reachable" };
  }
}

export const apiClient = {
  getSystemStatus: () => getJson<SystemStatusSummary>("/system/status"),
  getSettingsSummary: () => getJson<SettingsSummary>("/settings/summary"),
  getAiUsageSummary: () => getJson<AiUsageSummary>("/usage/ai/summary"),
  getIntegrationsSummary: () => getJson<IntegrationsSummary>("/integrations/summary"),
  getStorageStatus: () => getJson<StorageStatusSummary>("/storage/status"),
};
