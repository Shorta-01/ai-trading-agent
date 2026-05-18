from datetime import datetime
from decimal import Decimal

from pydantic import field_validator, model_validator

from .enums import (
    PaperPortfolioBaseCurrency,
    PaperSetupBlockReason,
    PaperSetupMode,
    PaperSetupStatus,
    PaperSetupWarningReason,
)
from .identifiers import AuditEventId, FirstRunSetupPreviewId, PaperCashAccountId, SourceReferenceId
from .primitives import DomainBaseModel


class PaperCashAccountDefinition(DomainBaseModel):
    paper_cash_account_id: PaperCashAccountId
    currency: PaperPortfolioBaseCurrency
    starting_cash: Decimal
    explanation_nl: str

    @field_validator("starting_cash", mode="before")
    @classmethod
    def reject_float_starting_cash(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float starting_cash is not allowed.")
        return value

    @field_validator("starting_cash")
    @classmethod
    def validate_starting_cash(cls, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise ValueError("starting_cash must be greater than zero.")
        return value

    @field_validator("explanation_nl")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("explanation_nl is required.")
        return value


class FirstRunPaperPortfolioSetupRequest(DomainBaseModel):
    setup_mode: PaperSetupMode
    base_currency: PaperPortfolioBaseCurrency
    starting_cash: Decimal
    portfolio_name: str
    user_confirmed_paper_only: bool
    user_confirmed_no_real_money: bool
    user_confirmed_no_broker_order: bool
    explanation_nl: str

    @field_validator("starting_cash", mode="before")
    @classmethod
    def reject_float_starting_cash(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float starting_cash is not allowed.")
        return value

    @field_validator("starting_cash")
    @classmethod
    def validate_starting_cash(cls, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise ValueError("starting_cash must be greater than zero.")
        return value

    @field_validator("portfolio_name", "explanation_nl")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field is required.")
        return value

    @model_validator(mode="after")
    def validate_confirmations(self) -> "FirstRunPaperPortfolioSetupRequest":
        if self.setup_mode is not PaperSetupMode.FIRST_RUN:
            raise ValueError("setup_mode must be first_run.")
        if not self.user_confirmed_paper_only:
            raise ValueError("paper-only confirmation is required.")
        if not self.user_confirmed_no_real_money:
            raise ValueError("no-real-money confirmation is required.")
        if not self.user_confirmed_no_broker_order:
            raise ValueError("no-broker-order confirmation is required.")
        return self


class FirstRunPaperPortfolioSetupPreview(DomainBaseModel):
    first_run_setup_preview_id: FirstRunSetupPreviewId
    setup_status: PaperSetupStatus
    request: FirstRunPaperPortfolioSetupRequest
    cash_account: PaperCashAccountDefinition
    block_reasons: list[PaperSetupBlockReason]
    warning_reasons: list[PaperSetupWarningReason]
    source_reference_ids: list[SourceReferenceId]
    audit_event_ids: list[AuditEventId]
    created_at: datetime
    title_nl: str
    summary_nl: str
    help_nl: str
    persisted: bool

    @field_validator("title_nl", "summary_nl", "help_nl")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Dutch text fields are required.")
        return value

    @model_validator(mode="after")
    def validate_state(self) -> "FirstRunPaperPortfolioSetupPreview":
        if self.persisted:
            raise ValueError("Preview cannot be persisted in this foundation step.")
        if self.setup_status is PaperSetupStatus.PREVIEW_READY and self.block_reasons:
            raise ValueError("preview_ready cannot contain block reasons.")
        if (
            self.setup_status in {PaperSetupStatus.BLOCKED, PaperSetupStatus.FAILED}
            and not self.block_reasons
        ):
            raise ValueError("blocked/failed preview must contain block reasons.")
        return self


class PaperPortfolioSetupDefaults(DomainBaseModel):
    default_base_currency: PaperPortfolioBaseCurrency
    default_starting_cash: Decimal
    minimum_starting_cash: Decimal
    maximum_starting_cash: Decimal | None = None
    default_portfolio_name: str
    paper_only_required: bool
    broker_required: bool
    live_trading_allowed: bool
    explanation_nl: str

    @field_validator(
        "default_starting_cash",
        "minimum_starting_cash",
        "maximum_starting_cash",
        mode="before",
    )
    @classmethod
    def reject_float_values(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Float values are not allowed.")
        return value

    @field_validator("default_starting_cash", "minimum_starting_cash")
    @classmethod
    def validate_positive_decimal(cls, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise ValueError("Cash values must be greater than zero.")
        return value

    @field_validator("explanation_nl")
    @classmethod
    def validate_explanation(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("explanation_nl is required.")
        return value

    @model_validator(mode="after")
    def validate_rules(self) -> "PaperPortfolioSetupDefaults":
        if (
            self.maximum_starting_cash is not None
            and self.maximum_starting_cash < self.minimum_starting_cash
        ):
            raise ValueError("maximum_starting_cash must be >= minimum_starting_cash.")
        if not self.paper_only_required:
            raise ValueError("paper_only_required must be true.")
        if self.broker_required:
            raise ValueError("broker_required must be false.")
        if self.live_trading_allowed:
            raise ValueError("live_trading_allowed must be false.")
        return self


class PaperPortfolioSetupState(DomainBaseModel):
    setup_status: PaperSetupStatus
    configured: bool
    can_preview_setup: bool
    can_create_setup: bool
    persisted: bool
    title_nl: str
    summary_nl: str
    help_nl: str

    @field_validator("title_nl", "summary_nl", "help_nl")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Dutch text fields are required.")
        return value

    @model_validator(mode="after")
    def validate_state(self) -> "PaperPortfolioSetupState":
        if not self.configured and self.setup_status is not PaperSetupStatus.NOT_CONFIGURED:
            raise ValueError("Not configured state must use not_configured status.")
        if not self.persisted and self.configured:
            raise ValueError("Non-persisted state cannot be configured.")
        return self


def build_default_paper_portfolio_setup_defaults() -> PaperPortfolioSetupDefaults:
    return PaperPortfolioSetupDefaults(
        default_base_currency=PaperPortfolioBaseCurrency.EUR,
        default_starting_cash=Decimal("10000"),
        minimum_starting_cash=Decimal("1"),
        maximum_starting_cash=None,
        default_portfolio_name="Mijn paper portefeuille",
        paper_only_required=True,
        broker_required=False,
        live_trading_allowed=False,
        explanation_nl="Dit is papergeld voor een veilige start zonder echt geld of broker.",
    )


def build_not_configured_paper_setup_state() -> PaperPortfolioSetupState:
    return PaperPortfolioSetupState(
        setup_status=PaperSetupStatus.NOT_CONFIGURED,
        configured=False,
        can_preview_setup=True,
        can_create_setup=False,
        persisted=False,
        title_nl="Eerste setup",
        summary_nl="Nog niet ingesteld.",
        help_nl="Controleer eerst een voorbeeld. Opslaan komt later.",
    )


def build_first_run_setup_preview(
    *,
    request: FirstRunPaperPortfolioSetupRequest,
    first_run_setup_preview_id: FirstRunSetupPreviewId,
    created_at: datetime,
    source_reference_ids: list[SourceReferenceId] | None = None,
    audit_event_ids: list[AuditEventId] | None = None,
) -> FirstRunPaperPortfolioSetupPreview:
    cash_account = PaperCashAccountDefinition(
        paper_cash_account_id="paper_cash_main",
        currency=request.base_currency,
        starting_cash=request.starting_cash,
        explanation_nl="Startsaldo in papergeld voor de eerste portfolio-opzet.",
    )
    return FirstRunPaperPortfolioSetupPreview(
        first_run_setup_preview_id=first_run_setup_preview_id,
        setup_status=PaperSetupStatus.PREVIEW_READY,
        request=request,
        cash_account=cash_account,
        block_reasons=[],
        warning_reasons=[
            PaperSetupWarningReason.PREVIEW_NOT_SAVED,
            PaperSetupWarningReason.IBKR_NOT_CONFIGURED,
            PaperSetupWarningReason.OPENAI_NOT_CONFIGURED,
            PaperSetupWarningReason.NO_POSITIONS_YET,
            PaperSetupWarningReason.NO_WATCHLIST_YET,
        ],
        source_reference_ids=source_reference_ids or [],
        audit_event_ids=audit_event_ids or [],
        created_at=created_at,
        title_nl="Voorbeeld van eerste paper setup",
        summary_nl="Deze controle is gelukt, maar nog niet opgeslagen.",
        help_nl="Er worden geen posities, orders of echt geld aangemaakt.",
        persisted=False,
    )


def paper_setup_ready_for_creation(preview: FirstRunPaperPortfolioSetupPreview) -> bool:
    return (
        preview.setup_status in {PaperSetupStatus.PREVIEW_READY, PaperSetupStatus.READY_TO_CREATE}
        and not preview.block_reasons
        and preview.request.user_confirmed_paper_only
        and preview.request.user_confirmed_no_real_money
        and preview.request.user_confirmed_no_broker_order
    )
