from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from .primitives import DomainBaseModel


class ResearchSourceType(StrEnum):
    BROKER_DATA = "broker_data"
    OFFICIAL_FILING = "official_filing"
    COMPANY_REPORT = "company_report"
    INVESTOR_PRESENTATION = "investor_presentation"
    EARNINGS_RELEASE = "earnings_release"
    ETF_FACTSHEET = "etf_factsheet"
    ETF_KID_KIID = "etf_kid_kiid"
    EXCHANGE_CALENDAR = "exchange_calendar"
    MARKET_DATA = "market_data"
    FINANCIAL_NEWS = "financial_news"
    ANALYST_COMMENTARY = "analyst_commentary"
    USER_UPLOADED_DOCUMENT = "user_uploaded_document"
    USER_URL = "user_url"
    USER_NOTE = "user_note"
    BLOG_OR_FORUM = "blog_or_forum"
    UNKNOWN = "unknown"


class ResearchDocumentType(StrEnum):
    ANNUAL_REPORT = "annual_report"
    QUARTERLY_REPORT = "quarterly_report"
    EARNINGS_RELEASE = "earnings_release"
    INVESTOR_PRESENTATION = "investor_presentation"
    FUND_FACTSHEET = "fund_factsheet"
    KID_KIID = "kid_kiid"
    PROSPECTUS = "prospectus"
    ANALYST_REPORT = "analyst_report"
    BROKER_REPORT = "broker_report"
    SEC_10K = "sec_10k"
    SEC_10Q = "sec_10q"
    SEC_8K = "sec_8k"
    SEC_20F = "sec_20f"
    SEC_40F = "sec_40f"
    SEC_6K = "sec_6k"
    WEBPAGE = "webpage"
    USER_NOTE = "user_note"
    OTHER = "other"
    UNKNOWN = "unknown"


class ResearchSourceStatus(StrEnum):
    NEW = "new"
    STORED = "stored"
    EXTRACTION_PENDING = "extraction_pending"
    EXTRACTED = "extracted"
    ANALYSIS_PENDING = "analysis_pending"
    ANALYZED = "analyzed"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    FAILED = "failed"


class SourceCredibilityLevel(StrEnum):
    HIGHEST = "highest"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class SourceAuthorityCategory(StrEnum):
    BROKER_TRUTH = "broker_truth"
    OFFICIAL_EXCHANGE = "official_exchange"
    REGULATOR_OR_FILING_SYSTEM = "regulator_or_filing_system"
    OFFICIAL_COMPANY = "official_company"
    OFFICIAL_FUND_PROVIDER = "official_fund_provider"
    REPUTABLE_NEWS = "reputable_news"
    ANALYST_OR_BROKER_OPINION = "analyst_or_broker_opinion"
    USER_SUPPLIED = "user_supplied"
    SOCIAL_OR_FORUM = "social_or_forum"
    UNKNOWN = "unknown"


class ResearchDataType(StrEnum):
    BROKER_CASH = "broker_cash"
    BROKER_POSITIONS = "broker_positions"
    BROKER_ORDERS = "broker_orders"
    BROKER_EXECUTIONS = "broker_executions"
    MARKET_PRICE = "market_price"
    FX_RATE = "fx_rate"
    MARKET_CALENDAR = "market_calendar"
    COMPANY_FILING = "company_filing"
    COMPANY_REPORT = "company_report"
    EARNINGS_EVENT = "earnings_event"
    NEWS = "news"
    AI_RESEARCH = "ai_research"
    ACTION_SUGGESTION = "action_suggestion"
    RECONCILIATION = "reconciliation"
    USER_UPLOADED_SOURCE = "user_uploaded_source"


class FreshnessStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class PromptInjectionRiskLevel(StrEnum):
    NONE_DETECTED = "none_detected"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class PromptInjectionSignalType(StrEnum):
    IGNORE_PREVIOUS_INSTRUCTIONS = "ignore_previous_instructions"
    OVERRIDE_SYSTEM_RULES = "override_system_rules"
    REQUEST_TO_TRADE_OR_ORDER = "request_to_trade_or_order"
    REQUEST_TO_REVEAL_SECRETS = "request_to_reveal_secrets"
    REQUEST_TO_CHANGE_STRATEGY = "request_to_change_strategy"
    REQUEST_TO_BYPASS_VALIDATION = "request_to_bypass_validation"
    HIDDEN_OR_SUSPICIOUS_TEXT = "hidden_or_suspicious_text"
    EXTERNAL_INSTRUCTION_CLAIM = "external_instruction_claim"
    UNKNOWN = "unknown"


