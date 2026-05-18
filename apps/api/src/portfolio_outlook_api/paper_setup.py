from datetime import UTC, datetime
from decimal import Decimal

from portfolio_outlook_domain import (
    FirstRunPaperPortfolioSetupRequest,
    PaperPortfolioBaseCurrency,
    PaperSetupMode,
    build_default_paper_portfolio_setup_defaults,
    build_first_run_setup_preview,
    build_not_configured_paper_setup_state,
)
from pydantic import BaseModel, field_validator


class SetupPreviewInput(BaseModel):
    base_currency: str
    starting_cash: str
    portfolio_name: str
    user_confirmed_paper_only: bool
    user_confirmed_no_real_money: bool
    user_confirmed_no_broker_order: bool

    @field_validator("starting_cash")
    @classmethod
    def validate_cash_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("starting_cash is verplicht.")
        return value


def get_setup_status() -> dict[str, object]:
    return build_not_configured_paper_setup_state().model_dump(mode="json")


def get_setup_defaults() -> dict[str, object]:
    defaults = build_default_paper_portfolio_setup_defaults()
    payload = defaults.model_dump(mode="json")
    payload["default_starting_cash"] = str(defaults.default_starting_cash)
    payload["minimum_starting_cash"] = str(defaults.minimum_starting_cash)
    payload["maximum_starting_cash"] = (
        str(defaults.maximum_starting_cash) if defaults.maximum_starting_cash else None
    )
    return payload


def create_setup_preview(input_data: SetupPreviewInput) -> dict[str, object]:
    request = FirstRunPaperPortfolioSetupRequest(
        setup_mode=PaperSetupMode.FIRST_RUN,
        base_currency=PaperPortfolioBaseCurrency(input_data.base_currency),
        starting_cash=Decimal(input_data.starting_cash),
        portfolio_name=input_data.portfolio_name,
        user_confirmed_paper_only=input_data.user_confirmed_paper_only,
        user_confirmed_no_real_money=input_data.user_confirmed_no_real_money,
        user_confirmed_no_broker_order=input_data.user_confirmed_no_broker_order,
        explanation_nl="Gebruiker controleert de eerste paper setup via voorbeeld.",
    )
    preview = build_first_run_setup_preview(
        request=request,
        first_run_setup_preview_id="preview_first_run",
        created_at=datetime.now(UTC),
    )
    return preview.model_dump(mode="json")
