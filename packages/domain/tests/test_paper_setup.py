from datetime import UTC, datetime
from decimal import Decimal

import pytest

from portfolio_outlook_domain import (
    FirstRunPaperPortfolioSetupRequest,
    PaperPortfolioBaseCurrency,
    PaperSetupMode,
    PaperSetupWarningReason,
    build_default_paper_portfolio_setup_defaults,
    build_first_run_setup_preview,
    build_not_configured_paper_setup_state,
    paper_setup_ready_for_creation,
)


def test_defaults() -> None:
    defaults = build_default_paper_portfolio_setup_defaults()
    assert defaults.default_base_currency is PaperPortfolioBaseCurrency.EUR
    assert defaults.default_starting_cash == Decimal("10000")
    assert defaults.paper_only_required is True


def test_preview_flow() -> None:
    req = FirstRunPaperPortfolioSetupRequest(
        setup_mode=PaperSetupMode.FIRST_RUN,
        base_currency=PaperPortfolioBaseCurrency.EUR,
        starting_cash=Decimal("10000"),
        portfolio_name="Mijn paper portefeuille",
        user_confirmed_paper_only=True,
        user_confirmed_no_real_money=True,
        user_confirmed_no_broker_order=True,
        explanation_nl="Test",
    )
    preview = build_first_run_setup_preview(
        request=req,
        first_run_setup_preview_id="preview_1",
        created_at=datetime.now(UTC),
    )
    assert preview.persisted is False
    assert PaperSetupWarningReason.PREVIEW_NOT_SAVED in preview.warning_reasons
    assert paper_setup_ready_for_creation(preview) is True
    assert preview.model_dump()


def test_invalid_cash() -> None:
    with pytest.raises(ValueError):
        FirstRunPaperPortfolioSetupRequest(
            setup_mode=PaperSetupMode.FIRST_RUN,
            base_currency=PaperPortfolioBaseCurrency.EUR,
            starting_cash=Decimal("0"),
            portfolio_name="x",
            user_confirmed_paper_only=True,
            user_confirmed_no_real_money=True,
            user_confirmed_no_broker_order=True,
            explanation_nl="x",
        )


def test_not_configured_state() -> None:
    state = build_not_configured_paper_setup_state()
    assert state.persisted is False
