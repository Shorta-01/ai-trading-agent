import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from .enums import (
    ApiConnectionCheckStatus,
    BudgetPeriod,
    BudgetStatus,
    ExternalIntegrationKind,
    ExternalIntegrationStatus,
    IBKRApiGatewayKind,
    IBKRConnectionMode,
    OpenAIModelPurpose,
    OpenAIUsageSource,
    PaperLiveMode,
    SecretStatus,
    SecretStorageKind,
)
from .identifiers import (
    ApiBudgetPolicyId,
    ApiConnectionCheckId,
    ApiCostEstimateId,
    ApiUsageSummaryId,
    AuditEventId,
    ExternalIntegrationId,
    ModelPricingId,
    SecretReferenceId,
    SettingsProfileId,
    SourceReferenceId,
)
from .primitives import CurrencyCode, DomainBaseModel, Money, Percentage

_MILLION = Decimal("1000000")
_ENV_VAR_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")

_VERSION_1_BLOCKED_ASSET_TYPES = (
    "options",
    "futures",
    "leverage",
    "short_selling",
    "crypto",
    "penny_stocks",
    "cfds",
    "complex_derivatives",
)


class AllowedAssetType(StrEnum):
    ETF = "etf"
    STOCK = "stock"
    CURRENCY = "currency"
    BOND_ETF = "bond_etf"
    COMMODITY_ETF = "commodity_etf"


class BlockedAssetType(StrEnum):
    OPTIONS = "options"
    FUTURES = "futures"
    LEVERAGE = "leverage"
    SHORT_SELLING = "short_selling"
    CRYPTO = "crypto"
    PENNY_STOCKS = "penny_stocks"
    CFDS = "cfds"
    COMPLEX_DERIVATIVES = "complex_derivatives"


class PortfolioGoal(StrEnum):
    BALANCED_GROWTH_RISK = "balanced_growth_risk"
    STABLE_INCOME = "stable_income"
    LONG_TERM_GROWTH = "long_term_growth"


class StrategyRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AssetMixPreference(StrEnum):
    ETF_AND_STOCK_MIX = "etf_and_stock_mix"
    MOSTLY_ETFS = "mostly_etfs"
    MOSTLY_STOCKS = "mostly_stocks"


class RegionPreference(StrEnum):
    GLOBAL = "global"
    EUROPE = "europe"
    USA = "usa"
    EMERGING = "emerging"


class SectorPreference(StrEnum):
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    INDUSTRIALS = "industrials"
    FINANCIALS = "financials"
    CONSUMER = "consumer"
    ENERGY = "energy"
    UTILITIES = "utilities"


class CurrencyPreference(StrEnum):
    EUR_PREFERRED_USD_ALLOWED = "eur_preferred_usd_allowed"
    EUR_ONLY = "eur_only"
    USD_ONLY = "usd_only"


class AssetPermissionStatus(StrEnum):
    ALLOWED = "allowed"
    WATCH_ONLY = "watch_only"
    BLOCKED = "blocked"


class SettingHelpText(DomainBaseModel):
    key: str
    label_nl: str
    help_nl: str

    @field_validator("key", "label_nl", "help_nl")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Veld is verplicht.")
        return value


class AllowedUniverseSettings(DomainBaseModel):
    allow_etfs: bool = True
    allow_stocks: bool = True
    allow_currencies_watch_only: bool = False
    allow_bond_etfs: bool = False
    allow_commodity_etfs: bool = False
    blocked_asset_types: tuple[BlockedAssetType, ...] = tuple(
        BlockedAssetType(value) for value in _VERSION_1_BLOCKED_ASSET_TYPES
    )
    explanation_nl: str = "Dit is de harde veiligheidsfilter voor toegestane beleggingen."


