from decimal import Decimal

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain import PaperLiveMode, PortfolioSettings
from portfolio_outlook_domain.primitives import Percentage


def test_portfolio_settings_defaults() -> None:
    settings = PortfolioSettings()
    assert settings.starting_paper_capital.amount == Decimal("10000")
    assert settings.starting_paper_capital.currency == "EUR"
    assert settings.paper_live_mode == PaperLiveMode.PAPER
    assert settings.interface_language == "nl"


def test_portfolio_settings_rejects_invalid_first_run_split() -> None:
    with pytest.raises(ValidationError):
        PortfolioSettings(
            first_run_minimum_cash_reserve=Percentage(value="60"),
            first_run_maximum_invested=Percentage(value="50"),
        )


def test_portfolio_settings_rejects_non_paper_mode() -> None:
    with pytest.raises(ValidationError):
        PortfolioSettings(paper_live_mode=PaperLiveMode.LIVE_READ_ONLY)