class AIResearchRunStatus(StrEnum):
    REQUESTED = "requested"
    RUNNING = "running"
    COMPLETED = "completed"
    VALIDATION_FAILED = "validation_failed"
    DISCARDED = "discarded"
    FAILED = "failed"


class AIResearchUseStatus(StrEnum):
    NOT_USED = "not_used"
    USED_IN_SUGGESTION = "used_in_suggestion"
    DISCARDED_DUE_TO_VALIDATION = "discarded_due_to_validation"
    DISCARDED_DUE_TO_STALENESS = "discarded_due_to_staleness"
    DISCARDED_DUE_TO_SOURCE_QUALITY = "discarded_due_to_source_quality"
    BLOCKED_DUE_TO_PROMPT_INJECTION = "blocked_due_to_prompt_injection"


class CatalystEventType(StrEnum):
    EARNINGS = "earnings"
    ANNUAL_REPORT = "annual_report"
    QUARTERLY_REPORT = "quarterly_report"
    FILING = "filing"
    DIVIDEND = "dividend"
    EX_DIVIDEND = "ex_dividend"
    INVESTOR_DAY = "investor_day"
    GUIDANCE_UPDATE = "guidance_update"
    PRODUCT_EVENT = "product_event"
    ETF_REBALANCE = "etf_rebalance"
    MACRO_EVENT = "macro_event"
    MARKET_HOLIDAY = "market_holiday"
    HALF_DAY = "half_day"
    AUCTION_PHASE = "auction_phase"
    UNKNOWN = "unknown"


class CatalystImpactLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class SuggestionAction(StrEnum):
    KOPEN = "kopen"
    LANGZAAM_BIJKOPEN = "langzaam_bijkopen"
    HOUDEN = "houden"
    BEKIJKEN = "bekijken"
    VERMINDEREN = "verminderen"
    VERKOPEN = "verkopen"
    VERMIJDEN = "vermijden"
    CASH_HOUDEN = "cash_houden"
    GEEN_ACTIE = "geen_actie"
    GEBLOKKEERD = "geblokkeerd"


class SuggestionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    CONVERTED_TO_IBKR_ACTION = "converted_to_ibkr_action"
    BLOCKED = "blocked"
    ARCHIVED = "archived"


class SuggestionConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class SuggestionTimeSensitivity(StrEnum):
    INTRADAY = "intraday"
    SHORT_TERM = "short_term"
    EVENT_DRIVEN = "event_driven"
    LONG_TERM = "long_term"
    UNKNOWN = "unknown"


class SuggestionBlockedReason(StrEnum):
    STALE_CASH = "stale_cash"
    STALE_POSITIONS = "stale_positions"
    STALE_PRICE = "stale_price"
    STALE_FX = "stale_fx"
    STALE_RESEARCH = "stale_research"
    MARKET_CLOSED = "market_closed"
    MARKET_STATE_UNKNOWN = "market_state_unknown"
    ACCOUNT_MODE_UNKNOWN = "account_mode_unknown"
    SOURCE_QUALITY_TOO_LOW = "source_quality_too_low"
    PROMPT_INJECTION_RISK = "prompt_injection_risk"
    RISK_RULE_FAILED = "risk_rule_failed"
    CASH_RULE_FAILED = "cash_rule_failed"
    POSITION_LIMIT_FAILED = "position_limit_failed"
    UNSUPPORTED_ASSET_TYPE = "unsupported_asset_type"
    MISSING_BROKER_DATA = "missing_broker_data"
    MISSING_RESEARCH = "missing_research"
    AI_VALIDATION_FAILED = "ai_validation_failed"
    RECONCILIATION_FAILED = "reconciliation_failed"
    UNKNOWN = "unknown"


class SuggestionOutcomeStatus(StrEnum):
    PENDING = "pending"
    USER_IGNORED = "user_ignored"
    USER_CONVERTED_TO_ACTION = "user_converted_to_action"
    ACTION_EXECUTED = "action_executed"
    EXPIRED_WITHOUT_ACTION = "expired_without_action"
    OUTCOME_MEASURED = "outcome_measured"
    NOT_MEASURABLE = "not_measurable"