class UserStrategySettings(DomainBaseModel):
    portfolio_goal: PortfolioGoal = PortfolioGoal.BALANCED_GROWTH_RISK
    risk_level: StrategyRiskLevel = StrategyRiskLevel.MEDIUM
    asset_mix_preference: AssetMixPreference = AssetMixPreference.ETF_AND_STOCK_MIX
    preferred_regions: tuple[RegionPreference, ...] = (RegionPreference.GLOBAL,)
    preferred_sectors: tuple[SectorPreference, ...] = ()
    avoided_sectors: tuple[SectorPreference, ...] = ()
    max_position_pct: Decimal = Decimal("10")
    min_cash_reserve_pct: Decimal = Decimal("5")
    currency_preference: CurrencyPreference = CurrencyPreference.EUR_PREFERRED_USD_ALLOWED
    prefer_simple_belgian_tax_admin: bool = True
    # Task 133 product lock §4 — EUR headroom subtracted from
    # available_funds when sizing BUY drafts. Default €0; users can
    # raise it in the Settings UI for more conservative sizing.
    user_buffer_eur: Decimal = Decimal("0")
    explanation_nl: str = (
        "Dit is je voorkeurlaag voor ranking en fit, niet voor harde blokkeringen."
    )

    @field_validator(
        "max_position_pct", "min_cash_reserve_pct", "user_buffer_eur", mode="before"
    )
    @classmethod
    def reject_float(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float is niet toegestaan.")
        return value

    @field_validator("max_position_pct", "min_cash_reserve_pct")
    @classmethod
    def validate_percentage_range(cls, value: Decimal) -> Decimal:
        if value < Decimal("0") or value > Decimal("100"):
            raise ValueError("Percentage moet tussen 0 en 100 liggen.")
        return value

    @field_validator("user_buffer_eur")
    @classmethod
    def validate_user_buffer_non_negative(cls, value: Decimal) -> Decimal:
        if value < Decimal("0"):
            raise ValueError("user_buffer_eur moet ≥ 0 zijn.")
        return value


class AssetPermission(DomainBaseModel):
    allowed: bool
    status: AssetPermissionStatus
    reason_nl: str


def evaluate_asset_permission(
    asset_type: AllowedAssetType | BlockedAssetType | str,
    settings: AllowedUniverseSettings,
) -> AssetPermission:
    if isinstance(asset_type, BlockedAssetType) or (
        str(asset_type) in _VERSION_1_BLOCKED_ASSET_TYPES
    ):
        return AssetPermission(
            allowed=False,
            status=AssetPermissionStatus.BLOCKED,
            reason_nl="Geblokkeerd in versie 1.",
        )
    if asset_type is AllowedAssetType.ETF:
        if settings.allow_etfs:
            return AssetPermission(
                allowed=True,
                status=AssetPermissionStatus.ALLOWED,
                reason_nl="Toegestaan volgens je instellingen.",
            )
    if asset_type is AllowedAssetType.STOCK:
        if settings.allow_stocks:
            return AssetPermission(
                allowed=True,
                status=AssetPermissionStatus.ALLOWED,
                reason_nl="Toegestaan volgens je instellingen.",
            )
    if asset_type is AllowedAssetType.BOND_ETF and settings.allow_bond_etfs:
        return AssetPermission(
            allowed=True,
            status=AssetPermissionStatus.ALLOWED,
            reason_nl="Toegestaan volgens je instellingen.",
        )
    if asset_type is AllowedAssetType.COMMODITY_ETF and settings.allow_commodity_etfs:
        return AssetPermission(
            allowed=True,
            status=AssetPermissionStatus.ALLOWED,
            reason_nl="Toegestaan volgens je instellingen.",
        )
    if asset_type is AllowedAssetType.CURRENCY and settings.allow_currencies_watch_only:
        return AssetPermission(
            allowed=False,
            status=AssetPermissionStatus.WATCH_ONLY,
            reason_nl="Alleen volgen, niet kopen.",
        )
    return AssetPermission(
        allowed=False,
        status=AssetPermissionStatus.BLOCKED,
        reason_nl="Niet toegestaan volgens Toegestane beleggingen.",
    )


def get_allowed_universe_help_texts() -> tuple[SettingHelpText, ...]:
    return (
        SettingHelpText(
            key="allow_etfs",
            label_nl="ETF’s toestaan",
            help_nl="Het systeem mag ETF’s onderzoeken en gebruiken voor IBKR paper-acties.",
        ),
        SettingHelpText(
            key="allow_stocks",
            label_nl="Aandelen toestaan",
            help_nl="Het systeem mag gewone aandelen onderzoeken en gebruiken voor paper-acties.",
        ),
        SettingHelpText(
            key="allow_currencies_watch_only",
            label_nl="Valuta alleen volgen",
            help_nl="Valuta mogen gevolgd worden, maar niet gekocht of verkocht.",
        ),
    )


def get_user_strategy_help_texts() -> tuple[SettingHelpText, ...]:
    return (
        SettingHelpText(
            key="max_position_pct",
            label_nl="Maximum positie per asset",
            help_nl=(
                "Dit beperkt hoeveel één belegging maximaal van de paper portefeuille "
                "mag worden."
            ),
        ),
        SettingHelpText(
            key="min_cash_reserve_pct",
            label_nl="Minimale cashreserve",
            help_nl="Dit bepaalt welk minimum deel van de portefeuille cash moet blijven.",
        ),
        SettingHelpText(
            key="currency_preference",
            label_nl="Valutavoorkeur",
            help_nl="Dit stuurt de voorkeur voor euro en het toelaten van dollarposities.",
        ),
        SettingHelpText(
            key="user_buffer_eur",
            label_nl="Cashbuffer voor actiedrafts (EUR)",
            help_nl=(
                "Dit bedrag wordt afgetrokken van je beschikbare cash voordat de "
                "voorgestelde aankoophoeveelheid wordt berekend. Standaard €0."
            ),
        ),
    )


def strategy_settings_summary_nl(settings: UserStrategySettings) -> str:
    return (
        "Strategie: "
        f"doel={settings.portfolio_goal.value}, "
        f"risico={settings.risk_level.value}, "
        f"max positie={settings.max_position_pct}% en "
        f"min cash={settings.min_cash_reserve_pct}%."
    )


class PortfolioSettings(DomainBaseModel):
    starting_paper_capital: Money = Money(amount=Decimal("10000"), currency="EUR")
    base_currency: CurrencyCode = "EUR"
    paper_live_mode: PaperLiveMode = PaperLiveMode.PAPER
    risk_profile: str = "balanced"
    normal_minimum_cash_reserve: Percentage = Percentage(value=Decimal("20"))
    first_run_minimum_cash_reserve: Percentage = Percentage(value=Decimal("40"))
    first_run_maximum_invested: Percentage = Percentage(value=Decimal("60"))
    daily_deep_analysis_enabled: bool = True
    intraday_watcher_enabled: bool = True
    weekly_deep_discovery_enabled: bool = True
    monthly_performance_review_enabled: bool = True
    interface_language: str = "nl"
    simple_ui_enabled: bool = True

    @model_validator(mode="after")
    def validate_paper_mode_and_percentages(self) -> "PortfolioSettings":
        if self.paper_live_mode is not PaperLiveMode.PAPER:
            raise ValueError("Version 1 is paper-only. paper_live_mode must be 'paper'.")

        first_run_total = (
            self.first_run_minimum_cash_reserve.value + self.first_run_maximum_invested.value
        )
        if first_run_total > Decimal("100"):
            raise ValueError("First-run reserve and invested percentages cannot exceed 100%.")
        return self


class SecretReference(DomainBaseModel):
    secret_reference_id: SecretReferenceId
    secret_name: str
    storage_kind: SecretStorageKind
    status: SecretStatus
    environment_variable_name: str | None = None
    configured: bool
    last_checked_at: datetime | None = None
    explanation_nl: str

    @field_validator("secret_name", "explanation_nl")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field is verplicht.")
        return value

    @field_validator("environment_variable_name")
    @classmethod
    def validate_env_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not _ENV_VAR_PATTERN.fullmatch(value):
            raise ValueError("Ongeldige naam voor environment variable.")
        if value.startswith("sk-") or "SECRET" in value and value.count("_") < 1:
            raise ValueError("Lijkt op een geheime waarde in plaats van een naam.")
        return value

    @model_validator(mode="after")
    def validate_model(self) -> "SecretReference":
        if self.storage_kind is SecretStorageKind.ENVIRONMENT_VARIABLE:
            if self.environment_variable_name is None:
                raise ValueError(
                    "environment_variable_name is verplicht voor environment_variable."
                )
        if self.status is SecretStatus.AVAILABLE and not self.configured:
            raise ValueError("Beschikbare secret reference moet configured=true hebben.")
        if self.storage_kind is SecretStorageKind.NOT_CONFIGURED and self.configured:
            raise ValueError("not_configured storage vereist configured=false.")
        return self


class IBKRConnectionSettings(DomainBaseModel):
    external_integration_id: ExternalIntegrationId
    status: ExternalIntegrationStatus
    connection_mode: IBKRConnectionMode
    gateway_kind: IBKRApiGatewayKind
    enabled: bool
    host: str | None = None
    port: int | None = None
    client_id: int | None = None
    account_id: str | None = None
    paper_account_required: bool = True
    allow_live_order_transmission: bool = False
    last_connection_check_at: datetime | None = None
    explanation_nl: str

    @field_validator("explanation_nl")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Uitleg is verplicht.")
        return value

    @model_validator(mode="after")
    def validate_model(self) -> "IBKRConnectionSettings":
        if self.allow_live_order_transmission:
            raise ValueError("Live order transmission is niet toegestaan in deze build.")
        if not self.paper_account_required:
            raise ValueError("paper_account_required moet true zijn.")
        if self.port is not None and not 1 <= self.port <= 65535:
            raise ValueError("Port moet tussen 1 en 65535 liggen.")
        if self.client_id is not None and self.client_id < 0:
            raise ValueError("client_id moet >= 0 zijn.")
        if self.account_id is not None and (
            " " in self.account_id or self.account_id.startswith("sk-")
        ):
            raise ValueError("account_id bevat onveilige inhoud.")
        if self.enabled:
            if self.connection_mode in {
                IBKRConnectionMode.NOT_CONFIGURED,
                IBKRConnectionMode.DISABLED,
            }:
                raise ValueError("Ongeldige connection_mode voor enabled IBKR.")
            if self.gateway_kind is IBKRApiGatewayKind.NOT_CONFIGURED:
                raise ValueError("gateway_kind is verplicht als enabled=true.")
            if self.host is None or self.port is None or self.client_id is None:
                raise ValueError("host, port en client_id zijn verplicht als enabled=true.")
        return self


class OpenAIIntegrationSettings(DomainBaseModel):
    external_integration_id: ExternalIntegrationId
    status: ExternalIntegrationStatus
    enabled: bool
    api_key_secret_reference_id: SecretReferenceId | None = None
    organization_id: str | None = None
    project_id: str | None = None
    default_research_model: str | None = None
    cheaper_model: str | None = None
    fallback_model: str | None = None
    budget_policy_id: ApiBudgetPolicyId | None = None
    last_connection_check_at: datetime | None = None
    explanation_nl: str

    @field_validator("explanation_nl")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Uitleg is verplicht.")
        return value

    @field_validator("organization_id", "project_id")
    @classmethod
    def validate_non_secret_metadata(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value.startswith("sk-"):
            raise ValueError("Lijkt op geheime sleutel.")
        return value

    @field_validator("default_research_model", "cheaper_model", "fallback_model")
    @classmethod
    def validate_model_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.strip():
            raise ValueError("Modelnaam mag niet leeg zijn.")
        return value

    @model_validator(mode="after")
    def validate_model(self) -> "OpenAIIntegrationSettings":
        if self.enabled:
            if self.api_key_secret_reference_id is None:
                raise ValueError("api_key_secret_reference_id is verplicht als enabled=true.")
            if self.default_research_model is None:
                raise ValueError("default_research_model is verplicht als enabled=true.")
        return self


class OpenAIModelPricing(DomainBaseModel):
    model_pricing_id: ModelPricingId
    model_name: str
    input_usd_per_1m_tokens: Decimal
    cached_input_usd_per_1m_tokens: Decimal | None = None
    output_usd_per_1m_tokens: Decimal
    purpose: OpenAIModelPurpose
    effective_from: datetime
    source_reference_ids: list[SourceReferenceId] = Field(min_length=1)
    audit_event_ids: list[AuditEventId] = Field(min_length=1)
    explanation_nl: str

    @field_validator(
        "input_usd_per_1m_tokens",
        "cached_input_usd_per_1m_tokens",
        "output_usd_per_1m_tokens",
        mode="before",
    )
    @classmethod
    def reject_float(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float is niet toegestaan.")
        return value

    @field_validator(
        "input_usd_per_1m_tokens", "cached_input_usd_per_1m_tokens", "output_usd_per_1m_tokens"
    )
    @classmethod
    def validate_non_negative_price(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < Decimal("0"):
            raise ValueError("Prijs moet >= 0 zijn.")
        return value


class ApiBudgetPolicy(DomainBaseModel):
    api_budget_policy_id: ApiBudgetPolicyId
    integration_kind: ExternalIntegrationKind
    period: BudgetPeriod
    budget_amount_eur: Decimal
    warning_threshold_percent: Decimal
    critical_threshold_percent: Decimal
    block_when_exceeded: bool
    enabled: bool
    explanation_nl: str

    @field_validator(
        "budget_amount_eur",
        "warning_threshold_percent",
        "critical_threshold_percent",
        mode="before",
    )
    @classmethod
    def reject_float(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float is niet toegestaan.")
        return value

    @model_validator(mode="after")
    def validate_model(self) -> "ApiBudgetPolicy":
        if not self.explanation_nl.strip():
            raise ValueError("Uitleg is verplicht.")
        if self.budget_amount_eur < Decimal("0"):
            raise ValueError("budget_amount_eur moet >= 0 zijn.")
        if not Decimal("0") <= self.warning_threshold_percent <= Decimal("100"):
            raise ValueError("warning_threshold_percent buiten bereik.")
        if not Decimal("0") <= self.critical_threshold_percent <= Decimal("100"):
            raise ValueError("critical_threshold_percent buiten bereik.")
        if self.warning_threshold_percent > self.critical_threshold_percent:
            raise ValueError("warning_threshold_percent mag niet groter zijn dan critical.")
        if self.enabled and self.budget_amount_eur <= Decimal("0"):
            raise ValueError("enabled budget vereist budget_amount_eur > 0.")
        return self


class ApiUsageSummary(DomainBaseModel):
    api_usage_summary_id: ApiUsageSummaryId
    integration_kind: ExternalIntegrationKind
    usage_source: OpenAIUsageSource
    period: BudgetPeriod
    period_start: datetime
    period_end: datetime
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: Decimal | None = None
    estimated_cost_eur: Decimal | None = None
    actual_cost_usd: Decimal | None = None
    eur_usd_exchange_rate: Decimal | None = None
    source_reference_ids: list[SourceReferenceId] = Field(default_factory=list)
    audit_event_ids: list[AuditEventId] = Field(min_length=1)
    explanation_nl: str

    @field_validator(
        "estimated_cost_usd",
        "estimated_cost_eur",
        "actual_cost_usd",
        "eur_usd_exchange_rate",
        mode="before",
    )
    @classmethod
    def reject_float(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float is niet toegestaan.")
        return value

    @model_validator(mode="after")
    def validate_model(self) -> "ApiUsageSummary":
        if not self.explanation_nl.strip():
            raise ValueError("Uitleg is verplicht.")
        if self.period_end <= self.period_start:
            raise ValueError("period_end moet na period_start liggen.")
        for tokens in (
            self.input_tokens,
            self.cached_input_tokens,
            self.output_tokens,
            self.total_tokens,
        ):
            if tokens < 0:
                raise ValueError("Tokens moeten >= 0 zijn.")
        if self.total_tokens != self.input_tokens + self.cached_input_tokens + self.output_tokens:
            raise ValueError("total_tokens komt niet overeen.")
        for cost_value in (self.estimated_cost_usd, self.estimated_cost_eur, self.actual_cost_usd):
            if cost_value is not None and cost_value < Decimal("0"):
                raise ValueError("Kosten moeten >= 0 zijn.")
        if self.eur_usd_exchange_rate is not None and self.eur_usd_exchange_rate <= Decimal("0"):
            raise ValueError("Wisselkoers moet > 0 zijn.")
        if (
            self.usage_source is not OpenAIUsageSource.LOCAL_ESTIMATE
            and not self.source_reference_ids
        ):
            raise ValueError("source_reference_ids zijn verplicht voor niet-local_estimate.")
        return self


class ApiCostEstimate(DomainBaseModel):
    api_cost_estimate_id: ApiCostEstimateId
    model_pricing_id: ModelPricingId
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    estimated_cost_usd: Decimal
    estimated_cost_eur: Decimal | None = None
    eur_usd_exchange_rate: Decimal | None = None
    calculated_at: datetime
    explanation_nl: str

    @field_validator(
        "estimated_cost_usd", "estimated_cost_eur", "eur_usd_exchange_rate", mode="before"
    )
    @classmethod
    def reject_float(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float is niet toegestaan.")
        return value

    @model_validator(mode="after")
    def validate_model(self) -> "ApiCostEstimate":
        if not self.explanation_nl.strip():
            raise ValueError("Uitleg is verplicht.")
        for tokens in (self.input_tokens, self.cached_input_tokens, self.output_tokens):
            if tokens < 0:
                raise ValueError("Tokens moeten >= 0 zijn.")
        if self.estimated_cost_usd < Decimal("0"):
            raise ValueError("estimated_cost_usd moet >= 0 zijn.")
        if self.estimated_cost_eur is not None and self.estimated_cost_eur < Decimal("0"):
            raise ValueError("estimated_cost_eur moet >= 0 zijn.")
        if self.eur_usd_exchange_rate is not None and self.eur_usd_exchange_rate <= Decimal("0"):
            raise ValueError("eur_usd_exchange_rate moet > 0 zijn.")
        return self


class ApiConnectionCheck(DomainBaseModel):
    api_connection_check_id: ApiConnectionCheckId
    integration_kind: ExternalIntegrationKind
    status: ApiConnectionCheckStatus
    checked_at: datetime
    message_nl: str
    blocks_related_jobs: bool

    @model_validator(mode="after")
    def validate_model(self) -> "ApiConnectionCheck":
        if not self.message_nl.strip():
            raise ValueError("message_nl is verplicht.")
        if self.status is ApiConnectionCheckStatus.BLOCKED and not self.blocks_related_jobs:
            raise ValueError("Blocked status vereist blocks_related_jobs=true.")
        return self


class SettingsProfile(DomainBaseModel):
    settings_profile_id: SettingsProfileId
    profile_name: str
    ibkr_settings: IBKRConnectionSettings
    openai_settings: OpenAIIntegrationSettings
    secret_references: list[SecretReference]
    budget_policies: list[ApiBudgetPolicy]
    created_at: datetime
    explanation_nl: str

    @model_validator(mode="after")
    def validate_model(self) -> "SettingsProfile":
        if not self.profile_name.strip() or not self.explanation_nl.strip():
            raise ValueError("profile_name en explanation_nl zijn verplicht.")
        if len({s.secret_reference_id for s in self.secret_references}) != len(
            self.secret_references
        ):
            raise ValueError("secret_reference_id moet uniek zijn.")
        if len({b.api_budget_policy_id for b in self.budget_policies}) != len(self.budget_policies):
            raise ValueError("api_budget_policy_id moet uniek zijn.")
        if self.openai_settings.api_key_secret_reference_id is not None:
            known = {s.secret_reference_id for s in self.secret_references}
            if self.openai_settings.api_key_secret_reference_id not in known:
                raise ValueError("OpenAI secret reference bestaat niet in secret_references.")
        return self


def build_default_settings_profile(*, created_at: datetime) -> SettingsProfile:
    return SettingsProfile(
        settings_profile_id="settings_default",
        profile_name="Standaard instellingen",
        ibkr_settings=IBKRConnectionSettings(
            external_integration_id="integration_ibkr",
            status=ExternalIntegrationStatus.NOT_CONFIGURED,
            connection_mode=IBKRConnectionMode.NOT_CONFIGURED,
            gateway_kind=IBKRApiGatewayKind.NOT_CONFIGURED,
            enabled=False,
            paper_account_required=True,
            allow_live_order_transmission=False,
            explanation_nl="IBKR is nog niet ingesteld.",
        ),
        openai_settings=OpenAIIntegrationSettings(
            external_integration_id="integration_openai",
            status=ExternalIntegrationStatus.NOT_CONFIGURED,
            enabled=False,
            api_key_secret_reference_id="secret_openai_api_key",
            explanation_nl="OpenAI is nog niet ingesteld.",
        ),
        secret_references=[
            SecretReference(
                secret_reference_id="secret_openai_api_key",
                secret_name="OpenAI API sleutel",
                storage_kind=SecretStorageKind.NOT_CONFIGURED,
                status=SecretStatus.NOT_CONFIGURED,
                configured=False,
                explanation_nl="API-sleutel referentie is nog niet ingesteld.",
            )
        ],
        budget_policies=[
            ApiBudgetPolicy(
                api_budget_policy_id="openai_daily_budget",
                integration_kind=ExternalIntegrationKind.OPENAI,
                period=BudgetPeriod.DAILY,
                budget_amount_eur=Decimal("0"),
                warning_threshold_percent=Decimal("80"),
                critical_threshold_percent=Decimal("95"),
                block_when_exceeded=True,
                enabled=False,
                explanation_nl="Dagbudget is nog niet geactiveerd.",
            ),
            ApiBudgetPolicy(
                api_budget_policy_id="openai_monthly_budget",
                integration_kind=ExternalIntegrationKind.OPENAI,
                period=BudgetPeriod.MONTHLY,
                budget_amount_eur=Decimal("0"),
                warning_threshold_percent=Decimal("80"),
                critical_threshold_percent=Decimal("95"),
                block_when_exceeded=True,
                enabled=False,
                explanation_nl="Maandbudget is nog niet geactiveerd.",
            ),
        ],
        created_at=created_at,
        explanation_nl="Standaardprofiel zonder echte sleutels of verbindingen.",
    )


def ibkr_settings_ready_for_paper(settings: IBKRConnectionSettings) -> bool:
    return (
        settings.enabled
        and settings.connection_mode
        in {IBKRConnectionMode.PAPER_ONLY, IBKRConnectionMode.PAPER_READINESS}
        and settings.gateway_kind in {IBKRApiGatewayKind.TWS, IBKRApiGatewayKind.IB_GATEWAY}
        and settings.host is not None
        and settings.port is not None
        and settings.client_id is not None
        and settings.paper_account_required
        and not settings.allow_live_order_transmission
    )


def openai_settings_ready(
    settings: OpenAIIntegrationSettings, secrets: list[SecretReference]
) -> bool:
    if not settings.enabled or settings.api_key_secret_reference_id is None:
        return False
    if settings.default_research_model is None:
        return False
    secret_map = {secret.secret_reference_id: secret for secret in secrets}
    ref = secret_map.get(settings.api_key_secret_reference_id)
    return ref is not None and ref.status is SecretStatus.AVAILABLE


def estimate_openai_cost(
    *,
    pricing: OpenAIModelPricing,
    input_tokens: int,
    cached_input_tokens: int,
    output_tokens: int,
    calculated_at: datetime,
    eur_usd_exchange_rate: Decimal | None = None,
) -> ApiCostEstimate:
    cached_price = pricing.cached_input_usd_per_1m_tokens or pricing.input_usd_per_1m_tokens
    input_cost = (Decimal(input_tokens) / _MILLION) * pricing.input_usd_per_1m_tokens
    cached_cost = (Decimal(cached_input_tokens) / _MILLION) * cached_price
    output_cost = (Decimal(output_tokens) / _MILLION) * pricing.output_usd_per_1m_tokens
    estimated_usd = input_cost + cached_cost + output_cost
    estimated_eur = None
    if eur_usd_exchange_rate is not None:
        estimated_eur = estimated_usd / eur_usd_exchange_rate
    return ApiCostEstimate(
        api_cost_estimate_id=f"cost_{pricing.model_pricing_id}_{calculated_at.strftime('%Y%m%d%H%M%S')}",
        model_pricing_id=pricing.model_pricing_id,
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=estimated_usd,
        estimated_cost_eur=estimated_eur,
        eur_usd_exchange_rate=eur_usd_exchange_rate,
        calculated_at=calculated_at,
        explanation_nl="Deterministische kostenschatting op basis van ingestelde modelprijzen.",
    )


def calculate_budget_status(
    *, policy: ApiBudgetPolicy, estimated_cost_eur: Decimal
) -> BudgetStatus:
    if not policy.enabled:
        return BudgetStatus.NOT_CONFIGURED
    if estimated_cost_eur >= policy.budget_amount_eur and policy.block_when_exceeded:
        return BudgetStatus.BLOCKED
    if estimated_cost_eur >= policy.budget_amount_eur:
        return BudgetStatus.EXCEEDED
    usage_percent = (estimated_cost_eur / policy.budget_amount_eur) * Decimal("100")
    if usage_percent >= policy.critical_threshold_percent:
        return BudgetStatus.CRITICAL
    if usage_percent >= policy.warning_threshold_percent:
        return BudgetStatus.WARNING
    return BudgetStatus.OK


def remaining_budget_eur(*, policy: ApiBudgetPolicy, estimated_cost_eur: Decimal) -> Decimal:
    remaining = policy.budget_amount_eur - estimated_cost_eur
    if remaining < Decimal("0"):
        return Decimal("0")
    return remaining


def connection_check_blocks_jobs(check: ApiConnectionCheck) -> bool:
    if check.status is ApiConnectionCheckStatus.BLOCKED:
        return True
    if check.status is ApiConnectionCheckStatus.ERROR:
        return check.blocks_related_jobs
    return False
