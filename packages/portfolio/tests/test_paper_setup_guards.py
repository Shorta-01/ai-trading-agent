from datetime import UTC, datetime
from decimal import Decimal

import pytest
from portfolio_outlook_domain import (
    FirstRunPaperPortfolioSetupRequest,
    PaperPortfolioBaseCurrency,
    PaperSetupMode,
    build_first_run_setup_preview,
)

from portfolio_outlook_portfolio import (
    require_first_run_setup_request_allowed,
    require_setup_preview_safe,
)
from portfolio_outlook_portfolio.errors import InvalidAccountingInputError


def _req(confirmed: bool = True) -> FirstRunPaperPortfolioSetupRequest:
    return FirstRunPaperPortfolioSetupRequest(
        setup_mode=PaperSetupMode.FIRST_RUN,
        base_currency=PaperPortfolioBaseCurrency.EUR,
        starting_cash=Decimal("10000"),
        portfolio_name="Mijn paper portefeuille",
        user_confirmed_paper_only=confirmed,
        user_confirmed_no_real_money=confirmed,
        user_confirmed_no_broker_order=confirmed,
        explanation_nl="test",
    )


def test_valid_request_passes() -> None:
    require_first_run_setup_request_allowed(_req())


def test_missing_confirmation_raises() -> None:
    with pytest.raises((ValueError, InvalidAccountingInputError)):
        require_first_run_setup_request_allowed(_req(False))


def test_valid_preview_passes() -> None:
    preview = build_first_run_setup_preview(
        request=_req(), first_run_setup_preview_id="preview_ok", created_at=datetime.now(UTC)
    )
    require_setup_preview_safe(preview)