class ResearchSourceReference(DomainBaseModel):
    source_id: str
    asset_symbol: str | None = None
    asset_name: str | None = None
    source_type: ResearchSourceType
    document_type: ResearchDocumentType
    title: str
    source_url: str | None = None
    file_name: str | None = None
    file_hash: str | None = None
    source_date: date | None = None
    reporting_period: str | None = None
    fiscal_year: int | None = None
    language: str | None = None
    uploaded_by_user: bool
    created_at: datetime
    status: ResearchSourceStatus
    explanation_nl: str

    @field_validator("source_id", "title")
    @classmethod
    def _required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("field must be non-empty")
        return value

    @model_validator(mode="after")
    def _validate_reference(self) -> "ResearchSourceReference":
        if self.source_type in {
            ResearchSourceType.USER_URL,
            ResearchSourceType.WEBPAGE if False else ResearchSourceType.UNKNOWN,
        }:
            pass
        if (
            self.source_type
            in {
                ResearchSourceType.USER_URL,
                ResearchSourceType.FINANCIAL_NEWS,
                ResearchSourceType.BLOG_OR_FORUM,
            }
            and not self.source_url
        ):
            raise ValueError("source_url required for URL-based source types")
        if self.source_type == ResearchSourceType.USER_UPLOADED_DOCUMENT and not self.file_name:
            raise ValueError("file_name required for uploaded document source")
        if (
            self.source_type == ResearchSourceType.USER_NOTE
            and self.source_url is None
            and self.file_name is None
        ):
            return self
        if not (
            self.source_url or self.file_name or self.source_type == ResearchSourceType.USER_NOTE
        ):
            raise ValueError("source reference requires source_url, file_name, or user_note")
        return self


