"""Read-only status and settings response models for the API foundation."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ServiceStatusCard(BaseModel):
    key: str
    label_nl: str
    status_key: str
    status_nl: str
    help_nl: str
    blocks_suggestions: bool
    last_checked_at: datetime | None
    action_nl: str | None = None


class SystemStatusSummary(BaseModel):
    project_name: str
    mode: str
    title_nl: str
    summary_nl: str
    help_nl: str
    paper_only: bool
    can_create_new_suggestions: bool
    suggestion_status_nl: str
    suggestion_help_nl: str
    services: list[ServiceStatusCard]


class SettingFieldHelp(BaseModel):
    label_nl: str
    help_nl: str


class IbkrSettingsSection(BaseModel):
    label_nl: str
    status_nl: str
    help_nl: str
    paper_account_required: bool
    live_order_transmission_allowed: bool
    fields_needed_later: list[SettingFieldHelp]


class OpenAiSettingsSection(BaseModel):
    label_nl: str
    status_nl: str
    help_nl: str
    api_key_configured: bool
    fields_needed_later: list[SettingFieldHelp]


class AiBudgetSection(BaseModel):
    label_nl: str
    status_nl: str
    help_nl: str


class SecretSafetySection(BaseModel):
    label_nl: str
    no_secret_values_returned: bool
    no_secret_values_stored_by_endpoint: bool
    help_nl: str


class SettingsSummary(BaseModel):
    title_nl: str
    help_nl: str
    ibkr: IbkrSettingsSection
    openai: OpenAiSettingsSection
    ai_budget: AiBudgetSection
    secret_safety: SecretSafetySection


class AiUsageSummary(BaseModel):
    title_nl: str
    help_nl: str
    usage_available: bool
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: Decimal | None
    estimated_cost_eur: Decimal | None
    actual_cost_usd: Decimal | None
    budget_status_nl: str
    budget_help_nl: str
    source_nl: str
    warning_nl: str


class IntegrationCard(BaseModel):
    key: str
    label_nl: str
    status_nl: str
    help_nl: str
    configured: bool
    connected: bool
    blocks_related_jobs: bool


class IntegrationsSummary(BaseModel):
    title_nl: str
    help_nl: str
    cards: list[IntegrationCard]


class DutchLabelsSummary(BaseModel):
    labels: dict[str, str]
