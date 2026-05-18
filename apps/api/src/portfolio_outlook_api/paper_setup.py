from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, field_validator

BASE_CURRENCY_EUR = "eur"
SETUP_STATUS_FIRST_RUN = "first_run"
SETUP_STATUS_NOT_CONFIGURED = "not_configured"
SETUP_STATUS_PREVIEW_READY = "preview_ready"
WARNING_PREVIEW_NOT_SAVED = "preview_not_saved"
WARNING_IBKR_NOT_CONFIGURED = "ibkr_not_configured"
WARNING_OPENAI_NOT_CONFIGURED = "openai_not_configured"


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
            raise ValueError("Startkapitaal is verplicht.")
        return value


def get_setup_status() -> dict[str, object]:
    return {
        "setup_status": SETUP_STATUS_NOT_CONFIGURED,
        "configured": False,
        "can_preview_setup": True,
        "can_create_setup": False,
        "persisted": False,
        "title_nl": "Paper setup nog niet ingesteld",
        "summary_nl": "Je kunt nu een veilige preview maken zonder opslag.",
        "help_nl": "Deze stap is alleen voor paper trading en maakt nog niets definitief.",
    }


def get_setup_defaults() -> dict[str, object]:
    return {
        "default_base_currency": BASE_CURRENCY_EUR,
        "default_starting_cash": "10000",
        "minimum_starting_cash": "1",
        "maximum_starting_cash": None,
        "default_portfolio_name": "Mijn paper portefeuille",
        "paper_only_required": True,
        "broker_required": False,
        "live_trading_allowed": False,
        "explanation_nl": "Gebruik deze standaardwaarden om veilig met paper trading te starten.",
    }


def create_setup_preview(input_data: SetupPreviewInput) -> dict[str, object]:
    if input_data.base_currency != BASE_CURRENCY_EUR:
        raise ValueError("Alleen EUR is toegestaan voor deze preview.")

    try:
        starting_cash = Decimal(input_data.starting_cash)
    except InvalidOperation as exc:
        raise ValueError("Startkapitaal moet een geldig getal zijn.") from exc

    if starting_cash <= Decimal("0"):
        raise ValueError("Startkapitaal moet groter zijn dan 0.")

    if not input_data.user_confirmed_paper_only:
        raise ValueError("Bevestig dat dit alleen paper trading is.")
    if not input_data.user_confirmed_no_real_money:
        raise ValueError("Bevestig dat er geen echt geld wordt gebruikt.")
    if not input_data.user_confirmed_no_broker_order:
        raise ValueError("Bevestig dat er geen broker orders worden geplaatst.")

    return {
        "setup_status": SETUP_STATUS_PREVIEW_READY,
        "setup_mode": SETUP_STATUS_FIRST_RUN,
        "persisted": False,
        "title_nl": "Preview van je paper setup",
        "summary_nl": "Controleer de instellingen. Er is nog niets opgeslagen.",
        "help_nl": "Dit is een veilige voorbeeldweergave zonder echte orders of opslag.",
        "warning_reasons": [
            WARNING_PREVIEW_NOT_SAVED,
            WARNING_IBKR_NOT_CONFIGURED,
            WARNING_OPENAI_NOT_CONFIGURED,
        ],
        "block_reasons": [],
        "request": {
            "base_currency": input_data.base_currency,
            "starting_cash": str(starting_cash),
            "portfolio_name": input_data.portfolio_name,
            "user_confirmed_paper_only": input_data.user_confirmed_paper_only,
            "user_confirmed_no_real_money": input_data.user_confirmed_no_real_money,
            "user_confirmed_no_broker_order": input_data.user_confirmed_no_broker_order,
        },
        "cash_account": {
            "currency": BASE_CURRENCY_EUR,
            "starting_cash": str(starting_cash),
        },
        "positions": [],
        "orders": [],
        "created_at": datetime.now(UTC).isoformat(),
    }