class SourceCredibilityAssessment(DomainBaseModel):
    source_id: str
    authority_category: SourceAuthorityCategory
    credibility_level: SourceCredibilityLevel
    credibility_score: Decimal = Field(ge=Decimal("0"), le=Decimal("100"))
    reason_nl: str
    assessed_at: datetime

    @field_validator("credibility_score", mode="before")
    @classmethod
    def _reject_float(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float credibility scores are not allowed.")
        return value


class FreshnessSla(DomainBaseModel):
    data_type: ResearchDataType
    max_age_seconds: int
    blocks_suggestions_when_stale: bool
    blocks_orders_when_stale: bool
    warning_nl: str
    explanation_nl: str

    @field_validator("max_age_seconds")
    @classmethod
    def _positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_age_seconds must be positive")
        return value


class FreshnessAssessment(DomainBaseModel):
    data_type: ResearchDataType
    status: FreshnessStatus
    observed_at: datetime | None = None
    checked_at: datetime
    age_seconds: int | None = None
    max_age_seconds: int
    blocks_suggestions: bool
    blocks_orders: bool
    reason_nl: str

    @field_validator("age_seconds")
    @classmethod
    def _age_not_negative(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("age_seconds must not be negative")
        return value


class PromptInjectionSignal(DomainBaseModel):
    signal_type: PromptInjectionSignalType
    risk_level: PromptInjectionRiskLevel
    matched_text_excerpt: str | None = None
    explanation_nl: str


class PromptInjectionAssessment(DomainBaseModel):
    source_id: str
    risk_level: PromptInjectionRiskLevel
    signals: tuple[PromptInjectionSignal, ...]
    safe_to_use_as_evidence: bool
    safe_to_use_as_instruction: bool
    assessed_at: datetime
    explanation_nl: str

    @model_validator(mode="after")
    def _validate_safety(self) -> "PromptInjectionAssessment":
        if self.safe_to_use_as_instruction:
            raise ValueError("external research content can never be used as instruction")
        if (
            self.risk_level in {PromptInjectionRiskLevel.HIGH, PromptInjectionRiskLevel.BLOCKED}
            and self.safe_to_use_as_evidence
        ):
            raise ValueError("high/blocked injection risk cannot be safe evidence")
        return self


class AIResearchEvidenceItem(DomainBaseModel):
    evidence_id: str
    source_id: str
    claim_nl: str
    claim_type: str
    supports_buy: bool
    supports_sell: bool
    supports_hold: bool
    credibility_level: SourceCredibilityLevel
    freshness_status: FreshnessStatus
    explanation_nl: str


class AIResearchOutput(DomainBaseModel):
    research_run_id: str
    asset_symbol: str
    summary_nl: str
    positive_evidence: tuple[AIResearchEvidenceItem, ...]
    negative_evidence: tuple[AIResearchEvidenceItem, ...]
    uncertainties_nl: tuple[str, ...]
    catalyst_notes_nl: tuple[str, ...]
    risk_notes_nl: tuple[str, ...]
    source_ids: tuple[str, ...]
    prompt_injection_assessment: PromptInjectionAssessment | None = None
    schema_version: str
    generated_at: datetime
    validation_passed: bool
    explanation_nl: str


class ResearchRun(DomainBaseModel):
    research_run_id: str
    asset_symbol: str
    requested_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: AIResearchRunStatus
    source_ids: tuple[str, ...]
    model_name: str | None = None
    input_token_count: int | None = None
    output_token_count: int | None = None
    estimated_cost: Decimal | None = None
    use_status: AIResearchUseStatus
    explanation_nl: str

    @field_validator("estimated_cost", mode="before")
    @classmethod
    def _reject_float_cost(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float estimated costs are not allowed.")
        return value

    @field_validator("input_token_count", "output_token_count")
    @classmethod
    def _non_negative_tokens(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("token counts must be non-negative")
        return value


class CatalystEvent(DomainBaseModel):
    event_id: str
    asset_symbol: str | None = None
    event_type: CatalystEventType
    event_time: datetime | None = None
    timezone: str | None = None
    source_id: str | None = None
    impact_level: CatalystImpactLevel
    known_before_suggestion: bool
    reason_nl: str


class SuggestionValidityWindow(DomainBaseModel):
    valid_from: datetime
    valid_until: datetime | None = None
    expires_on_market_close: bool
    expires_on_price_change: bool
    expires_on_event: bool
    related_event_ids: tuple[str, ...]
    reason_nl: str


class SuggestionAuditLink(DomainBaseModel):
    research_run_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    freshness_assessment_ids: tuple[str, ...]
    catalyst_event_ids: tuple[str, ...]
    system_event_ids: tuple[str, ...]
    explanation_nl: str


class ActionSuggestion(DomainBaseModel):
    suggestion_id: str
    asset_symbol: str
    action: SuggestionAction
    status: SuggestionStatus
    confidence: SuggestionConfidence
    time_sensitivity: SuggestionTimeSensitivity
    title_nl: str
    summary_nl: str
    reason_nl: str
    created_at: datetime
    updated_at: datetime
    validity_window: SuggestionValidityWindow
    blocked_reasons: tuple[SuggestionBlockedReason, ...]
    freshness_assessments: tuple[FreshnessAssessment, ...]
    source_credibility_assessments: tuple[SourceCredibilityAssessment, ...]
    catalyst_events: tuple[CatalystEvent, ...]
    audit_link: SuggestionAuditLink
    can_be_converted_to_ibkr_action: bool
    conversion_block_reason_nl: str | None = None

    @model_validator(mode="after")
    def _validate_action(self) -> "ActionSuggestion":
        if self.action == SuggestionAction.GEBLOKKEERD and not self.blocked_reasons:
            raise ValueError("blocked action requires blocked reasons")
        if self.can_be_converted_to_ibkr_action and self.blocked_reasons:
            raise ValueError("convertible suggestion cannot have blocking reasons")
        return self


class SuggestionOutcomePlaceholder(DomainBaseModel):
    suggestion_id: str
    status: SuggestionOutcomeStatus
    measured_at: datetime | None = None
    measurement_window_nl: str | None = None
    notes_nl: str


def default_credibility_for_source_type(
    source_type: ResearchSourceType, *, source_id: str = "default"
) -> SourceCredibilityAssessment:
    mapping = {
        ResearchSourceType.BROKER_DATA: (
            SourceAuthorityCategory.BROKER_TRUTH,
            SourceCredibilityLevel.HIGHEST,
            Decimal("99"),
            "Brokergegevens gelden als waarheid voor accountstatus.",
        ),
        ResearchSourceType.EXCHANGE_CALENDAR: (
            SourceAuthorityCategory.OFFICIAL_EXCHANGE,
            SourceCredibilityLevel.HIGHEST,
            Decimal("97"),
            "Officiële beurskalender is leidend voor handelsbeschikbaarheid.",
        ),
        ResearchSourceType.OFFICIAL_FILING: (
            SourceAuthorityCategory.REGULATOR_OR_FILING_SYSTEM,
            SourceCredibilityLevel.HIGH,
            Decimal("88"),
            "Officiële filing is sterk voor bedrijfsfeiten.",
        ),
        ResearchSourceType.COMPANY_REPORT: (
            SourceAuthorityCategory.OFFICIAL_COMPANY,
            SourceCredibilityLevel.HIGH,
            Decimal("85"),
            "Bedrijfsrapport is belangrijk maar vergt context.",
        ),
        ResearchSourceType.ANALYST_COMMENTARY: (
            SourceAuthorityCategory.ANALYST_OR_BROKER_OPINION,
            SourceCredibilityLevel.MEDIUM,
            Decimal("55"),
            "Analistencommentaar is opinie, geen bron van waarheid.",
        ),
        ResearchSourceType.BLOG_OR_FORUM: (
            SourceAuthorityCategory.SOCIAL_OR_FORUM,
            SourceCredibilityLevel.LOW,
            Decimal("20"),
            "Blog/forum-inhoud heeft lage betrouwbaarheid.",
        ),
    }
    authority, level, score, reason = mapping.get(
        source_type,
        (
            SourceAuthorityCategory.UNKNOWN,
            SourceCredibilityLevel.UNKNOWN,
            Decimal("40"),
            "Bronbetrouwbaarheid is nog onbekend en vereist review.",
        ),
    )
    return SourceCredibilityAssessment(
        source_id=source_id,
        authority_category=authority,
        credibility_level=level,
        credibility_score=score,
        reason_nl=reason,
        assessed_at=datetime.now(UTC),
    )


def default_freshness_slas() -> tuple[FreshnessSla, ...]:
    return (
        FreshnessSla(
            data_type=ResearchDataType.BROKER_CASH,
            max_age_seconds=300,
            blocks_suggestions_when_stale=True,
            blocks_orders_when_stale=True,
            warning_nl="Cashdata is mogelijk verouderd.",
            explanation_nl="Actuele cash is vereist voor veilige ordercontrole.",
        ),
        FreshnessSla(
            data_type=ResearchDataType.BROKER_POSITIONS,
            max_age_seconds=300,
            blocks_suggestions_when_stale=True,
            blocks_orders_when_stale=True,
            warning_nl="Positiedata is mogelijk verouderd.",
            explanation_nl="Actuele posities zijn nodig voor limieten en risico.",
        ),
        FreshnessSla(
            data_type=ResearchDataType.MARKET_PRICE,
            max_age_seconds=120,
            blocks_suggestions_when_stale=False,
            blocks_orders_when_stale=True,
            warning_nl="Marktprijs is mogelijk verouderd.",
            explanation_nl="Timing en ordercontrole vereisen recente prijzen.",
        ),
        FreshnessSla(
            data_type=ResearchDataType.FX_RATE,
            max_age_seconds=600,
            blocks_suggestions_when_stale=True,
            blocks_orders_when_stale=True,
            warning_nl="FX-koers is mogelijk verouderd.",
            explanation_nl="FX-conversie vereist recente wisselkoersen.",
        ),
        FreshnessSla(
            data_type=ResearchDataType.AI_RESEARCH,
            max_age_seconds=86400,
            blocks_suggestions_when_stale=True,
            blocks_orders_when_stale=False,
            warning_nl="AI-onderzoek is mogelijk verouderd.",
            explanation_nl="Oude onderzoekscontext mag geen actieve suggestie sturen.",
        ),
        FreshnessSla(
            data_type=ResearchDataType.ACTION_SUGGESTION,
            max_age_seconds=3600,
            blocks_suggestions_when_stale=True,
            blocks_orders_when_stale=True,
            warning_nl="Suggestie is mogelijk verlopen.",
            explanation_nl="Suggesties hebben een beperkte geldigheidsduur.",
        ),
    )


def action_label_nl(action: SuggestionAction) -> str:
    return {
        SuggestionAction.KOPEN: "Kopen",
        SuggestionAction.LANGZAAM_BIJKOPEN: "Langzaam bijkopen",
        SuggestionAction.HOUDEN: "Houden",
        SuggestionAction.BEKIJKEN: "Bekijken",
        SuggestionAction.VERMINDEREN: "Verminderen",
        SuggestionAction.VERKOPEN: "Verkopen",
        SuggestionAction.VERMIJDEN: "Vermijden",
        SuggestionAction.CASH_HOUDEN: "Cash houden",
        SuggestionAction.GEEN_ACTIE: "Geen actie",
        SuggestionAction.GEBLOKKEERD: "Geblokkeerd",
    }[action]


def blocked_reason_label_nl(reason: SuggestionBlockedReason) -> str:
    return reason.value.replace("_", " ")


def freshness_status_label_nl(status: FreshnessStatus) -> str:
    return status.value.replace("_", " ")


def source_credibility_label_nl(level: SourceCredibilityLevel) -> str:
    return level.value


def suggestion_is_blocked(suggestion: ActionSuggestion) -> bool:
    return suggestion.action == SuggestionAction.GEBLOKKEERD or bool(suggestion.blocked_reasons)


def suggestion_can_be_converted_to_ibkr_action(suggestion: ActionSuggestion) -> bool:
    return suggestion.can_be_converted_to_ibkr_action and not suggestion_is_blocked(suggestion)
